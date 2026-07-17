import os
import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import tensorflow as tf
from collections import deque

BASE_DIR = r"c:\Users\sahil\Desktop\ICFOSS\Anomaly Detection"
MLP_PATH = os.path.join(BASE_DIR, "models", "saved", "large_ar_mlp.keras")
OUTAGE_DATA = os.path.join(BASE_DIR, "data", "processed", "data-july1-14_outage.csv")
GT_DATA = os.path.join(BASE_DIR, "data", "processed", "data-july1-14_processed.csv")
OUT_HTML = os.path.join(BASE_DIR, "plots", "mlp_outage_dataset_test.html")

N_LAGS = 8
DATE_FMT = "%d-%m-%Y %H:%M"

def build_time_features_mlp(ts):
    mins_day = ts.hour * 60 + ts.minute
    day_frac = mins_day / 1440.0
    half_day_frac = mins_day / 720.0
    quarter_day_frac = mins_day / 360.0
    eighth_day_frac = mins_day / 180.0
    
    mins_week = ts.weekday() * 1440 + mins_day
    week_frac = mins_week / 10080.0
    
    return {
        "week_sin": math.sin(2 * math.pi * week_frac),
        "week_cos": math.cos(2 * math.pi * week_frac),
        "day_sin": math.sin(2 * math.pi * day_frac),
        "day_cos": math.cos(2 * math.pi * day_frac),
        "half_day_sin": math.sin(2 * math.pi * half_day_frac),
        "half_day_cos": math.cos(2 * math.pi * half_day_frac),
        "quarter_day_sin": math.sin(2 * math.pi * quarter_day_frac),
        "quarter_day_cos": math.cos(2 * math.pi * quarter_day_frac),
        "eighth_day_sin": math.sin(2 * math.pi * eighth_day_frac),
        "eighth_day_cos": math.cos(2 * math.pi * eighth_day_frac),
        "weekly_bin_norm": week_frac,
        "day_of_week": float(ts.weekday()) / 6.0,
    }

def relu(x): return np.maximum(0, x)
def sigmoid(x): return 1.0 / (1.0 + np.exp(-x))

def get_mlp_runner(model_path):
    model = tf.keras.models.load_model(model_path)
    
    w_h1_cls, b_h1_cls = model.get_layer("hidden1_cls").get_weights()
    w_h2_cls, b_h2_cls = model.get_layer("hidden2_cls").get_weights()
    w_out_cls, b_out_cls = model.get_layer("anomaly").get_weights()
    
    w_h1_reg, b_h1_reg = model.get_layer("hidden1_reg").get_weights()
    w_h2_reg, b_h2_reg = model.get_layer("hidden2_reg").get_weights()
    w_h3_reg, b_h3_reg = model.get_layer("hidden3_reg").get_weights()
    w_out_reg, b_out_reg = model.get_layer("wl").get_weights()
    
    def run_mlp_numpy(features):
        h1c = relu(np.dot(features, w_h1_cls) + b_h1_cls)
        h2c = relu(np.dot(h1c, w_h2_cls)      + b_h2_cls)
        prob = sigmoid(np.dot(h2c, w_out_cls)  + b_out_cls)[0]
        
        reg  = features[2:]
        h1r  = relu(np.dot(reg,  w_h1_reg) + b_h1_reg)
        h2r  = relu(np.dot(h1r,  w_h2_reg) + b_h2_reg)
        h3r  = relu(np.dot(h2r,  w_h3_reg) + b_h3_reg)
        wl   = (np.dot(h3r, w_out_reg) + b_out_reg)[0]
        return prob, wl
        
    return run_mlp_numpy

