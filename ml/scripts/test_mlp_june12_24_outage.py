import os
import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import tensorflow as tf
from collections import deque
import argparse

# ── Config ───────────────────────────────────────────────────────────────────
BASE_DIR     = "c:/Users/sahil/Desktop/ICFOSS/Anomaly Detection"
DEFAULT_MODEL = os.path.join(BASE_DIR, "models", "saved", "large_ar_mlp.keras")
DATASET_CSV  = os.path.join(BASE_DIR, "data", "processed", "data-june12-24_processed.csv")
DEFAULT_HTML = os.path.join(BASE_DIR, "plots", "interactive_mlp_june12_24_outage.html")

WL_MAX       = 4.5
PHYSICAL_MIN = 0.05
PHYSICAL_MAX = 4.45
DATE_FMT     = "%d-%m-%Y %H:%M"
N_LAGS       = 8

# ── MLP Helpers ─────────────────────────────────────────────────────────────

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

def relu(x): 
    return np.maximum(0, x)

def sigmoid(x): 
    return 1.0 / (1.0 + np.exp(-x))

def get_mlp_runner(model_path):
    print(f"Loading Keras model from: {model_path}")
    model = tf.keras.models.load_model(model_path)
    
    print("Extracting weights for optimized NumPy inference...")
    w_h1_cls, b_h1_cls = model.get_layer("hidden1_cls").get_weights()
    w_h2_cls, b_h2_cls = model.get_layer("hidden2_cls").get_weights()
    w_out_cls, b_out_cls = model.get_layer("anomaly").get_weights()
    
    w_h1_reg, b_h1_reg = model.get_layer("hidden1_reg").get_weights()
    w_h2_reg, b_h2_reg = model.get_layer("hidden2_reg").get_weights()
    w_h3_reg, b_h3_reg = model.get_layer("hidden3_reg").get_weights()
    w_out_reg, b_out_reg = model.get_layer("wl").get_weights()
    
    def run_mlp_numpy(features):
        # Classification head
        h1c = relu(np.dot(features, w_h1_cls) + b_h1_cls)
        h2c = relu(np.dot(h1c, w_h2_cls)      + b_h2_cls)
        prob = sigmoid(np.dot(h2c, w_out_cls)  + b_out_cls)[0]
        
        # Regression head (uses lags and time features, index 2 onwards)
        reg  = features[2:]
        h1r  = relu(np.dot(reg,  w_h1_reg) + b_h1_reg)
        h2r  = relu(np.dot(h1r,  w_h2_reg) + b_h2_reg)
        h3r  = relu(np.dot(h2r,  w_h3_reg) + b_h3_reg)
        wl   = (np.dot(h3r, w_out_reg) + b_out_reg)[0]
        return prob, wl
        
    return run_mlp_numpy

