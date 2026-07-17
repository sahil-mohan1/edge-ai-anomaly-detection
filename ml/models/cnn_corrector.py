from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
import os
import numpy as np
import tensorflow as tf

@dataclass
class CorrectionResult:
    timestamp:       datetime
    errorcode:       int
    original_value:  float
    corrected_value: float
    cnn_pred:        float
    is_anomaly:      bool
    correction_src:  str          # 'raw' | 'cnn_residual_gate' | 'zero_padding_interpolation'
    residual:        float

class CNNCorrector:
    """
    1D-CNN Inference wrapper and Anomaly Correction Pipeline.
    Implements Zero-Padding Latent Interpolation for missing data gaps.
    """
    def __init__(self, model_path='models/saved/water_level_cnn.keras', window_size=12, threshold=0.5):
        self.window_size = window_size
        self.threshold = threshold
        self.is_warmed_up = False
        
        # Buffer to store the last N readings
        self.history_buffer = []
        self.last_time: Optional[datetime] = None
        self.last_valid_time: Optional[datetime] = None
        
        # Load the model if it exists
        if os.path.exists(model_path):
            try:
                if model_path.endswith('.tflite'):
                    self.interpreter = tf.lite.Interpreter(model_path=model_path)
                    self.interpreter.allocate_tensors()
                    self.input_details = self.interpreter.get_input_details()
                    self.output_details = self.interpreter.get_output_details()
                    self.is_tflite = True
                    self.model = None
                else:
                    self.model = tf.keras.models.load_model(model_path)
                    self.is_tflite = False
                self.is_warmed_up = True
            except Exception as e:
                print(f"Failed to load CNN model from {model_path}: {e}")
                self.model = None
                self.is_tflite = False
        else:
            self.model = None
            self.is_tflite = False
            print(f"Warning: CNN model not found at {model_path}.")
            
        self._stats = {
            "total_processed": 0,
            "anomalies_corrected": 0,
            "interpolated_gaps": 0
        }

    def process(self, timestamp: datetime, errorcode: int, water_level: float) -> list[CorrectionResult]:
        """
        Main entry point for real-time processing.
        Returns a list of results. If there was a significant time gap, this will 
        automatically inject 'Zero-Padding' rows to interpolate the gap, returning 
        multiple CorrectionResults for a single raw input.
        """
        results = []
        
        # Check for time gaps > 25 mins (nominal interval is 15 mins)
        if self.last_time is not None:
            gap_minutes = (timestamp - self.last_time).total_seconds() / 60.0
            if gap_minutes > 25.0:
                # Calculate how many 15-minute intervals were missed
                missing_intervals = int(gap_minutes // 15) - 1
                if missing_intervals > 0:
                    for i in range(missing_intervals):
                        # Zero-padding injection: feed 0.0 to trigger the anomaly gate
                        self._stats["interpolated_gaps"] += 1
                        pad_time = self.last_time + timedelta(minutes=15)
                        res = self._process_step(pad_time, 0, 0.0, is_padding=True, real_timestamp=timestamp)
                        results.append(res)
                        self.last_time = pad_time
        
        # Process the actual reading
        res = self._process_step(timestamp, errorcode, water_level, is_padding=False, real_timestamp=timestamp)
        results.append(res)
        self.last_time = timestamp
        
        return results

    def _process_step(self, timestamp: datetime, errorcode: int, water_level: float, is_padding: bool, real_timestamp: datetime) -> CorrectionResult:
        self._stats["total_processed"] += 1
        
        # 1. Predict
        cnn_pred = self._predict_next()
        
        # 2. Residual Gate
        residual = abs(water_level - cnn_pred)
        
        # Dynamic Limit: scale limit by the time gap from the LAST VALID READING
        dyn_thresh = self.threshold
        if not is_padding and self.last_valid_time is not None:
            valid_gap_minutes = (real_timestamp - self.last_valid_time).total_seconds() / 60.0
            dyn_thresh = self.threshold * max(1.0, valid_gap_minutes / 15.0)
        
        # 3. Anomaly Rules
        is_anomaly = False
        if is_padding:
            is_anomaly = True
            src = "zero_padding_interpolation"
        elif errorcode > 0:
            is_anomaly = True
            src = f"errorcode_{errorcode}"
        elif len(self.history_buffer) == 0:
            # Always accept the very first reading to initialize the buffer (bypassing residual gate)
            is_anomaly = False
            src = "raw"
        elif water_level <= 0.01 and cnn_pred > 0.5:
            # Specific rule: Reject sudden drops to 0.0, regardless of dynamic threshold expansion
            is_anomaly = True
            src = "sudden_zero_dropout"
        else:
            roc = abs(water_level - self.history_buffer[-1])
            if roc <= self.threshold:
                # Normal physical rate of change, trust the sensor directly
                is_anomaly = False
                src = "raw"
            elif residual > dyn_thresh:
                is_anomaly = True
                src = "cnn_residual_gate"
            else:
                is_anomaly = False
                src = "raw"
            
        # 4. Correct
        if is_anomaly:
            final_val = cnn_pred
            self._stats["anomalies_corrected"] += 1
        else:
            final_val = water_level
            # Update last_valid_time ONLY if this was an accepted real reading
            if not is_padding:
                if self.last_valid_time is not None:
                    valid_gap_minutes = (real_timestamp - self.last_valid_time).total_seconds() / 60.0
                    # If recovering from a gap/anomaly, re-seed buffer to prevent CNN momentum lockout
                    if valid_gap_minutes > 25.0:
                        self.history_buffer = [final_val] * (self.window_size - 1)
                self.last_valid_time = timestamp
            
        # 5. Update state
        final_val = round(final_val, 3)
        self.history_buffer.append(final_val)
        if len(self.history_buffer) > self.window_size:
            self.history_buffer.pop(0)
            
        return CorrectionResult(
            timestamp=timestamp,
            errorcode=errorcode,
            original_value=water_level,
            corrected_value=final_val,
            cnn_pred=cnn_pred,
            is_anomaly=is_anomaly,
            correction_src=src,
            residual=residual
        )
        
    def _predict_next(self) -> float:
        """
        Fast inference using the history buffer.
        """
        if not self.is_warmed_up:
            return 0.0
            
        # If we don't have enough history, return the last known value or 0.0
        if len(self.history_buffer) < self.window_size:
            if len(self.history_buffer) > 0:
                return self.history_buffer[-1]
            return 0.0
            
        # Prepare input: (1, window_size, 1)
        x_input = np.array(self.history_buffer[-self.window_size:], dtype=np.float32)
        x_input = x_input.reshape((1, self.window_size, 1))
        
        if getattr(self, 'is_tflite', False):
            # Handle INT8 Quantization if applicable
            input_scale, input_zero_point = self.input_details[0]['quantization']
            if input_scale > 0.0:
                x_input_quant = (x_input / input_scale) + input_zero_point
                x_input_quant = np.clip(x_input_quant, -128, 127).astype(self.input_details[0]['dtype'])
                self.interpreter.set_tensor(self.input_details[0]['index'], x_input_quant)
            else:
                self.interpreter.set_tensor(self.input_details[0]['index'], x_input)
                
            self.interpreter.invoke()
            
            output_scale, output_zero_point = self.output_details[0]['quantization']
            raw_pred = self.interpreter.get_tensor(self.output_details[0]['index'])[0][0]
            if output_scale > 0.0:
                pred = float((float(raw_pred) - float(output_zero_point)) * output_scale)
            else:
                pred = float(raw_pred)
        else:
            # Inference using __call__ instead of predict() for performance in tight loops
            pred = float(self.model(x_input, training=False)[0][0])
        
        # Clamp to physical bounds to prevent mathematical extrapolation into negative numbers
        pred = max(0.0, min(pred, 4.5))
        return round(pred, 3)

    @property
    def stats(self) -> dict:
        return dict(self._stats)
