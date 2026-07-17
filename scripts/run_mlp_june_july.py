"""
run_mlp_june_july.py
--------------------
Runs the Large AR-MLP on data-june6-july1_outage.csv.
Shows raw sensor signal vs model-corrected prediction.
No ground truth is available for this period.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import tensorflow as tf
import math
from collections import deque

BASE = "c:/Users/sahil/Desktop/ICFOSS/Anomaly Detection"
DATASET  = f"{BASE}/data/processed/data-june6-july1_outage.csv"
MODEL    = f"{BASE}/models/saved/large_ar_mlp.keras"
OUT_HTML = f"{BASE}/plots/interactive_mlp_june_july.html"

# ---------------------------------------------------------------------------
# Time feature builder (must match training exactly)
# ---------------------------------------------------------------------------
def build_time_features(ts):
    mins_day        = ts.hour * 60 + ts.minute
    day_frac        = mins_day / 1440.0
    half_day_frac   = mins_day / 720.0
    quarter_day_frac= mins_day / 360.0
    eighth_day_frac = mins_day / 180.0
    mins_week       = ts.weekday() * 1440 + mins_day
    week_frac       = mins_week / 10080.0
    return {
        "week_sin":        math.sin(2 * math.pi * week_frac),
        "week_cos":        math.cos(2 * math.pi * week_frac),
        "day_sin":         math.sin(2 * math.pi * day_frac),
        "day_cos":         math.cos(2 * math.pi * day_frac),
        "half_day_sin":    math.sin(2 * math.pi * half_day_frac),
        "half_day_cos":    math.cos(2 * math.pi * half_day_frac),
        "quarter_day_sin": math.sin(2 * math.pi * quarter_day_frac),
        "quarter_day_cos": math.cos(2 * math.pi * quarter_day_frac),
        "eighth_day_sin":  math.sin(2 * math.pi * eighth_day_frac),
        "eighth_day_cos":  math.cos(2 * math.pi * eighth_day_frac),
        "weekly_bin_norm": week_frac,
        "day_of_week":     float(ts.weekday()) / 6.0,
    }

# ---------------------------------------------------------------------------
# Load & resample
# ---------------------------------------------------------------------------
print("Loading data...")
df = pd.read_csv(DATASET)
df['Time_datetime'] = pd.to_datetime(df['Time'], format="%d-%m-%Y %H:%M")
df = df.set_index('Time_datetime')
df = df.resample('15min').ffill().reset_index()
df['wl_raw']    = df['Water Level'].ffill().bfill()
df['errorcode'] = df['errorcode'].fillna(0).astype(int)

print(f"Loaded {len(df)} rows  |  {df['Time_datetime'].min().date()} to {df['Time_datetime'].max().date()}")
ec5_rows = (df['errorcode'] == 5).sum()
print(f"Outage rows (errorcode=5): {ec5_rows}  ({ec5_rows * 15 / 60:.1f} hours)")

# ---------------------------------------------------------------------------
# Load model weights (numpy inference, no TF overhead per step)
# ---------------------------------------------------------------------------
print("Loading model...")
model = tf.keras.models.load_model(MODEL)

w_h1_cls, b_h1_cls = model.get_layer("hidden1_cls").get_weights()
w_h2_cls, b_h2_cls = model.get_layer("hidden2_cls").get_weights()
w_out_cls, b_out_cls = model.get_layer("anomaly").get_weights()

w_h1_reg, b_h1_reg = model.get_layer("hidden1_reg").get_weights()
w_h2_reg, b_h2_reg = model.get_layer("hidden2_reg").get_weights()
w_h3_reg, b_h3_reg = model.get_layer("hidden3_reg").get_weights()
w_out_reg, b_out_reg = model.get_layer("wl").get_weights()

def relu(x):    return np.maximum(0, x)
def sigmoid(x): return 1.0 / (1.0 + np.exp(-x))

def run_mlp(features):
    h1c  = relu(np.dot(features, w_h1_cls) + b_h1_cls)
    h2c  = relu(np.dot(h1c, w_h2_cls)      + b_h2_cls)
    prob = sigmoid(np.dot(h2c, w_out_cls)  + b_out_cls)[0]

    reg  = features[2:]
    h1r  = relu(np.dot(reg,  w_h1_reg) + b_h1_reg)
    h2r  = relu(np.dot(h1r,  w_h2_reg) + b_h2_reg)
    h3r  = relu(np.dot(h2r,  w_h3_reg) + b_h3_reg)
    wl   = (np.dot(h3r, w_out_reg) + b_out_reg)[0]
    return prob, wl

# ---------------------------------------------------------------------------
# Autoregressive inference loop
# ---------------------------------------------------------------------------
N_LAGS = 8
wl_raw_arr  = df['wl_raw'].values
errorcodes  = df['errorcode'].values
times       = df['Time_datetime']

wl_corrected     = np.zeros(len(df))
wl_preds_mlp     = np.zeros(len(df))
anomaly_probs    = np.zeros(len(df))
is_anomaly_pred  = np.zeros(len(df), dtype=int)
correction_src   = []

lag_buf = deque([wl_raw_arr[0]] * N_LAGS, maxlen=N_LAGS)
prev_ec = 0

print("Running inference...")
for i in range(len(df)):
    ts  = times.iloc[i]
    ec  = errorcodes[i]
    wl  = wl_raw_arr[i]
    tf_ = build_time_features(ts)
    lags = list(reversed(lag_buf))

    feat = np.zeros(23, dtype=np.float32)
    feat[0]  = float(ec) / 5.0
    feat[1]  = float(wl) / 4.5
    feat[2:10] = lags
    feat[10] = tf_["week_sin"];    feat[11] = tf_["week_cos"]
    feat[12] = tf_["day_sin"];     feat[13] = tf_["day_cos"]
    feat[14] = tf_["half_day_sin"];feat[15] = tf_["half_day_cos"]
    feat[16] = tf_["quarter_day_sin"]; feat[17] = tf_["quarter_day_cos"]
    feat[18] = tf_["eighth_day_sin"];  feat[19] = tf_["eighth_day_cos"]
    feat[20] = tf_["weekly_bin_norm"]; feat[21] = tf_["day_of_week"]
    feat[22] = float(prev_ec) / 5.0

    prob, wl_pred = run_mlp(feat)
    anomaly_probs[i]   = prob
    wl_preds_mlp[i]    = wl_pred

    is_anom = (prob > 0.5) or (ec == 5)
    is_anomaly_pred[i] = int(is_anom)

    if not is_anom:
        wl_corr = wl
        correction_src.append("Raw (normal)")
    else:
        wl_corr = wl_pred
        correction_src.append(f"MLP pred (p={prob:.2f}, ec={ec})")

    wl_corrected[i] = wl_corr
    lag_buf.append(wl_corr)
    prev_ec = ec

df['wl_corrected']    = wl_corrected
df['wl_pred_mlp']     = wl_preds_mlp
df['anomaly_prob']    = anomaly_probs
df['is_anomaly']      = is_anomaly_pred
df['correction_src']  = correction_src

n_anom = is_anomaly_pred.sum()
print(f"Anomaly steps detected: {n_anom} ({n_anom * 15 / 60:.1f} hours)")

# ---------------------------------------------------------------------------
# Detect outage shading regions (contiguous errorcode==5 blocks)
# ---------------------------------------------------------------------------
outage_regions = []
in_outage = False
for i, ec in enumerate(errorcodes):
    if ec == 5 and not in_outage:
        start_i = i
        in_outage = True
    elif ec != 5 and in_outage:
        outage_regions.append((df['Time_datetime'].iloc[start_i],
                               df['Time_datetime'].iloc[i - 1]))
        in_outage = False
if in_outage:
    outage_regions.append((df['Time_datetime'].iloc[start_i],
                           df['Time_datetime'].iloc[-1]))

print(f"Outage regions: {len(outage_regions)}")
for s, e in outage_regions:
    print(f"  {s}  ->  {e}  ({(e-s).days}d {(e-s).seconds//3600}h)")

# ---------------------------------------------------------------------------
# Build Plotly figure
# ---------------------------------------------------------------------------
print("Building interactive plot...")
fig = go.Figure()

# ── Raw sensor signal ──────────────────────────────────────────────────────
fig.add_trace(go.Scatter(
    x=df['Time_datetime'], y=df['wl_raw'],
    mode='lines', name='Raw Sensor',
    line=dict(color='#f4a261', width=1.5, dash='dot'),
    opacity=0.7,
    hovertemplate='<b>%{x}</b><br>Raw: %{y:.3f} m<extra></extra>'
))

# ── MLP corrected output ───────────────────────────────────────────────────
fig.add_trace(go.Scatter(
    x=df['Time_datetime'], y=df['wl_corrected'],
    mode='lines', name='MLP Corrected',
    line=dict(color='#4cc9f0', width=2.2),
    customdata=np.stack([df['anomaly_prob'], df['correction_src']], axis=1),
    hovertemplate=(
        '<b>%{x}</b><br>'
        'Corrected: %{y:.3f} m<br>'
        'Anomaly prob: %{customdata[0]:.3f}<br>'
        'Source: %{customdata[1]}<extra></extra>'
    )
))

# ── Anomaly probability as a faint secondary trace ─────────────────────────
fig.add_trace(go.Scatter(
    x=df['Time_datetime'], y=df['anomaly_prob'],
    mode='lines', name='Anomaly Probability',
    line=dict(color='#e63946', width=1.0),
    yaxis='y2', opacity=0.6,
    hovertemplate='<b>%{x}</b><br>Prob: %{y:.3f}<extra></extra>'
))

# ── Detected anomaly markers (on raw signal) ───────────────────────────────
anom_df = df[df['is_anomaly'] == 1]
fig.add_trace(go.Scatter(
    x=anom_df['Time_datetime'], y=anom_df['wl_raw'],
    mode='markers', name='Detected Anomaly',
    marker=dict(color='#e63946', size=5, symbol='x', opacity=0.5),
    hovertemplate='<b>%{x}</b><br>Raw: %{y:.3f} m<extra></extra>'
))

# ── Outage shading ─────────────────────────────────────────────────────────
for idx, (s, e) in enumerate(outage_regions):
    fig.add_vrect(
        x0=s, x1=e,
        fillcolor='#e63946', opacity=0.15, line_width=0, layer='below',
        annotation_text=f'Outage {idx+1}' if len(outage_regions) > 1 else 'Simulated Outage (ec=5)',
        annotation_position='top left',
        annotation_font=dict(color='#ff6b6b', size=11)
    )

# ── Layout ─────────────────────────────────────────────────────────────────
fig.update_layout(
    title=dict(
        text='Large AR-MLP · Jun 24 – Jul 1 2026 · Real Sensor Data with Simulated Outage',
        x=0.5, xanchor='center',
        font=dict(size=17, color='#e0e0e0', family='Inter, sans-serif')
    ),
    xaxis=dict(
        title='Time', gridcolor='#2a2a2a', color='#aaaaaa',
        rangeslider=dict(visible=True, thickness=0.04),
        rangeselector=dict(
            buttons=[
                dict(count=1,  label='1d',  step='day',  stepmode='backward'),
                dict(count=3,  label='3d',  step='day',  stepmode='backward'),
                dict(count=7,  label='1w',  step='day',  stepmode='backward'),
                dict(step='all', label='All')
            ],
            bgcolor='#1e1e2e', activecolor='#4cc9f0',
            font=dict(color='#cccccc')
        )
    ),
    yaxis=dict(
        title='Water Level (m)', gridcolor='#2a2a2a', color='#aaaaaa',
        zeroline=False
    ),
    yaxis2=dict(
        title='Anomaly Probability', overlaying='y', side='right',
        range=[0, 1.5], gridcolor='#2a2a2a', color='#e63946',
        showgrid=False, zeroline=False
    ),
    legend=dict(
        font=dict(color='#cccccc', size=12),
        bgcolor='rgba(20,20,30,0.8)',
        bordercolor='#333344', borderwidth=1,
        x=0.01, y=0.99, xanchor='left', yanchor='top'
    ),
    paper_bgcolor='#0d0d1a',
    plot_bgcolor='#111120',
    hovermode='x unified',
    template='plotly_dark',
    margin=dict(l=60, r=70, t=70, b=60),
    height=580,
)

fig.write_html(OUT_HTML, include_plotlyjs='cdn')
print(f"\nPlot saved -> {OUT_HTML}")
