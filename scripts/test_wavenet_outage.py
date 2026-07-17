# -*- coding: utf-8 -*-
"""
test_wavenet_outage.py
----------------------
Evaluates the WaveNet TFLite model on the June-July 3-day simulated outage.

Inference contract
─────────────────
  Input A  (1, 96, 6)   — sliding window [wl_norm, recent_diurnal, day_sin, day_cos, half_day_sin, half_day_cos]
                          wl_norm = wl / 4.5.  During outages the wl position holds the
                          model's own previous prediction (autoregressive).
  Input B  (1, 1)        — outage_duration_norm = min(outage_step_count / 8.0, 1.0)
                          Computed from a trivial counter in the inference loop.
                          No water-usage knowledge encoded here.
  Output   (1, 1)        — predicted next water level, normalised [0, 1].
                          Multiply by 4.5 to convert to metres.

The outage gate (wl_temporal + wl_ar × (1 - odn)) lives inside the TFLite model.
No diurnal lookup table. No hardcoded usage patterns.

Output: plots/interactive_wavenet_june_july.html
"""

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
MODEL_PATH   = os.path.join(BASE_DIR, "models", "saved", "water_level_wavenet.tflite")

WL_MAX       = 4.5
PHYSICAL_MIN = 0.05
PHYSICAL_MAX = 4.45
WINDOW_SIZE  = 96
DATE_FMT     = "%d-%m-%Y %H:%M"
N_CHANNELS   = 7

BASE_THRESH  = 0.5
MAX_THRESH   = 1.5
THRESH_DECAY = 0.9


# ── Time feature helper ───────────────────────────────────────────────────────

def time_feats(ts: pd.Timestamp):
    """Returns [day_sin, day_cos, weekday_sin, weekday_cos, is_weekend]."""
    m = ts.hour * 60 + ts.minute
    d = m / 1440.0
    wd = ts.weekday() / 7.0
    is_weekend = 1.0 if ts.weekday() >= 5 else 0.0
    return [
        math.sin(2 * math.pi * d), math.cos(2 * math.pi * d),
        math.sin(2 * math.pi * wd), math.cos(2 * math.pi * wd),
        is_weekend
    ]


def window_row(ts: pd.Timestamp, wl_metres: float, diurnal_norm: float):
    """Build a single row: [wl_norm, diurnal_norm, day_sin, day_cos, weekday_sin, weekday_cos, is_weekend]."""
    wl_n = max(0.0, min(1.0, wl_metres / WL_MAX))
    return [wl_n, diurnal_norm] + time_feats(ts)


# ── TFLite inference ──────────────────────────────────────────────────────────

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


