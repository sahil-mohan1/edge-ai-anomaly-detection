import os
import sys
import numpy as np
import pandas as pd
import tensorflow as tf
from datetime import datetime
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("--- Python CNN Anomaly Detector Outage Tester ---")
    
    # Setup paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_path = os.path.join(base_dir, 'models', 'saved', 'water_level_cnn.keras')
    data_path = os.path.join(base_dir, 'data', 'processed', 'data-may26-june18_processed.csv')
    output_path = os.path.join(base_dir, 'cnn_model_raw_output.txt')
    
    outage_start_str = "01-06-2026 00:00"
    outage_end_str = "04-06-2026 00:00"
    if len(sys.argv) >= 3:
        outage_start_str = sys.argv[1]
        outage_end_str = sys.argv[2]
        
    outage_start = datetime.strptime(outage_start_str, "%d-%m-%Y %H:%M")
    outage_end = datetime.strptime(outage_end_str, "%d-%m-%Y %H:%M")
    
    print(f"Simulating Outage from {outage_start} to {outage_end}")
    
    # Load model
    print("Loading CNN model...")
    model = tf.keras.models.load_model(model_path)
    
    # Load data
    df = pd.read_csv(data_path)
    df['Time_datetime'] = pd.to_datetime(df['Time'], format="%d-%m-%Y %H:%M")
    
    # Load diurnal profile
    # The C++ script uses diurnal_profile_means[672]. We can extract this from the training dataset
    print("Loading diurnal profile...")
    train_df = pd.read_csv(os.path.join(base_dir, 'data', 'processed', 'training_dataset.csv'))
    train_df['Time_datetime'] = pd.to_datetime(train_df['Time'], format="%d-%m-%Y %H:%M")
    day_idx = (train_df['Time_datetime'].dt.dayofweek + 1) % 7
    train_df['weekly_bin'] = day_idx * 96 + train_df['Time_datetime'].dt.hour * 4 + train_df['Time_datetime'].dt.minute // 15
    normal_samples = train_df[(train_df['is_anomaly'] == 0) & (train_df['wl_clean'] > 0)]
    diurnal_means = normal_samples.groupby('weekly_bin')['wl_clean'].mean().reindex(range(672))
    diurnal_means = diurnal_means.interpolate(limit_direction='both').fillna(1.34).values
    
    # Simulation state
    history = [1.34] * 12
    last_corrected_wl = 1.34
    anomaly_seq_len = 0
    anomaly_offset = 0.0
    dyn_thresh = 0.5
    BASE_THRESH = 0.5
    MAX_THRESH = 1.5
    
    print("Running simulation...")
    
    with open(output_path, 'w', encoding='utf-16') as f:
        for i, row in df.iterrows():
            t = row['Time_datetime']
            wl_raw = row['Water Level']
            errorcode = row['errorcode']
            
            # Inject outage
            if outage_start <= t < outage_end:
                wl_raw = 0.0
                errorcode = 5
                
            is_anomaly = False
            basic_anom = errorcode in [1, 2, 5]
            
            if not basic_anom:
                # CNN Inference
                input_tensor = tf.convert_to_tensor(np.array(history).reshape(1, 12, 1), dtype=tf.float32)
                cnn_pred = model(input_tensor, training=False).numpy()[0][0]
                cnn_pred = round(float(cnn_pred), 3)
                
                roc = abs(wl_raw - last_corrected_wl)
                residual = abs(wl_raw - cnn_pred)
                
                if roc <= BASE_THRESH:
                    cnn_anom = False
                elif residual > dyn_thresh:
                    cnn_anom = True
                    dyn_thresh = min(MAX_THRESH, dyn_thresh + 0.1)
                else:
                    cnn_anom = False
            else:
                cnn_anom = False
                
            if basic_anom or cnn_anom:
                is_anomaly = True
                
                if anomaly_seq_len == 0:
                    last_time = t - pd.Timedelta(minutes=15)
                    last_day_idx = (last_time.dayofweek + 1) % 7
                    last_bin = last_time.hour * 4 + last_time.minute // 15
                    last_weekly_bin = last_day_idx * 96 + last_bin
                    if last_weekly_bin >= 672: last_weekly_bin = 671
                    anomaly_offset = last_corrected_wl - diurnal_means[last_weekly_bin]
                    
                anomaly_seq_len += 1
                
                if anomaly_seq_len <= 8:
                    # Autoregressive CNN
                    input_tensor = tf.convert_to_tensor(np.array(history).reshape(1, 12, 1), dtype=tf.float32)
                    raw_pred = model(input_tensor, training=False).numpy()[0][0]
                    wl_corr = round(float(raw_pred), 3)
                else:
                    # Diurnal fallback
                    day_idx = (t.dayofweek + 1) % 7
                    bin_idx = t.hour * 4 + t.minute // 15
                    weekly_bin_idx = day_idx * 96 + bin_idx
                    if weekly_bin_idx >= 672: weekly_bin_idx = 671
                    wl_corr = diurnal_means[weekly_bin_idx] + anomaly_offset
                    
                wl_corr = max(0.05, min(4.45, wl_corr))
                
                # Push to history for autoregression
                history = history[1:] + [wl_corr]
                last_corrected_wl = wl_corr
                
            else:
                is_anomaly = False
                dyn_thresh = BASE_THRESH
                anomaly_seq_len = 0
                anomaly_offset = 0.0
                last_corrected_wl = round(wl_raw, 3)
                history = history[1:] + [last_corrected_wl]
                wl_corr = last_corrected_wl
                
            printed_ec = 3 if is_anomaly else errorcode
            
            f.write(f"Raw_WaterLevel:{wl_raw},Corr_WaterLevel:{wl_corr},ErrorCode:{printed_ec},Offset:{anomaly_offset},Seq:{anomaly_seq_len}\n")
            
    print("Done!")

if __name__ == "__main__":
    main()