def main():
    print("Loading data...")
    df_out = pd.read_csv(OUTAGE_DATA)
    df_gt = pd.read_csv(GT_DATA)
    
    df_out['Time_datetime'] = pd.to_datetime(df_out['Time'], format=DATE_FMT)
    df_gt['Time_datetime'] = pd.to_datetime(df_gt['Time'], format=DATE_FMT)
    
    print("Loading model...")
    run_mlp = get_mlp_runner(MLP_PATH)
    
    wl_raw_arr = df_out['Water Level'].values
    ec_arr = df_out['errorcode'].values
    times = df_out['Time_datetime']
    
    wl_corrected = np.zeros(len(df_out))
    
    # Initialize lag buffer
    init_val = wl_raw_arr[0]
    lag_buf = deque([init_val] * N_LAGS, maxlen=N_LAGS)
    prev_ec = 0
    
    print("Running AR-MLP Inference...")
    for i in range(len(df_out)):
        ts = times.iloc[i]
        ec = ec_arr[i]
        wl = wl_raw_arr[i]
        time_feat = build_time_features_mlp(ts)
        
        feat = np.zeros(23, dtype=np.float32)
        feat[0] = float(ec) / 5.0
        feat[1] = float(wl) / 4.5
        feat[2:10] = list(reversed(lag_buf))
        feat[10] = time_feat["week_sin"]
        feat[11] = time_feat["week_cos"]
        feat[12] = time_feat["day_sin"]
        feat[13] = time_feat["day_cos"]
        feat[14] = time_feat["half_day_sin"]
        feat[15] = time_feat["half_day_cos"]
        feat[16] = time_feat["quarter_day_sin"]
        feat[17] = time_feat["quarter_day_cos"]
        feat[18] = time_feat["eighth_day_sin"]
        feat[19] = time_feat["eighth_day_cos"]
        feat[20] = time_feat["weekly_bin_norm"]
        feat[21] = time_feat["day_of_week"]
        feat[22] = float(prev_ec) / 5.0
        
        prob, pred = run_mlp(feat)
        is_anom = (prob > 0.5) or (ec == 1) or (ec == 5)
        
        if not is_anom:
            wl_corr = wl
        else:
            wl_corr = pred
            
        wl_corrected[i] = wl_corr
        lag_buf.append(wl_corr)
        prev_ec = ec

    df_out['wl_corrected'] = wl_corrected
    
    # Plotting
    print("Generating Plotly visualization...")
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_gt['Time_datetime'], y=df_gt['Water Level'], mode='lines',
        name='Ground Truth (Original)', line=dict(color='rgba(255, 255, 255, 0.4)', width=2, dash='dash')
    ))
    
    fig.add_trace(go.Scatter(
        x=df_out['Time_datetime'], y=df_out['Water Level'], mode='lines',
        name='Raw Sensor Input (Outages injected)', line=dict(color='rgba(255, 50, 50, 0.6)', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=df_out['Time_datetime'], y=df_out['wl_corrected'], mode='lines',
        name='AR-MLP Prediction', line=dict(color='#00ff9d', width=2)
    ))
    
    # Calculate RMSE during outages
    outage_mask = (df_out['errorcode'] == 1) | (df_out['errorcode'] == 5)
    
    # Align GT and Outage predictions for RMSE calculation
    aligned_df = pd.merge(df_out[['Time_datetime', 'wl_corrected', 'errorcode']], 
                          df_gt[['Time_datetime', 'Water Level']], 
                          on='Time_datetime', suffixes=('', '_gt'))
                          
    aligned_outage = aligned_df[(aligned_df['errorcode'] == 1) | (aligned_df['errorcode'] == 5)]
    
    if len(aligned_outage) > 0:
        rmse = np.sqrt(np.mean((aligned_outage['wl_corrected'] - aligned_outage['Water Level'])**2))
        title = f'AR-MLP Inference on data-july1-14_outage.csv<br><sup>RMSE during Outages: {rmse:.4f} m</sup>'
    else:
        title = 'AR-MLP Inference on data-july1-14_outage.csv'
    
    fig.update_layout(
        title=dict(text=title, x=0.5, font=dict(color='white')),
        plot_bgcolor='#111111', paper_bgcolor='#111111',
        xaxis=dict(title='Time', gridcolor='#333333', color='white'),
        yaxis=dict(title='Water Level (m)', gridcolor='#333333', color='white'),
        legend=dict(font=dict(color='white')),
        hovermode='x unified'
    )
    
    os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
    fig.write_html(OUT_HTML)
    print(f"Plot saved successfully to {OUT_HTML}")
    fig.show()

if __name__ == '__main__':
    main()