def run_wavenet(interp: tf.lite.Interpreter, seq_idx: int, out_idx: int,
                history: deque) -> float:
    """Runs a single causal step of the TFLite model."""
    seq_np = np.array(history, dtype=np.float32).reshape(1, WINDOW_SIZE, N_CHANNELS)
    interp.set_tensor(seq_idx, seq_np)
    interp.invoke()
    pred_norm = float(interp.get_tensor(out_idx)[0, 0])
    pred_norm = max(0.0, min(1.0, pred_norm))
    return pred_norm * WL_MAX


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=str, choices=['june-july', 'may-june', 'feb-may'], default='june-july',
                        help='Dataset to run simulation on')
    parser.add_argument('--outage-start', type=str, default=None,
                        help='Simulated outage start date (e.g. "06-25 19:00"). Overrides defaults.')
    parser.add_argument('--outage-end', type=str, default=None,
                        help='Simulated outage end date (e.g. "06-28 19:00"). Overrides defaults.')
    args = parser.parse_args()

    if args.dataset == 'june-july':
        OUTAGE_CSV = os.path.join(BASE_DIR, "data", "processed", "data-june6-july1_outage.csv")
        GT_CSV     = os.path.join(BASE_DIR, "data", "processed", "data-june6-july1_processed.csv")
        OUT_HTML   = os.path.join(BASE_DIR, "plots", "interactive_wavenet_june_july.html")
        SIM_OUTAGE_START = args.outage_start if args.outage_start else "06-25 19:00"
        SIM_OUTAGE_END   = args.outage_end if args.outage_end else "06-28 19:00"
        title_suffix = "Jun 24 – Jul 1"
    elif args.dataset == 'may-june':
        OUTAGE_CSV = os.path.join(BASE_DIR, "data", "processed", "data-may26-june18_processed.csv")
        GT_CSV     = os.path.join(BASE_DIR, "data", "processed", "data-may26-june18_processed.csv")
        OUT_HTML   = os.path.join(BASE_DIR, "plots", "interactive_wavenet_may_june.html")
        SIM_OUTAGE_START = args.outage_start if args.outage_start else "06-13 19:00"
        SIM_OUTAGE_END   = args.outage_end if args.outage_end else "06-16 19:00"
        title_suffix = "May 26 – Jun 18"
    else: # feb-may
        OUTAGE_CSV = os.path.join(BASE_DIR, "data", "processed", "combined_data.csv")
        GT_CSV     = os.path.join(BASE_DIR, "data", "processed", "filtered_data.csv")
        OUT_HTML   = os.path.join(BASE_DIR, "plots", "interactive_wavenet_feb_may.html")
        SIM_OUTAGE_START = args.outage_start if args.outage_start else "03-15 19:00"
        SIM_OUTAGE_END   = args.outage_end if args.outage_end else "03-18 19:00"
        title_suffix = "Feb 20 – May 26"

    print("-" * 60)
    print(f"  WaveNet Outage Tester — {args.dataset.title()} Dataset")
    print("-" * 60)

    # ── Load data ─────────────────────────────────────────────────────────────
    print(f"\nLoading outage dataset  : {OUTAGE_CSV}")
    df = pd.read_csv(OUTAGE_CSV)
    df['Time_datetime'] = pd.to_datetime(df['Time'], format=DATE_FMT)
    df = (df.set_index('Time_datetime')
            .resample('15min').ffill()
            .reset_index())
            
    if 'errorcode' not in df.columns:
        df['errorcode'] = 0
        
    df['wl_raw']    = df['Water Level'].ffill().bfill()
    df['errorcode'] = df['errorcode'].fillna(0).astype(int)

    print(f"Loading ground truth    : {GT_CSV}")
    df_gt = pd.read_csv(GT_CSV)
    df_gt['Time_datetime'] = pd.to_datetime(df_gt['Time'], format=DATE_FMT)
    df_gt = (df_gt.set_index('Time_datetime')
                  .resample('15min').ffill()
                  .reset_index())
    df_gt['wl_gt'] = df_gt['Water Level'].ffill().bfill()
    gt_map = dict(zip(df_gt['Time_datetime'], df_gt['wl_gt']))
    df['wl_gt'] = df['Time_datetime'].map(gt_map)

    # Restore other timeframes to actual data
    df['wl_raw'] = df['wl_gt']
    df['errorcode'] = 0
    
    # Inject simulated outage from configured timeframe
    if SIM_OUTAGE_START and SIM_OUTAGE_END:
        year = df['Time_datetime'].dt.year.iloc[0]
        outage_start = pd.to_datetime(f'{year}-{SIM_OUTAGE_START}:00')
        outage_end = pd.to_datetime(f'{year}-{SIM_OUTAGE_END}:00')
        outage_mask = (df['Time_datetime'] >= outage_start) & (df['Time_datetime'] <= outage_end)
        
        df.loc[outage_mask, 'errorcode'] = 5
        df.loc[outage_mask, 'wl_raw'] = 0.0

    print(f"Dataset : {df['Time_datetime'].min()} → {df['Time_datetime'].max()}  "
          f"({len(df)} rows)")

    # ── Load model ────────────────────────────────────────────────────────────
    print(f"\nLoading WaveNet TFLite  : {MODEL_PATH}")
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Model not found. Train the model first:\n  python scripts/train_wavenet.py\n"
            f"  Expected: {MODEL_PATH}")

    interp, seq_idx, out_idx = load_tflite(MODEL_PATH)
    model_size_kb = os.path.getsize(MODEL_PATH) / 1024
    print(f"  Model size : {model_size_kb:.1f} KB")

    # ── Initialise 96-step sliding window ────────────────────────────────────
    
    # We will use the first 96 steps of df to cleanly initialize the diurnal profile
    # and the history buffer, avoiding any flat 0.3 initialization bias.
    diurnal_profile = np.zeros(96, dtype=np.float32)
    
    for i in range(WINDOW_SIZE):
        ts = df['Time_datetime'].iloc[i]
        wl = float(df['wl_raw'].iloc[i])
        slot = (ts.hour * 60 + ts.minute) // 15
        if wl > 0.05 and wl < 4.45:
            diurnal_profile[slot] = min(max(wl / WL_MAX, 0.0), 1.0)
        else:
            diurnal_profile[slot] = 0.3

    history: deque = deque(maxlen=WINDOW_SIZE)
    for i in range(WINDOW_SIZE):
        ts = df['Time_datetime'].iloc[i]
        wl = float(df['wl_raw'].iloc[i])
        slot = (ts.hour * 60 + ts.minute) // 15
        history.append(window_row(ts, wl, diurnal_profile[slot]))

    print(f"\nBuffer initialised cleanly using first {WINDOW_SIZE} steps.")

    # ── Simulation loop ───────────────────────────────────────────────────────
    print("Running simulation...")

    wl_raw_arr   = df['wl_raw'].values
    ec_arr       = df['errorcode'].values
    times        = df['Time_datetime']
    start_time   = times.iloc[0]

    wl_corrected   = np.zeros(len(df), dtype=np.float64)
    is_anomaly_arr = np.zeros(len(df), dtype=np.int8)

    last_valid_wl   = float(wl_raw_arr[WINDOW_SIZE - 1])
    previous_valid_wl = float(wl_raw_arr[WINDOW_SIZE - 2])
    last_valid_time = int((times.iloc[WINDOW_SIZE - 1] - start_time).total_seconds() / 60)
    consecutive_anom = 0
    dyn_thresh       = BASE_THRESH
    buffer_poisoned  = False
    in_outage        = False

    for i in range(len(df)):
        if i < WINDOW_SIZE:
            # Warm-up period, pass through raw
            wl_corrected[i]   = float(wl_raw_arr[i])
            is_anomaly_arr[i] = 0
            continue
            
        ts  = times.iloc[i]
        ec  = int(ec_arr[i])
        wl  = float(wl_raw_arr[i])
        cur_t = int((ts - start_time).total_seconds() / 60)

        # ── Anomaly detection rules (same as existing scripts) ────────────────
        is_protocol = (ec in [1, 3]) or (ec == 5 and (wl == 0.0 or wl >= PHYSICAL_MAX))
        is_bounds   = (wl < PHYSICAL_MIN or wl >= PHYSICAL_MAX)
        sudden_zero = (wl == 0.0 and abs(wl - last_valid_wl) > BASE_THRESH)

        is_anom = False
        wl_corr = wl   # default: pass raw through

        if is_protocol or is_bounds or sudden_zero:
            # Hard anomaly: replace with model prediction
            is_anom = True
        else:
            gap = cur_t - last_valid_time

            if buffer_poisoned and gap > 25:
                # Buffer recovered from outage: re-seed from real reading
                slot = (ts.hour * 60 + ts.minute) // 15
                val_norm = min(max(wl / WL_MAX, 0.0), 1.0)
                diurnal_profile[slot] = 0.2 * val_norm + 0.8 * diurnal_profile[slot]
                history.append(window_row(ts, wl, diurnal_profile[slot]))
                buffer_poisoned   = False
                last_valid_wl     = wl
                last_valid_time   = cur_t
                consecutive_anom  = 0
                dyn_thresh        = BASE_THRESH
                wl_corr           = wl
            else:
                # Use WaveNet to check for residual anomaly
                pred     = run_wavenet(interp, seq_idx, out_idx, history)
                residual = abs(wl - pred)
                roc      = abs(wl - last_valid_wl)

                time_since = cur_t - last_valid_time
                dyn_thresh = (BASE_THRESH
                              + (dyn_thresh - BASE_THRESH)
                              * (THRESH_DECAY ** (time_since / 15.0)))

                if consecutive_anom > 5:
                    is_anom = False   # cap: don't flag indefinitely
                elif roc <= BASE_THRESH:
                    is_anom = False   # small change → trust sensor
                elif residual > dyn_thresh:
                    is_anom = True
                    consecutive_anom += 1
                    dyn_thresh = min(MAX_THRESH, dyn_thresh + 0.1)
                else:
                    is_anom = False

        if is_anom:
            if not in_outage:
                roc = last_valid_wl - previous_valid_wl
                wl_corr = last_valid_wl + roc
                in_outage = True
            else:
                wl_corr  = run_wavenet(interp, seq_idx, out_idx, history)
                
            wl_corr  = max(PHYSICAL_MIN, min(PHYSICAL_MAX, wl_corr))

            if cur_t - last_valid_time > 25:
                buffer_poisoned = True

            # Push predicted value into sliding window, use frozen diurnal profile
            slot = (ts.hour * 60 + ts.minute) // 15
            history.append(window_row(ts, wl_corr, diurnal_profile[slot]))
            wl_corrected[i] = wl_corr
            
        else:
            in_outage = False
            consecutive_anom = 0
            dyn_thresh       = BASE_THRESH
            last_valid_time  = cur_t
            previous_valid_wl = last_valid_wl
            last_valid_wl    = wl
            wl_corr          = wl

            # Push real value into sliding window and update diurnal profile
            slot = (ts.hour * 60 + ts.minute) // 15
            val_norm = min(max(wl / WL_MAX, 0.0), 1.0)
            diurnal_profile[slot] = 0.2 * val_norm + 0.8 * diurnal_profile[slot]
            history.append(window_row(ts, wl, diurnal_profile[slot]))

        wl_corrected[i]   = round(float(wl_corr), 3)
        is_anomaly_arr[i] = int(is_anom)

    # ── Metrics ───────────────────────────────────────────────────────────────
    outage_mask = df['errorcode'] == 5
    valid_gt    = ~df['wl_gt'].isna() & outage_mask

    print("\n=== Outage Region Metrics ===")
    if valid_gt.sum() > 0:
        gt_vals   = df['wl_gt'][valid_gt].values
        pred_vals = wl_corrected[valid_gt]
        rmse = float(np.sqrt(np.mean((pred_vals - gt_vals) ** 2)))
        mae  = float(np.mean(np.abs(pred_vals - gt_vals)))
        print(f"  RMSE        : {rmse:.4f} m")
        print(f"  MAE         : {mae:.4f} m")
        print(f"  GT samples  : {valid_gt.sum()}")
        print(f"  Outage steps: {int(outage_mask.sum())}")
    else:
        rmse, mae = 0.0, 0.0
        print("  Warning: no ground truth found in outage region.")

    n_detected = int(is_anomaly_arr.sum())
    n_outage   = int(outage_mask.sum())
    print(f"  Anomalies detected : {n_detected}  (outage region has {n_outage} steps)")

    # ── Plotly visualisation ──────────────────────────────────────────────────
    print("\nBuilding Plotly visualisation...")
    fig = go.Figure()

    # Raw sensor
    fig.add_trace(go.Scatter(
        x=df['Time_datetime'], y=df['wl_raw'],
        mode='lines', name='Raw Sensor (Outage)',
        line=dict(color='#f4a261', width=1.2, dash='dot'), opacity=0.7,
        hovertemplate='%{x}<br>Raw: %{y:.3f} m<extra></extra>'
    ))

    # Ground truth
    gt_out = df[outage_mask & ~df['wl_gt'].isna()]
    if len(gt_out) > 0:
        fig.add_trace(go.Scatter(
            x=gt_out['Time_datetime'], y=gt_out['wl_gt'],
            mode='lines', name='Ground Truth',
            line=dict(color='#57cc99', width=2.0, dash='dash'), opacity=0.9,
            hovertemplate='%{x}<br>GT: %{y:.3f} m<extra></extra>'
        ))

    # WaveNet corrected
    fig.add_trace(go.Scatter(
        x=df['Time_datetime'], y=wl_corrected,
        mode='lines', name='WaveNet Corrected',
        line=dict(color='#4cc9f0', width=2.4),
        hovertemplate='%{x}<br>WaveNet: %{y:.3f} m<extra></extra>'
    ))

    # Detected anomaly markers
    anom_df = df[is_anomaly_arr == 1]
    if len(anom_df) > 0:
        fig.add_trace(go.Scatter(
            x=anom_df['Time_datetime'], y=anom_df['wl_raw'],
            mode='markers', name='Detected Anomalies',
            marker=dict(color='#ff6b6b', size=5, symbol='x', opacity=0.7),
            hovertemplate='%{x}<br>Raw: %{y:.3f} m<extra></extra>'
        ))

    # Shade outage region
    out_rows = df[outage_mask]
    if len(out_rows) > 0:
        fig.add_vrect(
            x0=out_rows['Time_datetime'].iloc[0],
            x1=out_rows['Time_datetime'].iloc[-1],
            fillcolor='#e63946', opacity=0.12, line_width=0, layer='below',
            annotation_text='3-Day Simulated Outage (errorcode=5)',
            annotation_position='top left',
            annotation_font=dict(color='#ff6b6b', size=11)
        )

    # Layout
    metrics_str = (f"RMSE: {rmse:.3f} m  |  MAE: {mae:.3f} m"
                   if valid_gt.sum() > 0 else "No ground truth in outage region")
    title = (
        f"WaveNet Causal Dilated CNN — Outage Correction ({title_suffix})<br>"
        f"<sup>Model: {model_size_kb:.0f} KB  |  Receptive field: 127 steps (31.75 hr)  |  "
        f"{metrics_str}</sup>"
    )

    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor='center',
                   font=dict(size=16, color='#e0e0e0', family='Inter, sans-serif')),
        xaxis=dict(title='Timestamp', gridcolor='#252535', color='#aaaaaa',
                   rangeslider=dict(visible=True, thickness=0.04)),
        yaxis=dict(title='Water Level — distance from sensor (m)',
                   gridcolor='#252535', color='#aaaaaa', zeroline=False),
        legend=dict(font=dict(color='#cccccc', size=11),
                    bgcolor='rgba(15,15,28,0.85)',
                    bordercolor='#333355', borderwidth=1,
                    x=0.01, y=0.99, xanchor='left', yanchor='top'),
        paper_bgcolor='#0d0d1a',
        plot_bgcolor='#111120',
        hovermode='x unified',
        template='plotly_dark',
        margin=dict(l=60, r=60, t=95, b=60),
        height=620,
    )

    os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
    fig.write_html(OUT_HTML, include_plotlyjs='cdn')
    print(f"Saved → {OUT_HTML}")
    print("\nDone!")


if __name__ == '__main__':
    main()
