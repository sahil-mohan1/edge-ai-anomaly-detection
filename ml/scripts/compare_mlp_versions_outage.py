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
MLP_V1_PATH  = os.path.join(BASE_DIR, "models", "saved", "large_ar_mlp.keras")
MLP_REG_PATH = os.path.join(BASE_DIR, "models", "saved", "large_ar_mlp_reg_opt.keras")

WL_MAX       = 4.5
PHYSICAL_MIN = 0.05
PHYSICAL_MAX = 4.45
DATE_FMT     = "%d-%m-%Y %H:%M"

# MLP Constants
N_LAGS = 8

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

def run_simulation(df, run_mlp_func):
    wl_raw_arr   = df['wl_raw'].values
    ec_arr       = df['errorcode'].values
    times        = df['Time_datetime']
    
    wl_corrected = np.zeros(len(df))
    init_val = wl_raw_arr[0]
    lag_buf = deque([init_val] * N_LAGS, maxlen=N_LAGS)
    prev_ec = 0

    for i in range(len(df)):
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
        
        prob, pred = run_mlp_func(feat)
        is_anom = (prob > 0.5) or (ec == 5)
        
        if not is_anom:
            wl_corr = wl
        else:
            wl_corr = pred
                
        wl_corrected[i] = wl_corr
        lag_buf.append(wl_corr)
        prev_ec = ec
        
    return wl_corrected

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=str, choices=['june-july', 'may-june'], default='june-july',
                        help='Dataset to run simulation on')
    parser.add_argument('--outage-start', type=str, default=None,
                        help='Simulated outage start date (e.g. "06-25 19:00"). Overrides defaults.')
    parser.add_argument('--outage-end', type=str, default=None,
                        help='Simulated outage end date (e.g. "06-28 19:00"). Overrides defaults.')
    args = parser.parse_args()

    if args.dataset == 'june-july':
        GT_CSV     = os.path.join(BASE_DIR, "data", "processed", "data-june6-july1_processed.csv")
        OUT_HTML   = os.path.join(BASE_DIR, "plots", "interactive_mlp_versions_comparison_june_july.html")
        SIM_OUTAGE_START = args.outage_start if args.outage_start else "06-25 19:00"
        SIM_OUTAGE_END   = args.outage_end if args.outage_end else "06-28 19:00"
        title_suffix = "Jun 24 – Jul 1"
    else:
        GT_CSV     = os.path.join(BASE_DIR, "data", "processed", "data-may26-june18_processed.csv")
        OUT_HTML   = os.path.join(BASE_DIR, "plots", "interactive_mlp_versions_comparison_may_june.html")
        SIM_OUTAGE_START = args.outage_start if args.outage_start else "06-13 19:00"
        SIM_OUTAGE_END   = args.outage_end if args.outage_end else "06-16 19:00"
        title_suffix = "May 26 – Jun 18"

    print(f"Loading ground truth dataset: {GT_CSV}")
    df = pd.read_csv(GT_CSV)
    df['Time_datetime'] = pd.to_datetime(df['Time'], format=DATE_FMT)
    df = df.set_index('Time_datetime').resample('15min').ffill().reset_index()
    df['wl_gt'] = df['Water Level'].ffill().bfill()
    df['wl_raw'] = df['wl_gt']
    df['errorcode'] = 0

    year = df['Time_datetime'].dt.year.iloc[0]
    outage_start_dt = pd.to_datetime(f'{year}-{SIM_OUTAGE_START}:00')
    outage_end_dt = pd.to_datetime(f'{year}-{SIM_OUTAGE_END}:00')
    outage_mask = (df['Time_datetime'] >= outage_start_dt) & (df['Time_datetime'] <= outage_end_dt)
    
    df.loc[outage_mask, 'errorcode'] = 5
    df.loc[outage_mask, 'wl_raw'] = 0.0

    # --- Run MLP Simulations ---
    print("\nRunning Large MLP v1 (Original) simulation...")
    run_mlp_v1 = get_mlp_runner(MLP_V1_PATH)
    wl_corrected_v1 = run_simulation(df, run_mlp_v1)

    print("\nRunning Large MLP (Regression Optimized) simulation...")
    run_mlp_reg = get_mlp_runner(MLP_REG_PATH)
    wl_corrected_reg = run_simulation(df, run_mlp_reg)

    # --- Plotting ---
    print("\nGenerating Plotly comparison...")
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['Time_datetime'], y=df['wl_raw'], mode='lines',
        name='Raw Sensor (w/ outage)', line=dict(color='#ff7f0e', width=1.0, dash='dot'), opacity=0.6,
        visible=True
    ))
    
    gt_mask = outage_mask & ~df['wl_gt'].isna()
    gt_outage = df[gt_mask]
    if len(gt_outage) > 0:
        fig.add_trace(go.Scatter(
            x=gt_outage['Time_datetime'], y=gt_outage['wl_gt'], mode='lines',
            name='Ground Truth (Outage Region)', line=dict(color='#2ca02c', width=2.0, dash='dash'), opacity=0.9,
            visible=True
        ))
    
    fig.add_trace(go.Scatter(
        x=df['Time_datetime'], y=wl_corrected_v1, mode='lines',
        name='Large MLP (Original)', line=dict(color='#d62728', width=2.0),
        visible=True
    ))

    fig.add_trace(go.Scatter(
        x=df['Time_datetime'], y=wl_corrected_reg, mode='lines',
        name='Large MLP (Reg Optimized)', line=dict(color='#4cc9f0', width=2.0),
        visible=True
    ))

    if len(df[outage_mask]) > 0:
        fig.add_vrect(
            x0=df[outage_mask]['Time_datetime'].iloc[0], 
            x1=df[outage_mask]['Time_datetime'].iloc[-1], 
            fillcolor="red", opacity=0.1, line_width=0, layer="below",
            annotation_text="Simulated Outage", annotation_position="top left",
            annotation_font=dict(color='red')
        )

    rmse_v1 = 0
    rmse_reg = 0
    if len(gt_outage) > 0:
        valid_gt_v1 = wl_corrected_v1[gt_mask]
        valid_gt_reg = wl_corrected_reg[gt_mask]
        gt_vals = gt_outage['wl_gt'].values
        
        rmse_v1 = np.sqrt(np.mean((valid_gt_v1 - gt_vals)**2))
        rmse_reg = np.sqrt(np.mean((valid_gt_reg - gt_vals)**2))

    title_text = f'MLP Versions Outage Comparison ({title_suffix})'
    if len(gt_outage) > 0:
        title_text += f'<br><sup>RMSE in Outage - Original: {rmse_v1:.3f}m | Reg Optimized: {rmse_reg:.3f}m</sup>'

    fig.update_layout(
        title=dict(text=title_text, x=0.5, xanchor='center', font=dict(size=16, color='#ffffff')),
        xaxis=dict(title='Time', gridcolor='#333333', color='#ffffff'),
        yaxis=dict(title='Water Level (meters)', gridcolor='#333333', color='#ffffff'),
        legend=dict(font=dict(color='#ffffff'), bgcolor='rgba(0,0,0,0)'),
        paper_bgcolor='#111111', plot_bgcolor='#111111', hovermode='x unified', template='plotly_dark'
    )
    
    os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
    fig.write_html(OUT_HTML)
    print(f"Plot saved successfully -> {OUT_HTML}")
    
    print("\n--- Summary ---")
    print(f"Outage Start: {outage_start_dt}")
    print(f"Outage End:   {outage_end_dt}")
    if len(gt_outage) > 0:
        print(f"Original RMSE: {rmse_v1:.4f}m")
        print(f"Reg Opt RMSE:  {rmse_reg:.4f}m")

if __name__ == '__main__':
    main()
