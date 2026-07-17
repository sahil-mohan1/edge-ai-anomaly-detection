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
WAVENET_PATH = os.path.join(BASE_DIR, "models", "saved", "water_level_wavenet.tflite")
MLP_PATH     = os.path.join(BASE_DIR, "models", "saved", "large_ar_mlp.keras")

WL_MAX       = 4.5
PHYSICAL_MIN = 0.05
PHYSICAL_MAX = 4.45
DATE_FMT     = "%d-%m-%Y %H:%M"

# WaveNet Constants
WINDOW_SIZE  = 96
N_CHANNELS   = 7
BASE_THRESH  = 0.5
MAX_THRESH   = 1.5
THRESH_DECAY = 0.9

# MLP Constants
N_LAGS = 8

# ── WaveNet Helpers ─────────────────────────────────────────────────────────

def time_feats_wavenet(ts: pd.Timestamp):
    m = ts.hour * 60 + ts.minute
    d = m / 1440.0
    wd = ts.weekday() / 7.0
    is_weekend = 1.0 if ts.weekday() >= 5 else 0.0
    return [
        math.sin(2 * math.pi * d), math.cos(2 * math.pi * d),
        math.sin(2 * math.pi * wd), math.cos(2 * math.pi * wd),
        is_weekend
    ]

def window_row_wavenet(ts: pd.Timestamp, wl_metres: float, diurnal_norm: float):
    wl_n = max(0.0, min(1.0, wl_metres / WL_MAX))
    return [wl_n, diurnal_norm] + time_feats_wavenet(ts)

def load_tflite(model_path: str):
    interp = tf.lite.Interpreter(model_path=model_path)
    interp.allocate_tensors()
    seq_idx = -1
    for d in interp.get_input_details():
        if list(d['shape']) == [1, WINDOW_SIZE, N_CHANNELS]:
            seq_idx = d['index']
    out_idx = interp.get_output_details()[0]['index']
    if seq_idx == -1:
        raise RuntimeError("Cannot identify model inputs by shape.")
    return interp, seq_idx, out_idx