def main():
    parser = argparse.ArgumentParser(description="Test the Large MLP model on June 12-24 dataset with custom simulated outage.")
    parser.add_argument('--outage-start', type=str, default="06-18 12:00",
                        help='Simulated outage start date (MM-DD HH:MM). Default is "06-18 12:00".')
    parser.add_argument('--outage-end', type=str, default="06-21 12:00",
                        help='Simulated outage end date (MM-DD HH:MM). Default is "06-21 12:00".')
    parser.add_argument('--model', type=str, default=DEFAULT_MODEL,
                        help='Path to the Keras model. Default: models/saved/large_ar_mlp.keras')
    parser.add_argument('--output-html', type=str, default=DEFAULT_HTML,
                        help='Path to save interactive Plotly HTML. Default: plots/interactive_mlp_june12_24_outage.html')
    args = parser.parse_args()

    # Verify files
    if not os.path.exists(DATASET_CSV):
        raise FileNotFoundError(f"Dataset CSV not found at: {DATASET_CSV}")
    if not os.path.exists(args.model):
        raise FileNotFoundError(f"Model file not found at: {args.model}")

    # Load dataset
    print(f"Loading dataset: {DATASET_CSV}")
    df = pd.read_csv(DATASET_CSV)
    df['Time_datetime'] = pd.to_datetime(df['Time'], format=DATE_FMT)
    
    # Resample to uniform 15-minute grid to fill any small gaps and keep time steps consistent
    print("Resampling dataset to uniform 15-minute grid...")
    df = df.set_index('Time_datetime').resample('15min').ffill().reset_index()
    df['wl_gt'] = df['Water Level'].ffill().bfill()
    df['wl_raw'] = df['wl_gt'].copy()
    df['errorcode'] = 0

    # Inject custom simulated outage timeframe
    year = df['Time_datetime'].dt.year.iloc[0]
    try:
        outage_start_dt = pd.to_datetime(f"{year}-{args.outage_start}:00")
        outage_end_dt = pd.to_datetime(f"{year}-{args.outage_end}:00")
    except Exception as e:
        print(f"Error parsing date format. Please check --outage-start and --outage-end match MM-DD HH:MM format.")
        raise e

    print(f"Injecting simulated outage from {outage_start_dt} to {outage_end_dt}...")
    outage_mask = (df['Time_datetime'] >= outage_start_dt) & (df['Time_datetime'] <= outage_end_dt)
    
    # During outage, sensor reports 0.0m water level and errorcode = 5
    df.loc[outage_mask, 'errorcode'] = 5
    df.loc[outage_mask, 'wl_raw'] = 0.0

    # Initialize model runner
    run_mlp = get_mlp_runner(args.model)

    wl_raw_arr = df['wl_raw'].values
    ec_arr = df['errorcode'].values
    times = df['Time_datetime']

    wl_corrected = np.zeros(len(df))
    anomaly_probs = np.zeros(len(df))
    is_anomaly_pred = np.zeros(len(df), dtype=int)
    correction_src = []

    # Initialize lag buffer with first raw water level reading
    lag_buf = deque([wl_raw_arr[0]] * N_LAGS, maxlen=N_LAGS)
    prev_ec = 0

    print("Running autoregressive simulation loop...")
    for i in range(len(df)):
        ts = times.iloc[i]
        ec = ec_arr[i]
        wl = wl_raw_arr[i]
        time_feat = build_time_features_mlp(ts)
        
        # Prepare feature vector (size 23) matching training features exactly
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
        anomaly_probs[i] = prob
        
        is_anom = (prob > 0.5) or (ec == 5)
        is_anomaly_pred[i] = int(is_anom)
        
        if not is_anom:
            wl_corr = wl
            correction_src.append("Raw (Normal)")
        else:
            wl_corr = pred
            correction_src.append(f"MLP (p={prob:.3f})")
            
        wl_corrected[i] = wl_corr
        lag_buf.append(wl_corr)
        prev_ec = ec

    df['wl_corrected'] = wl_corrected
    df['anomaly_prob'] = anomaly_probs
    df['is_anomaly'] = is_anomaly_pred
    df['correction_src'] = correction_src

    # Calculate metrics inside outage region
    gt_outage_mask = outage_mask & ~df['wl_gt'].isna()
    gt_outage = df[gt_outage_mask]
    
    rmse = 0.0
    mae = 0.0
    if len(gt_outage) > 0:
        valid_corrected = wl_corrected[gt_outage_mask]
        gt_vals = gt_outage['wl_gt'].values
        rmse = np.sqrt(np.mean((valid_corrected - gt_vals)**2))
        mae = np.mean(np.abs(valid_corrected - gt_vals))

    # --- Plotting with Plotly (Premium Dark Theme Aesthetics) ---
    print("Generating premium interactive Plotly visualization...")
    fig = go.Figure()

    # Raw Sensor Signal (with simulated outage)
    fig.add_trace(go.Scatter(
        x=df['Time_datetime'], y=df['wl_raw'], mode='lines',
        name='Raw Sensor (w/ Outage)', line=dict(color='#ff7f0e', width=1.2, dash='dot'), opacity=0.6,
        hovertemplate='<b>%{x}</b><br>Raw: %{y:.3f} m<extra></extra>'
    ))

    # Ground Truth in Outage Region
    if len(gt_outage) > 0:
        fig.add_trace(go.Scatter(
            x=gt_outage['Time_datetime'], y=gt_outage['wl_gt'], mode='lines',
            name='Ground Truth (Outage)', line=dict(color='#2ca02c', width=2.0, dash='dash'),
            hovertemplate='<b>%{x}</b><br>GT: %{y:.3f} m<extra></extra>'
        ))

    # MLP Corrected/Reconstructed Signal
    fig.add_trace(go.Scatter(
        x=df['Time_datetime'], y=df['wl_corrected'], mode='lines',
        name='MLP Corrected', line=dict(color='#4cc9f0', width=2.2),
        customdata=np.stack([df['anomaly_prob'], df['correction_src']], axis=1),
        hovertemplate=(
            '<b>%{x}</b><br>'
            'Corrected: %{y:.3f} m<br>'
            'Anomaly prob: %{customdata[0]:.3f}<br>'
            'Source: %{customdata[1]}<extra></extra>'
        )
    ))

    # Anomaly Probability (Secondary Axis)
    fig.add_trace(go.Scatter(
        x=df['Time_datetime'], y=df['anomaly_prob'], mode='lines',
        name='Anomaly Prob', line=dict(color='#ff4757', width=1.0),
        yaxis='y2', opacity=0.5,
        hovertemplate='<b>%{x}</b><br>Prob: %{y:.3f}<extra></extra>'
    ))

    # Shade Outage Region
    if outage_mask.any():
        outage_rows = df[outage_mask]
        fig.add_vrect(
            x0=outage_rows['Time_datetime'].iloc[0], 
            x1=outage_rows['Time_datetime'].iloc[-1], 
            fillcolor="#ff4757", opacity=0.12, line_width=0, layer="below",
            annotation_text="Simulated Outage Window", annotation_position="top left",
            annotation_font=dict(color='#ff6b81', size=11)
        )

    # Titles and Layout formatting
    title_text = f"Large AR-MLP Outage Correction · June 12-24 Dataset"
    if len(gt_outage) > 0:
        title_text += f"<br><sup>RMSE in Outage: {rmse:.4f}m | MAE: {mae:.4f}m</sup>"

    fig.update_layout(
        title=dict(
            text=title_text,
            x=0.5, xanchor='center',
            font=dict(size=17, color='#ffffff', family='Inter, sans-serif')
        ),
        xaxis=dict(
            title='Time', gridcolor='#2a2a2a', color='#aaaaaa',
            rangeslider=dict(visible=True, thickness=0.04)
        ),
        yaxis=dict(
            title='Water Level / Distance (meters)', gridcolor='#2a2a2a', color='#aaaaaa',
            zeroline=False
        ),
        yaxis2=dict(
            title='Anomaly Probability', overlaying='y', side='right',
            range=[0, 1.1], gridcolor='#2a2a2a', color='#ff4757',
            showgrid=False, zeroline=False
        ),
        legend=dict(
            font=dict(color='#cccccc', size=12),
            bgcolor='rgba(13,13,26,0.8)',
            bordercolor='#333344', borderwidth=1,
            x=0.01, y=0.99, xanchor='left', yanchor='top'
        ),
        paper_bgcolor='#0d0d1a',
        plot_bgcolor='#111120',
        hovermode='x unified',
        template='plotly_dark',
        margin=dict(l=60, r=60, t=75, b=60),
        height=600
    )

    # Save to file
    os.makedirs(os.path.dirname(args.output_html), exist_ok=True)
    fig.write_html(args.output_html, include_plotlyjs='cdn')
    print(f"Interactive plot saved successfully -> {args.output_html}")

    print("\n--- Metrics Summary ---")
    print(f"Outage Start: {outage_start_dt}")
    print(f"Outage End:   {outage_end_dt}")
    if len(gt_outage) > 0:
        print(f"Outage RMSE:  {rmse:.4f}m")
        print(f"Outage MAE:   {mae:.4f}m")
    else:
        print("Warning: No ground truth available in selected outage window.")

if __name__ == '__main__':
    main()
