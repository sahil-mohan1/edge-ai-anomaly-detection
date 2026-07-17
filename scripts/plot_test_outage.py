import pandas as pd
import numpy as np
import plotly.graph_objects as go
import tensorflow as tf
import os
import math
from collections import deque

def build_time_features(ts):
    mins_day = ts.hour * 60 + ts.minute
    day_frac = mins_day / 1440.0
    refill_frac = mins_day / 720.0
    return {
        "hour_sin"   : math.sin(2 * math.pi * day_frac),
        "hour_cos"   : math.cos(2 * math.pi * day_frac),
        "refill_sin" : math.sin(2 * math.pi * refill_frac),
        "refill_cos" : math.cos(2 * math.pi * refill_frac),
        "day_of_week": float(ts.weekday()),   # 0=Mon ... 6=Sun (MLP feature)
    }

def main():
    print("Loading test data...")
    # Using aligned_test_data.csv
    df = pd.read_csv("c:/Users/sahil/Desktop/ICFOSS/Anomaly Detection/data/processed/aligned_test_data.csv")
    df['Time_datetime'] = pd.to_datetime(df['Time'])
    df = df.sort_values('Time_datetime').reset_index(drop=True)
    
    df['wl_raw'] = df['Water_Level_Raw'].ffill().bfill()
    df['wl_clean'] = df['Water_Level_GT'].replace(-1.0, np.nan)
    df['errorcode'] = df['errorcode'].fillna(0).astype(int)
    
    # Introduce a 3-day outage
    # 3 days = 72 hours = 288 samples (15 min intervals)
    print("Simulating 3-day outage...")
    outage_start = len(df) // 2
    outage_length = 288
    
    # Set errorcode to 5 and wl_raw to 0.0 for the outage duration
    df.loc[outage_start:outage_start + outage_length - 1, 'errorcode'] = 5
    df.loc[outage_start:outage_start + outage_length - 1, 'wl_raw'] = 0.0
    
    # Load training data to build diurnal profile
    print("Loading training data to build diurnal profile...")
    train_df = pd.read_csv("c:/Users/sahil/Desktop/ICFOSS/Anomaly Detection/data/processed/training_dataset.csv")
    train_df['Time_datetime'] = pd.to_datetime(train_df['Time'], format="%d-%m-%Y %H:%M")
    day_idx = (train_df['Time_datetime'].dt.dayofweek + 1) % 7
    train_df['weekly_bin'] = day_idx * 96 + train_df['Time_datetime'].dt.hour * 4 + train_df['Time_datetime'].dt.minute // 15
    normal_samples = train_df[(train_df['is_anomaly'] == 0) & (train_df['wl_clean'] > 0)]
    diurnal_means = normal_samples.groupby('weekly_bin')['wl_clean'].mean().reindex(range(672))
    baseline_normal = 1.34
    diurnal_means = diurnal_means.interpolate(limit_direction='both').fillna(baseline_normal).values
    print("Diurnal profile built.")

    # Load Keras Model
    print("Loading AR-MLP model...")
    model_path = "c:/Users/sahil/Desktop/ICFOSS/Anomaly Detection/models/saved/ar_mlp.keras"
    model = tf.keras.models.load_model(model_path)
    
    # Extract weights for fast NumPy execution
    w_h1_cls, b_h1_cls = model.get_layer("hidden1_cls").get_weights()
    w_h2_cls, b_h2_cls = model.get_layer("hidden2_cls").get_weights()
    w_out_cls, b_out_cls = model.get_layer("anomaly").get_weights()

    w_h1_reg, b_h1_reg = model.get_layer("hidden1_reg").get_weights()
    w_h2_reg, b_h2_reg = model.get_layer("hidden2_reg").get_weights()
    w_out_reg, b_out_reg = model.get_layer("wl").get_weights()

    def relu(x):
        return np.maximum(0, x)

    def sigmoid(x):
        return 1.0 / (1.0 + np.exp(-x))

    def run_mlp_numpy(features):
        h1_cls = relu(np.dot(features, w_h1_cls) + b_h1_cls)
        h2_cls = relu(np.dot(h1_cls, w_h2_cls) + b_h2_cls)
        prob = sigmoid(np.dot(h2_cls, w_out_cls) + b_out_cls)[0]
        
        reg_in = features[2:]
        h1_reg = relu(np.dot(reg_in, w_h1_reg) + b_h1_reg)
        h2_reg = relu(np.dot(h1_reg, w_h2_reg) + b_h2_reg)
        wl_val = (np.dot(h2_reg, w_out_reg) + b_out_reg)[0]
        
        return prob, wl_val

    # Initialize simulation states
    N_LAGS = 8
    wl_raw_arr = df['wl_raw'].values
    errorcodes = df['errorcode'].values
    times = df['Time_datetime']
    
    wl_corrected = np.zeros(len(df))
    is_anomaly_pred = np.zeros(len(df), dtype=int)
    anomaly_probs = np.zeros(len(df))
    wl_preds_mlp = np.zeros(len(df))
    correction_sources = []
    
    init_val = wl_raw_arr[0]
    lag_buf = deque([init_val] * N_LAGS, maxlen=N_LAGS)
    prev_ec = 0
    in_anomaly_seq = False
    anomaly_offset = 0.0
    anomaly_seq_len = 0
    
    print("Simulating combined model sequentially on test data...")
    for i in range(len(df)):
        ts = times.iloc[i]
        ec = errorcodes[i]
        wl = wl_raw_arr[i]
        
        time_feat = build_time_features(ts)
        lags = list(reversed(lag_buf))
        
        features = np.zeros(16, dtype=np.float32)
        features[0] = float(ec) / 5.0
        features[1] = float(wl) / 4.5
        features[2:10] = lags
        features[10] = time_feat["hour_sin"]
        features[11] = time_feat["hour_cos"]
        features[12] = time_feat["refill_sin"]
        features[13] = time_feat["refill_cos"]
        features[14] = time_feat["day_of_week"]
        features[15] = float(prev_ec) / 5.0
        
        prob, wl_pred_mlp = run_mlp_numpy(features)
        
        anomaly_probs[i] = prob
        wl_preds_mlp[i] = wl_pred_mlp
        
        is_anom = prob > 0.5
        is_anomaly_pred[i] = int(is_anom)
        
        if not is_anom:
            in_anomaly_seq = False
            anomaly_seq_len = 0
            wl_corr = wl
            correction_sources.append("Raw Normal")
        else:
            if not in_anomaly_seq:
                in_anomaly_seq = True
                anomaly_seq_len = 0
                
                last_wl = wl_corrected[i-1] if i > 0 else init_val
                last_time = times.iloc[i-1] if i > 0 else ts
                last_day = (last_time.dayofweek + 1) % 7
                last_bin = last_time.hour * 4 + last_time.minute // 15
                last_weekly_bin = last_day * 96 + last_bin
                anomaly_offset = last_wl - diurnal_means[last_weekly_bin]
            
            anomaly_seq_len += 1
            
            if anomaly_seq_len <= 8:
                wl_corr = wl_pred_mlp
                correction_sources.append("MLP Regression")
            else:
                day_idx_i = (ts.dayofweek + 1) % 7
                bin_idx = ts.hour * 4 + ts.minute // 15
                weekly_bin_idx = day_idx_i * 96 + bin_idx
                wl_corr = diurnal_means[weekly_bin_idx] + anomaly_offset
                correction_sources.append("Diurnal Fallback")
                
        wl_corrected[i] = wl_corr
        lag_buf.append(wl_corr)
        prev_ec = ec

    df['wl_corrected'] = wl_corrected
    df['is_anomaly_pred'] = is_anomaly_pred
    df['anomaly_prob'] = anomaly_probs
    df['wl_pred_mlp'] = wl_preds_mlp
    df['correction_source'] = correction_sources

    print("Generating Plotly visualizer...")
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['Time_datetime'], y=df['wl_raw'], mode='lines',
        name='Raw Water Level (w/ outage)', line=dict(color='#ff7f0e', width=1.0, dash='dot'), opacity=0.6
    ))
    
    fig.add_trace(go.Scatter(
        x=df['Time_datetime'], y=df['wl_clean'], mode='lines',
        name='Ground Truth (Original)', line=dict(color='#2ca02c', width=1.5), opacity=0.8
    ))
    
    fig.add_trace(go.Scatter(
        x=df['Time_datetime'], y=df['wl_corrected'], mode='lines',
        name='Corrected (MLP + Diurnal)', line=dict(color='#1f77b4', width=2.0),
        customdata=df['correction_source'],
        hovertemplate='<b>Time</b>: %{x}<br><b>Corrected WL</b>: %{y:.3f}m<br><b>Source</b>: %{customdata}'
    ))
    
    anom_points = df[df['is_anomaly_pred'] == 1]
    fig.add_trace(go.Scatter(
        x=anom_points['Time_datetime'], y=anom_points['wl_raw'], mode='markers',
        name='Detected Anomaly', marker=dict(color='red', size=6, symbol='x'),
        hovertemplate='<b>Time</b>: %{x}<br><b>Raw WL</b>: %{y:.3f}m<br><b>ErrorCode</b>: %{text}', text=anom_points['errorcode']
    ))
    
    fig.add_vrect(
        x0=df['Time_datetime'].iloc[outage_start], 
        x1=df['Time_datetime'].iloc[outage_start + outage_length - 1], 
        fillcolor="red", opacity=0.2, line_width=0, layer="below",
        annotation_text="3-Day Outage", annotation_position="top left"
    )

    fig.update_layout(
        title=dict(text='Test Dataset Predictions with Simulated 3-Day Outage', x=0.5, xanchor='center', font=dict(size=18, color='#ffffff')),
        xaxis=dict(title='Time', gridcolor='#333333', color='#ffffff'),
        yaxis=dict(title='Water Level (meters)', gridcolor='#333333', color='#ffffff'),
        legend=dict(font=dict(color='#ffffff'), bgcolor='rgba(0,0,0,0)'),
        paper_bgcolor='#111111', plot_bgcolor='#111111', hovermode='x unified', template='plotly_dark'
    )
    
    out_path = "c:/Users/sahil/Desktop/ICFOSS/Anomaly Detection/plots/interactive_mlp_test_outage.html"
    fig.write_html(out_path)
    print(f"Plot saved successfully -> {out_path}")

if __name__ == '__main__':
    main()