def run_wavenet(interp: tf.lite.Interpreter, seq_idx: int, out_idx: int, history: deque) -> float:
    seq_np = np.array(history, dtype=np.float32).reshape(1, WINDOW_SIZE, N_CHANNELS)
    interp.set_tensor(seq_idx, seq_np)
    interp.invoke()
    pred_norm = float(interp.get_tensor(out_idx)[0, 0])
    pred_norm = max(0.0, min(1.0, pred_norm))
    return pred_norm * WL_MAX

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

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=str, choices=['june-july', 'may-june'], default='may-june',
                        help='Dataset to run simulation on')
    parser.add_argument('--outage-start', type=str, default=None,
                        help='Simulated outage start date (e.g. "06-25 19:00"). Overrides defaults.')
    parser.add_argument('--outage-end', type=str, default=None,
                        help='Simulated outage end date (e.g. "06-28 19:00"). Overrides defaults.')
    args = parser.parse_args()

    if args.dataset == 'june-july':
        GT_CSV     = os.path.join(BASE_DIR, "data", "processed", "data-june6-july1_processed.csv")
        OUT_HTML   = os.path.join(BASE_DIR, "plots", "interactive_model_comparison_june_july.html")
        SIM_OUTAGE_START = args.outage_start if args.outage_start else "06-25 19:00"
        SIM_OUTAGE_END   = args.outage_end if args.outage_end else "06-28 19:00"
        title_suffix = "Jun 24 – Jul 1"
    else:
        GT_CSV     = os.path.join(BASE_DIR, "data", "processed", "data-may26-june18_processed.csv")
        OUT_HTML   = os.path.join(BASE_DIR, "plots", "interactive_model_comparison_may_june.html")
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

    wl_raw_arr   = df['wl_raw'].values
    ec_arr       = df['errorcode'].values
    times        = df['Time_datetime']

    # --- Run MLP Simulation ---
    print("\nRunning Large MLP v1 simulation...")
    run_mlp = get_mlp_runner(MLP_PATH)
    wl_corrected_mlp = np.zeros(len(df))
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
        
        prob, pred = run_mlp(feat)
        is_anom = (prob > 0.5) or (ec == 5)
        
        if not is_anom:
            wl_corr = wl
        else:
            wl_corr = pred
                
        wl_corrected_mlp[i] = wl_corr
        lag_buf.append(wl_corr)
        prev_ec = ec

    # --- Run WaveNet Simulation ---
    print("\nRunning WaveNet simulation...")
    interp, seq_idx, out_idx = load_tflite(WAVENET_PATH)
    wl_corrected_wavenet = np.zeros(len(df))
    
    diurnal_profile = np.zeros(96, dtype=np.float32)
    for i in range(WINDOW_SIZE):
        ts = times.iloc[i]
        wl = float(wl_raw_arr[i])
        slot = (ts.hour * 60 + ts.minute) // 15
        if 0.05 < wl < 4.45:
            diurnal_profile[slot] = min(max(wl / WL_MAX, 0.0), 1.0)
        else:
            diurnal_profile[slot] = 0.3

    history = deque(maxlen=WINDOW_SIZE)
    for i in range(WINDOW_SIZE):
        ts = times.iloc[i]
        wl = float(wl_raw_arr[i])
        slot = (ts.hour * 60 + ts.minute) // 15
        history.append(window_row_wavenet(ts, wl, diurnal_profile[slot]))

    start_time   = times.iloc[0]
    last_valid_wl   = float(wl_raw_arr[WINDOW_SIZE - 1])
    previous_valid_wl_wavenet = float(wl_raw_arr[WINDOW_SIZE - 2])
    last_valid_time = int((times.iloc[WINDOW_SIZE - 1] - start_time).total_seconds() / 60)
    consecutive_anom_wavenet = 0
    dyn_thresh       = BASE_THRESH
    buffer_poisoned  = False
    in_outage_wavenet = False

    for i in range(len(df)):
        if i < WINDOW_SIZE:
            wl_corrected_wavenet[i] = float(wl_raw_arr[i])
            continue
            
        ts  = times.iloc[i]
        ec  = int(ec_arr[i])
        wl  = float(wl_raw_arr[i])
        cur_t = int((ts - start_time).total_seconds() / 60)

        is_protocol = (ec in [1, 3]) or (ec == 5 and (wl == 0.0 or wl >= PHYSICAL_MAX))
        is_bounds   = (wl < PHYSICAL_MIN or wl >= PHYSICAL_MAX)
        sudden_zero = (wl == 0.0 and abs(wl - last_valid_wl) > BASE_THRESH)

        is_anom = False
        wl_corr = wl

        if is_protocol or is_bounds or sudden_zero:
            is_anom = True
        else:
            gap = cur_t - last_valid_time
            if buffer_poisoned and gap > 25:
                slot = (ts.hour * 60 + ts.minute) // 15
                val_norm = min(max(wl / WL_MAX, 0.0), 1.0)
                diurnal_profile[slot] = 0.2 * val_norm + 0.8 * diurnal_profile[slot]
                history.append(window_row_wavenet(ts, wl, diurnal_profile[slot]))
                buffer_poisoned   = False
                last_valid_wl     = wl
                last_valid_time   = cur_t
                consecutive_anom_wavenet  = 0
                dyn_thresh        = BASE_THRESH
                wl_corr           = wl
            else:
                pred     = run_wavenet(interp, seq_idx, out_idx, history)
                residual = abs(wl - pred)
                roc      = abs(wl - last_valid_wl)

                time_since = cur_t - last_valid_time
                dyn_thresh = (BASE_THRESH + (dyn_thresh - BASE_THRESH) * (THRESH_DECAY ** (time_since / 15.0)))

                if consecutive_anom_wavenet > 5:
                    is_anom = False
                elif roc <= BASE_THRESH:
                    is_anom = False
                elif residual > dyn_thresh:
                    is_anom = True
                    consecutive_anom_wavenet += 1
                    dyn_thresh = min(MAX_THRESH, dyn_thresh + 0.1)
                else:
                    is_anom = False

        if is_anom:
            if not in_outage_wavenet:
                roc = last_valid_wl - previous_valid_wl_wavenet
                wl_corr = last_valid_wl + roc
                in_outage_wavenet = True
            else:
                wl_corr = run_wavenet(interp, seq_idx, out_idx, history)
            wl_corr = max(PHYSICAL_MIN, min(PHYSICAL_MAX, wl_corr))
            if cur_t - last_valid_time > 25:
                buffer_poisoned = True
            slot = (ts.hour * 60 + ts.minute) // 15
            history.append(window_row_wavenet(ts, wl_corr, diurnal_profile[slot]))
            wl_corrected_wavenet[i] = wl_corr
        else:
            in_outage_wavenet = False
            consecutive_anom_wavenet = 0
            dyn_thresh       = BASE_THRESH
            last_valid_time  = cur_t
            previous_valid_wl_wavenet = last_valid_wl
            last_valid_wl    = wl
            wl_corr          = wl
            slot = (ts.hour * 60 + ts.minute) // 15
            val_norm = min(max(wl / WL_MAX, 0.0), 1.0)
            diurnal_profile[slot] = 0.2 * val_norm + 0.8 * diurnal_profile[slot]
            history.append(window_row_wavenet(ts, wl, diurnal_profile[slot]))
            
        wl_corrected_wavenet[i] = round(float(wl_corr), 3)

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
        x=df['Time_datetime'], y=wl_corrected_mlp, mode='lines',
        name='Large MLP v1 Corrected', line=dict(color='#d62728', width=2.0),
        visible=True
    ))

    fig.add_trace(go.Scatter(
        x=df['Time_datetime'], y=wl_corrected_wavenet, mode='lines',
        name='WaveNet Corrected', line=dict(color='#4cc9f0', width=2.0),
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

    rmse_mlp = 0
    rmse_wavenet = 0
    if len(gt_outage) > 0:
        valid_gt_mlp = wl_corrected_mlp[gt_mask]
        valid_gt_wavenet = wl_corrected_wavenet[gt_mask]
        gt_vals = gt_outage['wl_gt'].values
        
        rmse_mlp = np.sqrt(np.mean((valid_gt_mlp - gt_vals)**2))
        rmse_wavenet = np.sqrt(np.mean((valid_gt_wavenet - gt_vals)**2))

    title_text = f'MLP vs WaveNet Outage Comparison ({title_suffix})'
    if len(gt_outage) > 0:
        title_text += f'<br><sup>RMSE in Outage - MLP: {rmse_mlp:.3f}m | WaveNet: {rmse_wavenet:.3f}m</sup>'

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
        print(f"MLP RMSE:     {rmse_mlp:.4f}m")
        print(f"WaveNet RMSE: {rmse_wavenet:.4f}m")

if __name__ == '__main__':
    main()
