"""
test_cnn_float_outage.py
------------------------
Evaluates the unquantized (float) 1D-CNN TFLite model on the June-July outage dataset.
Calculates performance metrics (RMSE/MAE) inside the outage region against ground truth.
Generates an interactive Plotly visualization showing the raw sensor, ground truth,
pure autoregressive CNN prediction, and hybrid CNN + Diurnal fallback correction.
"""

import os
import sys
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import tensorflow as tf
from collections import deque

BASE_DIR = "c:/Users/sahil/Desktop/ICFOSS/Anomaly Detection"
DATASET_PATH = os.path.join(BASE_DIR, "data", "processed", "data-june6-july1_outage.csv")
GT_PATH = os.path.join(BASE_DIR, "data", "processed", "data-june6-july1_processed.csv")
MODEL_PATH = os.path.join(BASE_DIR, "models", "saved", "water_level_cnn_float.tflite")
OUT_HTML = os.path.join(BASE_DIR, "plots", "interactive_cnn_june_july.html")

def main():
    print("--- 1D-CNN Float Model Outage Tester ---")
    
    # 1. Load data
    print(f"Loading dataset: {DATASET_PATH}")
    df = pd.read_csv(DATASET_PATH)
    df['Time_datetime'] = pd.to_datetime(df['Time'], format="%d-%m-%Y %H:%M")
    
    # Resample to 15-minute grid (ensuring strict continuity)
    df = df.set_index('Time_datetime')
    df = df.resample('15min').ffill().reset_index()
    df['wl_raw'] = df['Water Level'].ffill().bfill()
    df['errorcode'] = df['errorcode'].fillna(0).astype(int)
    
    # Load ground truth for comparison
    print(f"Loading ground truth: {GT_PATH}")
    df_gt = pd.read_csv(GT_PATH)
    df_gt['Time_datetime'] = pd.to_datetime(df_gt['Time'], format="%d-%m-%Y %H:%M")
    df_gt = df_gt.set_index('Time_datetime')
    df_gt = df_gt.resample('15min').ffill().reset_index()
    df_gt['wl_gt'] = df_gt['Water Level'].ffill().bfill()
    
    # Map ground truth values to main dataframe
    gt_map = dict(zip(df_gt['Time_datetime'], df_gt['wl_gt']))
    df['wl_gt'] = df['Time_datetime'].map(gt_map)
    
    print(f"Dataset span: {df['Time_datetime'].min()} to {df['Time_datetime'].max()} ({len(df)} rows)")
    
    # 2. Load TFLite Model
    print(f"Loading float TFLite model: {MODEL_PATH}")
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model not found at {MODEL_PATH}")
        
    interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    def run_cnn_tflite(history_window):
        # Format history window as (1, 12, 1) float32 array
        x_input = np.array(history_window, dtype=np.float32).reshape(1, 12, 1)
        interpreter.set_tensor(input_details[0]['index'], x_input)
        interpreter.invoke()
        pred = interpreter.get_tensor(output_details[0]['index'])[0][0]
        # Clamp output to physical boundaries
        return max(0.0, min(float(pred), 4.5))

    # 3. Compute Diurnal Profile from clean history before the outage starts
    outage_start_dt = pd.Timestamp("2026-06-28 00:00:00")
    print(f"Computing diurnal profile using history prior to {outage_start_dt}...")
    
    hist_df = df[df['Time_datetime'] < outage_start_dt].copy()
    clean_hist = hist_df[(hist_df['errorcode'] == 0) & (hist_df['wl_raw'] >= 0.05) & (hist_df['wl_raw'] < 4.45)].copy()
    
    clean_hist['day_idx'] = (clean_hist['Time_datetime'].dt.dayofweek + 1) % 7
    clean_hist['weekly_bin'] = clean_hist['day_idx'] * 96 + clean_hist['Time_datetime'].dt.hour * 4 + clean_hist['Time_datetime'].dt.minute // 15
    
    weekly_means = clean_hist.groupby('weekly_bin')['wl_raw'].mean().reindex(range(672))
    diurnal_means = weekly_means.interpolate(limit_direction='both').fillna(1.34).values
    
    # Smooth diurnal profile
    window_size = 5
    half_w = window_size // 2
    padded = np.concatenate([diurnal_means[-half_w:], diurnal_means, diurnal_means[:half_w]])
    smoothed = pd.Series(padded).rolling(window=window_size, center=True).median().values
    diurnal_means = smoothed[half_w : -half_w]
    
    # 4. Sequential Simulations
    BASE_THRESH = 0.5
    MAX_THRESH = 1.5
    THRESH_DECAY = 0.9
    
    wl_raw_arr = df['wl_raw'].values
    errorcodes = df['errorcode'].values
    times = df['Time_datetime']
    start_time = times.iloc[0]
    
    # --- Mode A: Pure CNN Autoregression (No Fallback) ---
    print("Running Pure CNN Autoregression simulation...")
    wl_corrected_pure = np.zeros(len(df))
    is_anomaly_pure = np.zeros(len(df), dtype=int)
    history_pure = deque([wl_raw_arr[0]] * 12, maxlen=12)
    last_corrected_pure = wl_raw_arr[0]
    last_valid_time_pure = 0
    dyn_thresh_pure = BASE_THRESH
    buffer_poisoned_pure = False
    consecutive_anomalies_pure = 0
    
    for i in range(len(df)):
        ts = times.iloc[i]
        ec = errorcodes[i]
        wl = wl_raw_arr[i]
        current_time = int((ts - start_time).total_seconds() / 60)
        
        # Model Prediction
        cnn_pred = round(run_cnn_tflite(list(history_pure)), 3)
        
        # Rules
        is_protocol_error = (ec == 1 or ec == 3) or (ec == 5 and (wl == 0.0 or wl >= 4.45))
        is_bounds_error = (wl < 0.05 or wl >= 4.45)
        sudden_zero = (wl == 0.0 and abs(wl - last_corrected_pure) > 0.5)
        
        is_anom = False
        if is_protocol_error or is_bounds_error or sudden_zero:
            is_anom = True
            wl_corr = cnn_pred
            
            gap_mins = current_time - last_valid_time_pure
            if gap_mins > 25:
                buffer_poisoned_pure = True
        else:
            gap_mins = current_time - last_valid_time_pure
            if buffer_poisoned_pure and gap_mins > 25:
                history_pure = deque([wl] * 12, maxlen=12)
                buffer_poisoned_pure = False
                last_corrected_pure = wl
                last_valid_time_pure = current_time
                dyn_thresh_pure = BASE_THRESH
                consecutive_anomalies_pure = 0
                is_anom = False
                wl_corr = wl
            else:
                residual = abs(wl - cnn_pred)
                roc = abs(wl - last_corrected_pure)
                
                time_since_valid = current_time - last_valid_time_pure
                dyn_thresh_pure = BASE_THRESH + (dyn_thresh_pure - BASE_THRESH) * (THRESH_DECAY ** (time_since_valid / 15.0))
                
                if consecutive_anomalies_pure > 5:
                    is_anom = False
                elif roc <= BASE_THRESH:
                    is_anom = False
                elif residual > dyn_thresh_pure:
                    is_anom = True
                    consecutive_anomalies_pure += 1
                    dyn_thresh_pure = min(MAX_THRESH, dyn_thresh_pure + 0.1)
                    wl_corr = cnn_pred
                else:
                    is_anom = False
                    
            if not is_anom:
                consecutive_anomalies_pure = 0
                dyn_thresh_pure = BASE_THRESH
                last_valid_time_pure = current_time
                wl_corr = wl
                
        wl_corr = round(wl_corr, 3)
        wl_corrected_pure[i] = wl_corr
        history_pure.append(wl_corr)
        last_corrected_pure = wl_corr
        is_anomaly_pure[i] = int(is_anom)

    # --- Mode B: Hybrid CNN + Diurnal Fallback ---
    print("Running Hybrid CNN + Diurnal Fallback simulation...")
    wl_corrected_hybrid = np.zeros(len(df))
    is_anomaly_hybrid = np.zeros(len(df), dtype=int)
    history_hybrid = deque([wl_raw_arr[0]] * 12, maxlen=12)
    last_corrected_hybrid = wl_raw_arr[0]
    last_valid_time_hybrid = 0
    dyn_thresh_hybrid = BASE_THRESH
    buffer_poisoned_hybrid = False
    consecutive_anomalies_hybrid = 0
    
    anomaly_seq_len = 0
    anomaly_offset = 0.0
    
    for i in range(len(df)):
        ts = times.iloc[i]
        ec = errorcodes[i]
        wl = wl_raw_arr[i]
        current_time = int((ts - start_time).total_seconds() / 60)
        
        # Model Prediction
        cnn_pred = round(run_cnn_tflite(list(history_hybrid)), 3)
        
        # Rules
        is_protocol_error = (ec == 1 or ec == 3) or (ec == 5 and (wl == 0.0 or wl >= 4.45))
        is_bounds_error = (wl < 0.05 or wl >= 4.45)
        sudden_zero = (wl == 0.0 and abs(wl - last_corrected_hybrid) > 0.5)
        
        is_anom = False
        if is_protocol_error or is_bounds_error or sudden_zero:
            is_anom = True
        else:
            gap_mins = current_time - last_valid_time_hybrid
            if buffer_poisoned_hybrid and gap_mins > 25:
                history_hybrid = deque([wl] * 12, maxlen=12)
                buffer_poisoned_hybrid = False
                last_corrected_hybrid = wl
                last_valid_time_hybrid = current_time
                dyn_thresh_hybrid = BASE_THRESH
                consecutive_anomalies_hybrid = 0
                is_anom = False
                wl_corr = wl
            else:
                residual = abs(wl - cnn_pred)
                roc = abs(wl - last_corrected_hybrid)
                
                time_since_valid = current_time - last_valid_time_hybrid
                dyn_thresh_hybrid = BASE_THRESH + (dyn_thresh_hybrid - BASE_THRESH) * (THRESH_DECAY ** (time_since_valid / 15.0))
                
                if consecutive_anomalies_hybrid > 5:
                    is_anom = False
                elif roc <= BASE_THRESH:
                    is_anom = False
                elif residual > dyn_thresh_hybrid:
                    is_anom = True
                    consecutive_anomalies_hybrid += 1
                    dyn_thresh_hybrid = min(MAX_THRESH, dyn_thresh_hybrid + 0.1)
                else:
                    is_anom = False
                    
        if is_anom:
            if anomaly_seq_len == 0:
                last_time = ts - pd.Timedelta(minutes=15)
                last_day_idx = (last_time.dayofweek + 1) % 7
                last_bin = last_time.hour * 4 + last_time.minute // 15
                last_weekly_bin = last_day_idx * 96 + last_bin
                if last_weekly_bin >= 672: last_weekly_bin = 671
                anomaly_offset = last_corrected_hybrid - diurnal_means[last_weekly_bin]
            
            anomaly_seq_len += 1
            
            if anomaly_seq_len <= 8:
                # Use pure CNN autoregression short-term
                wl_corr = cnn_pred
            else:
                # Fall back to diurnal profile with decaying offset
                day_idx = (ts.dayofweek + 1) % 7
                bin_idx = ts.hour * 4 + ts.minute // 15
                weekly_bin_idx = day_idx * 96 + bin_idx
                if weekly_bin_idx >= 672: weekly_bin_idx = 671
                decay = 0.98 ** (anomaly_seq_len - 8)
                wl_corr = diurnal_means[weekly_bin_idx] + anomaly_offset * decay
                
            wl_corr = round(wl_corr, 3)
            gap_mins = current_time - last_valid_time_hybrid
            if gap_mins > 25:
                buffer_poisoned_hybrid = True
        else:
            anomaly_seq_len = 0
            anomaly_offset = 0.0
            consecutive_anomalies_hybrid = 0
            dyn_thresh_hybrid = BASE_THRESH
            last_valid_time_hybrid = current_time
            wl_corr = wl
            
        wl_corr = round(wl_corr, 3)
        wl_corrected_hybrid[i] = wl_corr
        history_hybrid.append(wl_corr)
        last_corrected_hybrid = wl_corr
        is_anomaly_hybrid[i] = int(is_anom)

    # 5. Calculate Metrics in the Outage Region
    outage_mask = df['errorcode'] == 5
    valid_gt = ~df['wl_gt'].isna() & outage_mask
    
    print("\n=== Outage Region Metrics Comparison ===")
    if valid_gt.sum() > 0:
        rmse_pure = np.sqrt(np.mean((wl_corrected_pure[valid_gt] - df['wl_gt'][valid_gt])**2))
        mae_pure = np.mean(np.abs(wl_corrected_pure[valid_gt] - df['wl_gt'][valid_gt]))
        
        rmse_hybrid = np.sqrt(np.mean((wl_corrected_hybrid[valid_gt] - df['wl_gt'][valid_gt])**2))
        mae_hybrid = np.mean(np.abs(wl_corrected_hybrid[valid_gt] - df['wl_gt'][valid_gt]))
        
        print(f"Pure CNN Autoregression (No Fallback):")
        print(f"  RMSE: {rmse_pure:.4f} m")
        print(f"  MAE:  {mae_pure:.4f} m")
        print(f"Hybrid CNN + Diurnal Fallback:")
        print(f"  RMSE: {rmse_hybrid:.4f} m")
        print(f"  MAE:  {mae_hybrid:.4f} m")
        print(f"Ground truth samples in outage: {valid_gt.sum()}")
    else:
        print("Warning: No valid ground truth found inside the outage region.")
        rmse_pure, mae_pure = 0.0, 0.0
        rmse_hybrid, mae_hybrid = 0.0, 0.0

    # 6. Generate Plotly HTML Visualizer
    print("Building Plotly visualizer...")
    fig = go.Figure()
    
    # Raw sensor trace
    fig.add_trace(go.Scatter(
        x=df['Time_datetime'], y=df['wl_raw'], mode='lines',
        name='Raw Sensor (with Outage)', line=dict(color='#f4a261', width=1.2, dash='dot'),
        opacity=0.7, hovertemplate='Time: %{x}<br>Raw Value: %{y:.3f}m'
    ))
    
    # Ground truth trace (overlay inside outage)
    gt_outage = df[outage_mask & ~df['wl_gt'].isna()]
    if len(gt_outage) > 0:
        fig.add_trace(go.Scatter(
            x=gt_outage['Time_datetime'], y=gt_outage['wl_gt'], mode='lines',
            name='Ground Truth (Clean Data)', line=dict(color='#2ca02c', width=2.0, dash='dash'),
            opacity=0.9, hovertemplate='Time: %{x}<br>GT Value: %{y:.3f}m'
        ))
        
    # Pure CNN trace
    fig.add_trace(go.Scatter(
        x=df['Time_datetime'], y=wl_corrected_pure, mode='lines',
        name='Pure CNN Autoregression', line=dict(color='#e63946', width=1.5),
        opacity=0.8, hovertemplate='Time: %{x}<br>Pure CNN: %{y:.3f}m'
    ))
    
    # Hybrid CNN + Diurnal trace
    fig.add_trace(go.Scatter(
        x=df['Time_datetime'], y=wl_corrected_hybrid, mode='lines',
        name='Hybrid CNN + Diurnal Fallback', line=dict(color='#4cc9f0', width=2.2),
        hovertemplate='Time: %{x}<br>Hybrid Corrected: %{y:.3f}m'
    ))
    
    # Anomaly points markers
    anoms = df[is_anomaly_hybrid == 1]
    if len(anoms) > 0:
        fig.add_trace(go.Scatter(
            x=anoms['Time_datetime'], y=anoms['wl_raw'], mode='markers',
            name='Detected Anomalies (Hybrid)', marker=dict(color='#ff6b6b', size=6, symbol='x', opacity=0.8)
        ))
        
    # Shade simulated outage regions
    outage_indices = df[outage_mask].index
    if len(outage_indices) > 0:
        fig.add_vrect(
            x0=df['Time_datetime'].iloc[outage_indices[0]],
            x1=df['Time_datetime'].iloc[outage_indices[-1]],
            fillcolor="#e63946", opacity=0.15, line_width=0, layer="below",
            annotation_text="3-Day Simulated Outage (errorcode=5)",
            annotation_position="top left",
            annotation_font=dict(color="#ff6b6b", size=11)
        )
        
    # Layout styling
    title_text = f"1D-CNN Float Model Outage Correction (Jun 24 - Jul 1)<br>" \
                 f"<sup>Hybrid RMSE: {rmse_hybrid:.3f}m | Pure CNN RMSE: {rmse_pure:.3f}m</sup>"
                 
    fig.update_layout(
        title=dict(
            text=title_text, x=0.5, xanchor='center',
            font=dict(size=17, color='#e0e0e0', family='Inter, sans-serif')
        ),
        xaxis=dict(
            title='Timestamp', gridcolor='#2a2a2a', color='#aaaaaa',
            rangeslider=dict(visible=True, thickness=0.04)
        ),
        yaxis=dict(
            title='Water Level (Distance from sensor, m)', gridcolor='#2a2a2a', color='#aaaaaa',
            zeroline=False
        ),
        legend=dict(
            font=dict(color='#cccccc', size=11),
            bgcolor='rgba(20,20,30,0.8)',
            bordercolor='#333344', borderwidth=1,
            x=0.01, y=0.99, xanchor='left', yanchor='top'
        ),
        paper_bgcolor='#0d0d1a',
        plot_bgcolor='#111120',
        hovermode='x unified',
        template='plotly_dark',
        margin=dict(l=60, r=60, t=80, b=60),
        height=600
    )
    
    os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
    fig.write_html(OUT_HTML, include_plotlyjs='cdn')
    print(f"Saved interactive Plotly graph to: {OUT_HTML}")
    print("Done!")

if __name__ == '__main__':
    main()
