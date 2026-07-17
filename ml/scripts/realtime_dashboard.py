"""
Real-time MLP + Diurnal Anomaly Detection Dashboard
=====================================================
Feeds any raw CSV through the trained model one row per second, streaming
results to a Grafana-style browser dashboard via Server-Sent Events (SSE).

The browser UI lets the user pick a CSV from discovered files or type any
custom path, then (re)start the simulation without restarting the server.

Usage:
    python scripts/realtime_dashboard.py [--input PATH] [--port PORT]

Options:
    --input   Pre-select this CSV on startup (optional; auto-starts simulation)
    --port    HTTP port (default: 5050)
"""

import os
import sys
import math
import json
import time
import glob
import threading
import queue
from collections import deque

import numpy as np
import pandas as pd
import tensorflow as tf
from flask import Flask, Response, render_template_string, request, jsonify

# ── Project paths ─────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH  = os.path.join(BASE_DIR, "models", "saved", "ar_mlp.keras")
TRAIN_PATH  = os.path.join(BASE_DIR, "data", "processed", "training_dataset.csv")

app = Flask(__name__)

# ── Global simulation state ───────────────────────────────────────────────────
g_lock = threading.Lock()
g_clients: list = []          # SSE client queues
g_sim_thread: threading.Thread | None = None
g_stop_event = threading.Event()

g_state = {
    "running"     : False,
    "paused"      : False,
    "total_rows"  : 0,
    "current_row" : 0,
    "anomaly_count": 0,
    "csv_path"    : None,
    "csv_name"    : None,
    "error"       : None,
    "rate"        : 1.0,
}

# ── Cached model (loaded once) ────────────────────────────────────────────────
g_run_mlp   = None
g_model_lock = threading.Lock()

# ── Helpers ───────────────────────────────────────────────────────────────────
def build_time_features(ts):
    mins = ts.hour * 60 + ts.minute
    df   = mins / 1440.0
    rf   = mins / 720.0
    return {
        "hour_sin"   : math.sin(2 * math.pi * df),
        "hour_cos"   : math.cos(2 * math.pi * df),
        "refill_sin" : math.sin(2 * math.pi * rf),
        "refill_cos" : math.cos(2 * math.pi * rf),
        "day_of_week": float(ts.weekday()),
    }

def clean_wl(val):
    if pd.isna(val):
        return np.nan
    s = str(val).strip().lower()
    try:
        if s.endswith("mm"): return float(s[:-2].strip()) / 1000.0
        if s.endswith("m"):  return float(s[:-1].strip())
        return float(s)
    except ValueError:
        return np.nan

# ── Model loader (singleton) ──────────────────────────────────────────────────
def get_or_load_model():
    global g_run_mlp
    with g_model_lock:
        if g_run_mlp is not None:
            return g_run_mlp
        print("[server] Loading Keras model …")
        model = tf.keras.models.load_model(MODEL_PATH)
        w1c, b1c = model.get_layer("hidden1_cls").get_weights()
        w2c, b2c = model.get_layer("hidden2_cls").get_weights()
        woc, boc = model.get_layer("anomaly").get_weights()
        w1r, b1r = model.get_layer("hidden1_reg").get_weights()
        w2r, b2r = model.get_layer("hidden2_reg").get_weights()
        wor, bor = model.get_layer("wl").get_weights()

        relu    = lambda x: np.maximum(0, x)
        sigmoid = lambda x: 1.0 / (1.0 + np.exp(-x))

        def run(features):
            h1    = relu(features @ w1c + b1c)
            h2    = relu(h1 @ w2c + b2c)
            prob  = float(sigmoid(h2 @ woc + boc).flat[0])
            ri    = features[2:]
            h1r   = relu(ri @ w1r + b1r)
            h2r   = relu(h1r @ w2r + b2r)
            wl_h  = float(np.asarray(h2r @ wor + bor).flat[0])
            return prob, wl_h   # wl_h is height-space

        g_run_mlp = run
        print("[server] Model ready.")
        return run

# ── Diurnal profile ───────────────────────────────────────────────────────────
def build_diurnal(df_aligned):
    baseline = 2.21
    hist_min, hist_max = 0.095, 4.24

    if os.path.exists(TRAIN_PATH):
        try:
            dt = pd.read_csv(TRAIN_PATH)
            dt["wl_d"] = 4.5 - dt["wl_clean"]
            ct = dt[dt["is_anomaly"] == 0]
            if len(ct):
                hist_min = float(ct["wl_d"].min())
                hist_max = float(ct["wl_d"].max())
        except Exception as e:
            print(f"[server] Warning reading training bounds: {e}")

    clean = df_aligned[
        (df_aligned["is_missing"] == 0) &
        (df_aligned["wl_raw"].between(0.05, 4.44))
    ].copy()

    if len(clean) >= 96:
        span = (clean["Time"].max() - clean["Time"].min()).total_seconds() / 86400
        if span < 5:
            clean["dbin"] = clean["Time"].dt.hour * 4 + clean["Time"].dt.minute // 15
            dm = clean.groupby("dbin")["wl_raw"].mean().reindex(range(96))
            dm = dm.interpolate(limit_direction="both").fillna(baseline).values
            diurnal = np.tile(dm, 7)
        else:
            di = (clean["Time"].dt.dayofweek + 1) % 7
            clean["wbin"] = di * 96 + clean["Time"].dt.hour * 4 + clean["Time"].dt.minute // 15
            wm = clean.groupby("wbin")["wl_raw"].mean().reindex(range(672))
            diurnal = wm.interpolate(limit_direction="both").fillna(baseline).values
    elif os.path.exists(TRAIN_PATH):
        dt = pd.read_csv(TRAIN_PATH)
        dt["tp"] = pd.to_datetime(dt["Time"], format="%d-%m-%Y %H:%M")
        di = (dt["tp"].dt.dayofweek + 1) % 7
        dt["wbin"] = di * 96 + dt["tp"].dt.hour * 4 + dt["tp"].dt.minute // 15
        ct = dt[dt["is_anomaly"] == 0].copy()
        ct["wl_d"] = 4.5 - ct["wl_clean"]
        wm = ct.groupby("wbin")["wl_d"].mean().reindex(range(672))
        diurnal = wm.interpolate(limit_direction="both").fillna(baseline).values
    else:
        diurnal = np.full(672, baseline)

    hw  = 2
    pad = np.concatenate([diurnal[-hw:], diurnal, diurnal[:hw]])
    s   = pd.Series(pad).rolling(5, center=True).median().values
    diurnal = s[hw:-hw]
    print(f"[server] Diurnal ready. hist=[{hist_min:.3f}, {hist_max:.3f}]")
    return diurnal, hist_min, hist_max

# ── Preprocessor ──────────────────────────────────────────────────────────────
def preprocess(path):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()

    # Detect layout: "Time + value" (raw) vs "Time + wl_raw" (preprocessed distance)
    non_time = [c for c in df.columns if c.lower() != "time"]
    if not non_time:
        raise ValueError("CSV has no data column besides 'Time'.")

    # If the CSV already has a 'wl_raw' numeric column (preprocessed distance CSV)
    if "wl_raw" in df.columns and pd.api.types.is_numeric_dtype(df["wl_raw"]):
        df["Time"] = pd.to_datetime(df["Time"])
        df = df.sort_values("Time").reset_index(drop=True)
        df["is_missing"] = df["wl_raw"].isna().astype(int)
        df["wl_raw_filled"] = df["wl_raw"].ffill().bfill()
        di = (df["Time"].dt.dayofweek + 1) % 7
        df["weekly_bin"] = di * 96 + df["Time"].dt.hour * 4 + df["Time"].dt.minute // 15
        print(f"[server] Preprocessed CSV (distance space): {len(df)} rows.")
        return df

    # Otherwise treat as raw sensor CSV with string units (e.g. "1.34 m", "790 mm")
    wl_col = non_time[0]
    df["wl_raw_height"] = df[wl_col].apply(clean_wl)
    df["Time_parsed"]   = pd.to_datetime(df["Time"])
    df = df.drop(columns=["Time"])

    start = df["Time_parsed"].min().round("15min")
    end   = df["Time_parsed"].max().round("15min")
    grid  = pd.date_range(start=start, end=end, freq="15min")
    gdf   = pd.DataFrame({"GridTime": grid})

    al = pd.merge_asof(
        gdf, df.sort_values("Time_parsed"),
        left_on="GridTime", right_on="Time_parsed",
        direction="nearest", tolerance=pd.Timedelta(minutes=7),
    )
    al = al.rename(columns={"GridTime": "Time", "wl_raw_height": "_wl_h"})
    al = al[["Time", "_wl_h"]].copy()
    al["wl_raw"]     = 4.5 - al["_wl_h"]   # convert height → distance
    al["is_missing"] = al["wl_raw"].isna().astype(int)
    al["wl_raw_filled"] = al["wl_raw"].ffill().bfill()

    di = (al["Time"].dt.dayofweek + 1) % 7
    al["weekly_bin"] = di * 96 + al["Time"].dt.hour * 4 + al["Time"].dt.minute // 15
    print(f"[server] Raw sensor CSV → {len(al)} rows, {al['is_missing'].sum()} missing.")
    return al

# ── SSE broadcast ─────────────────────────────────────────────────────────────
def broadcast(payload: dict):
    msg = f"data: {json.dumps(payload)}\n\n"
    with g_lock:
        dead = []
        for q in g_clients:
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.append(q)
        for q in dead:
            g_clients.remove(q)

# ── Simulation thread ─────────────────────────────────────────────────────────
def simulation_thread(csv_path: str, stop_evt: threading.Event):
    print(f"[server] Starting simulation: {csv_path}")
    g_state.update({"running": True, "paused": False, "error": None,
                    "current_row": 0, "anomaly_count": 0})

    try:
        run_mlp = get_or_load_model()
        df      = preprocess(csv_path)
        diurnal, hist_min, hist_max = build_diurnal(df)
    except Exception as e:
        import traceback; traceback.print_exc()
        g_state.update({"running": False, "error": str(e)})
        broadcast({"type": "error", "msg": str(e)})
        return

    N = len(df)
    g_state["total_rows"] = N
    broadcast({
        "type" : "reset",
        "total": N,
        "name" : os.path.basename(csv_path),
        "start": df["Time"].iloc[0].isoformat(),
        "end"  : df["Time"].iloc[-1].isoformat(),
        "rate" : g_state.get("rate", 1.0),
    })

    wl_raw_filled = df["wl_raw_filled"].values
    is_missing    = df["is_missing"].values
    times         = df["Time"]
    weekly_bins   = df["weekly_bin"].values

    N_LAGS   = 8
    baseline = 2.21
    init_val = float(wl_raw_filled[0]) if N > 0 else baseline
    lag_buf  = deque([init_val] * N_LAGS, maxlen=N_LAGS)
    prev_ec  = 0
    in_anom_seq  = False
    anom_offset  = 0.0
    anom_seq_len = 0
    corr_hist    = [init_val]
    anom_count   = 0

    for i in range(N):
        if stop_evt.is_set():
            print("[server] Simulation stopped by request.")
            break

        while g_state["paused"] and not stop_evt.is_set():
            time.sleep(0.05)
        if stop_evt.is_set():
            break

        tick_start = time.time()

        ts      = times.iloc[i]
        wl_raw  = float(wl_raw_filled[i])
        missing = int(is_missing[i])

        # ── Build features ────────────────────────────────────────
        tf_feat  = build_time_features(ts)
        lags_d   = list(reversed(lag_buf))
        wl_raw_h = 4.5 - wl_raw
        lags_h   = [4.5 - l for l in lags_d]

        features = np.zeros(16, dtype=np.float32)
        features[0]    = 0.0
        features[1]    = wl_raw_h / 4.5
        features[2:10] = lags_h
        features[10]   = tf_feat["hour_sin"]
        features[11]   = tf_feat["hour_cos"]
        features[12]   = tf_feat["refill_sin"]
        features[13]   = tf_feat["refill_cos"]
        features[14]   = tf_feat["day_of_week"]
        features[15]   = float(prev_ec) / 5.0

        # ── Model inference ───────────────────────────────────────
        prob, wl_pred_h = run_mlp(features)
        wl_pred_dist    = float(np.clip(4.5 - wl_pred_h, hist_min, hist_max))

        # ── Anomaly detection ─────────────────────────────────────
        is_bounds = (wl_raw < 0.05 or wl_raw >= 4.45)
        
        # Check for recovery from missing data gap / outage / bounds anomaly
        prev_was_outage = False
        if i > 0:
            prev_wl_raw = float(wl_raw_filled[i-1])
            prev_was_outage = (
                is_missing[i-1] == 1 or
                prev_wl_raw < 0.05 or
                prev_wl_raw >= 4.45 or
                prev_ec in [1, 3]
            )
            
        just_recovered = (i > 0 and prev_was_outage
                          and not missing and not is_bounds)

        if just_recovered:
            is_anom      = False
            lag_buf      = deque([wl_raw] * N_LAGS, maxlen=N_LAGS)
            in_anom_seq  = False
            anom_seq_len = 0
        else:
            prev_wl = corr_hist[-1]
            is_roc  = abs(wl_raw - prev_wl) > 0.6
            is_anom = (prob > 0.5) or is_bounds or is_roc or bool(missing)

        # ── Corrected / displayed value ───────────────────────────
        #   Normal  → raw sensor value
        #   Anomaly → model prediction (MLP short / Diurnal long)
        if not is_anom:
            in_anom_seq  = False
            anom_seq_len = 0
            wl_corr      = wl_raw
            source       = "Raw"
        else:
            if not in_anom_seq:
                in_anom_seq = True
                anom_seq_len = 0
                last_wl  = corr_hist[-1]
                last_bin = int(weekly_bins[i - 1]) if i > 0 else int(weekly_bins[i])
                anom_offset = last_wl - diurnal[last_bin]

            anom_seq_len += 1
            anom_count   += 1

            if anom_seq_len <= 8:
                wl_corr = wl_pred_dist
                source  = "MLP"
            else:
                decay   = 0.98 ** (anom_seq_len - 8)
                wl_corr = diurnal[int(weekly_bins[i])] + anom_offset * decay
                source  = "Diurnal"

        wl_corr = float(np.clip(wl_corr, hist_min, hist_max))
        corr_hist.append(wl_corr)
        lag_buf.append(wl_corr)
        g_state["current_row"]    = i + 1
        g_state["anomaly_count"] = anom_count

        broadcast({
            "type"    : "tick",
            "idx"     : i,
            "time"    : ts.isoformat(),
            "wl_raw"  : round(wl_raw, 4),
            "wl_corr" : round(wl_corr, 4),
            "wl_mlp"  : round(wl_pred_dist, 4),
            "prob"    : round(prob, 4),
            "is_anom" : int(is_anom),
            "source"  : source,
            "progress": round((i + 1) / N * 100, 2),
            "anom_cnt": anom_count,
        })

        elapsed = time.time() - tick_start
        with g_lock:
            rate = g_state.get("rate", 1.0)
        delay = 1.0 / rate if rate > 0 else 1.0
        time.sleep(max(0.0, delay - elapsed))

    g_state["running"] = False
    if not stop_evt.is_set():
        broadcast({"type": "done", "total": N, "anomalies": anom_count})
    print("[server] Simulation finished.")

# ── CSV discovery ─────────────────────────────────────────────────────────────
def discover_csvs():
    patterns = [
        os.path.join(BASE_DIR, "data", "raw",       "*.csv"),
        os.path.join(BASE_DIR, "data", "processed", "*.csv"),
        os.path.join(BASE_DIR, "models", "saved",   "*.csv"),
    ]
    found = []
    for pat in patterns:
        for f in sorted(glob.glob(pat)):
            found.append({
                "path"  : f.replace("\\", "/"),
                "name"  : os.path.basename(f),
                "folder": os.path.basename(os.path.dirname(f)),
                "size"  : _human_size(os.path.getsize(f)),
            })
    return found

def _human_size(b):
    for unit in ("B","KB","MB","GB"):
        if b < 1024: return f"{b:.0f} {unit}"
        b /= 1024
    return f"{b:.1f} GB"

# ── Simulation lifecycle helpers ──────────────────────────────────────────────
def stop_simulation():
    global g_sim_thread, g_stop_event
    g_stop_event.set()
    if g_sim_thread and g_sim_thread.is_alive():
        g_sim_thread.join(timeout=3)
    g_state["running"] = False

def start_simulation(csv_path: str):
    global g_sim_thread, g_stop_event
    stop_simulation()
    g_stop_event = threading.Event()
    g_state.update({
        "csv_path": csv_path,
        "csv_name": os.path.basename(csv_path),
    })
    g_sim_thread = threading.Thread(
        target=simulation_thread,
        args=(csv_path, g_stop_event),
        daemon=True,
    )
    g_sim_thread.start()


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard HTML
# ─────────────────────────────────────────────────────────────────────────────
DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Water Level Monitor — Live</title>
  <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
  <style>
    :root{
      --bg:#0d0f14; --surface:#12151c; --panel:#171b24;
      --card:#1d2130; --bdr:#252936; --bdr2:#343a52;
      --accent:#5e7cf5; --ok:#22c55e; --warn:#f59e0b; --danger:#ef4444; --purple:#a78bfa;
      --t1:#e8ecf4; --t2:#8892a4; --t3:#4f566b;
    }
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--t1);min-height:100vh}

    /* ── NAV ── */
    .nav{display:flex;align-items:center;justify-content:space-between;
         padding:10px 20px;background:var(--surface);border-bottom:1px solid var(--bdr);
         position:sticky;top:0;z-index:200}
    .nav-left{display:flex;align-items:center;gap:12px}
    .logo{width:32px;height:32px;border-radius:8px;
          background:linear-gradient(135deg,#5e7cf5,#a78bfa);
          display:flex;align-items:center;justify-content:center;font-size:17px}
    .nav-title{font-size:14px;font-weight:600}
    .nav-file{font-size:11px;color:var(--t2);margin-left:8px;
              font-family:'JetBrains Mono',monospace}
    .badge{display:flex;align-items:center;gap:5px;padding:4px 11px;
           border-radius:20px;font-size:11px;font-weight:700;letter-spacing:.5px;
           border:1px solid;cursor:default}
    .badge.live  {background:rgba(239,68,68,.1); border-color:rgba(239,68,68,.3);  color:#ef4444}
    .badge.paused{background:rgba(245,158,11,.1);border-color:rgba(245,158,11,.3); color:#f59e0b}
    .badge.idle  {background:rgba(94,124,245,.1);border-color:rgba(94,124,245,.3); color:#5e7cf5}
    .badge.done  {background:rgba(34,197,94,.1); border-color:rgba(34,197,94,.3);  color:#22c55e}
    .dot{width:6px;height:6px;border-radius:50%;background:currentColor;animation:blink 1.2s infinite}
    @keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
    .nav-right{display:flex;align-items:center;gap:8px}
    .btn{padding:6px 14px;border-radius:6px;border:1px solid var(--bdr2);
         background:var(--card);color:var(--t1);font:500 12px 'Inter',sans-serif;
         cursor:pointer;transition:all .18s;display:flex;align-items:center;gap:5px}
    .btn:hover{border-color:var(--accent);background:rgba(94,124,245,.1)}
    .btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}
    .btn.primary:hover{background:#4a68e8}
    .btn.red{color:var(--danger);border-color:rgba(239,68,68,.35)}
    .btn.red:hover{background:rgba(239,68,68,.1)}

    /* ── DATASET LOADER PANEL ── */
    .loader-overlay{
      position:fixed;inset:0;background:rgba(7,9,14,.88);
      z-index:300;display:flex;align-items:center;justify-content:center;
      backdrop-filter:blur(4px);
    }
    .loader-box{
      background:var(--panel);border:1px solid var(--bdr2);border-radius:14px;
      padding:28px 30px;width:660px;max-width:95vw;
      box-shadow:0 24px 60px rgba(0,0,0,.6);
    }
    .loader-title{font-size:16px;font-weight:700;margin-bottom:4px}
    .loader-sub  {font-size:12px;color:var(--t2);margin-bottom:20px}
    .loader-section{margin-bottom:18px}
    .loader-section-title{font-size:11px;font-weight:600;color:var(--t2);
                          text-transform:uppercase;letter-spacing:.7px;margin-bottom:8px}
    /* File list */
    .file-list{display:flex;flex-direction:column;gap:5px;max-height:220px;overflow-y:auto}
    .file-item{
      display:flex;align-items:center;gap:10px;padding:8px 12px;
      background:var(--card);border:1px solid var(--bdr);border-radius:8px;
      cursor:pointer;transition:all .15s;
    }
    .file-item:hover{border-color:var(--accent);background:rgba(94,124,245,.08)}
    .file-item.selected{border-color:var(--accent);background:rgba(94,124,245,.12)}
    .file-folder{font-size:10px;color:var(--t3);background:var(--surface);
                 padding:2px 6px;border-radius:4px;font-family:'JetBrains Mono',monospace}
    .file-name  {font-size:12px;font-weight:500;flex:1}
    .file-size  {font-size:10px;color:var(--t3);font-family:'JetBrains Mono',monospace}
    /* Custom path input */
    .path-row{display:flex;gap:8px}
    .path-input{
      flex:1;background:var(--card);border:1px solid var(--bdr2);border-radius:8px;
      padding:9px 12px;color:var(--t1);font:13px 'JetBrains Mono',monospace;
      outline:none;transition:border-color .18s;
    }
    .path-input:focus{border-color:var(--accent)}
    .path-input::placeholder{color:var(--t3)}
    .loader-err{color:#fca5a5;font-size:12px;margin-top:8px;display:none}
    .loader-footer{display:flex;justify-content:flex-end;gap:8px;margin-top:20px;
                   border-top:1px solid var(--bdr);padding-top:16px}

    /* ── MAIN LAYOUT ── */
    .page{padding:14px 18px;display:flex;flex-direction:column;gap:12px}

    /* Progress */
    .prog-wrap{background:var(--panel);border:1px solid var(--bdr);border-radius:10px;padding:10px 16px}
    .prog-hdr{display:flex;justify-content:space-between;align-items:center;margin-bottom:7px}
    .prog-label{font-size:11px;font-weight:600;color:var(--t2);text-transform:uppercase;letter-spacing:.7px}
    .prog-right{display:flex;align-items:center;gap:12px}
    .prog-pct{font-size:12px;font-weight:700;font-family:'JetBrains Mono',monospace;color:var(--accent)}
    .prog-rows{font-size:11px;color:var(--t3);font-family:'JetBrains Mono',monospace}
    .prog-bg  {height:5px;background:var(--card);border-radius:3px;overflow:hidden}
    .prog-fill{height:100%;background:linear-gradient(90deg,var(--accent),var(--purple));
               border-radius:3px;transition:width .4s ease;width:0%}

    /* KPIs */
    .kpi-row{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}
    .kpi{background:var(--panel);border:1px solid var(--bdr);border-radius:10px;
         padding:13px 16px;position:relative;overflow:hidden}
    .kpi::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--kl,var(--accent))}
    .kpi-lbl{font-size:10px;font-weight:600;color:var(--t2);text-transform:uppercase;letter-spacing:.8px;margin-bottom:5px}
    .kpi-val{font-size:24px;font-weight:700;font-family:'JetBrains Mono',monospace;color:var(--kc,var(--t1))}
    .kpi-sub{font-size:10px;color:var(--t3);margin-top:3px}
    .kpi-ico{position:absolute;right:12px;top:11px;font-size:20px;opacity:.12}

    /* Charts */
    .chart-panel{background:var(--panel);border:1px solid var(--bdr);border-radius:10px;overflow:hidden}
    .chart-hdr{display:flex;align-items:center;justify-content:space-between;
               padding:10px 16px;border-bottom:1px solid var(--bdr)}
    .chart-title{font-size:12px;font-weight:600}
    .legend{display:flex;gap:14px}
    .leg{display:flex;align-items:center;gap:5px;font-size:10px;color:var(--t2)}
    .leg-line{width:16px;height:2px;border-radius:1px}
    #main-chart{height:400px}

    /* Bottom */
    .bottom{display:grid;grid-template-columns:1fr 320px;gap:12px}
    .log-panel{background:var(--panel);border:1px solid var(--bdr);border-radius:10px;overflow:hidden}
    .log-hdr  {display:flex;justify-content:space-between;align-items:center;
               padding:10px 16px;border-bottom:1px solid var(--bdr);font-size:12px;font-weight:600}
    .log-body {height:220px;overflow-y:auto;font-family:'JetBrains Mono',monospace;font-size:11px}
    .log-row  {display:flex;gap:8px;align-items:center;padding:5px 16px;
               border-bottom:1px solid rgba(37,41,54,.7)}
    .log-row:hover{background:rgba(255,255,255,.02)}
    .log-time {color:var(--t3);min-width:150px;font-size:10.5px}
    .tag{padding:1px 7px;border-radius:3px;font-size:9px;font-weight:700;letter-spacing:.5px}
    .tag-raw {background:rgba(34,197,94,.1); color:#22c55e}
    .tag-mlp {background:rgba(94,124,245,.12);color:#5e7cf5}
    .tag-diu {background:rgba(245,158,11,.1); color:#f59e0b}
    .log-vals{color:var(--t2);flex:1}
    .log-prob{color:var(--danger);font-weight:600}

    /* Stats */
    .stats{background:var(--panel);border:1px solid var(--bdr);border-radius:10px;
           padding:14px;display:flex;flex-direction:column;gap:10px}
    .stat-row{display:flex;justify-content:space-between;align-items:center}
    .stat-lbl{font-size:11px;color:var(--t2)}
    .stat-val{font-size:12px;font-weight:600;font-family:'JetBrains Mono',monospace}
    hr{border:none;border-top:1px solid var(--bdr)}
    .src-bars{display:flex;flex-direction:column;gap:7px}
    .src-bar-lbl{display:flex;justify-content:space-between;font-size:10px;margin-bottom:3px}
    .src-bg  {height:4px;background:var(--card);border-radius:2px;overflow:hidden}
    .src-fill{height:100%;border-radius:2px;transition:width .6s ease;width:0%}

    /* Idle screen */
    .idle-screen{
      display:flex;flex-direction:column;align-items:center;justify-content:center;
      height:calc(100vh - 52px);gap:12px;color:var(--t2);
    }
    .idle-icon{font-size:52px;opacity:.3}
    .idle-title{font-size:18px;font-weight:600;color:var(--t1)}
    .idle-sub{font-size:13px;text-align:center;max-width:380px;line-height:1.6}

    ::-webkit-scrollbar{width:4px}
    ::-webkit-scrollbar-thumb{background:var(--bdr2);border-radius:4px}

    /* Banner */
    #banner{display:none;padding:9px 16px;border-radius:8px;font-size:12px;font-weight:500;text-align:center}
    #banner.info{background:rgba(94,124,245,.12);border:1px solid rgba(94,124,245,.3);color:#a5b4fc}
    #banner.ok  {background:rgba(34,197,94,.1); border:1px solid rgba(34,197,94,.3); color:#86efac}
    #banner.err {background:rgba(239,68,68,.1); border:1px solid rgba(239,68,68,.3); color:#fca5a5}
    #rate-select option {
      background: var(--panel);
      color: var(--t1);
    }
  </style>
</head>
<body>

<!-- ── NAV ─────────────────────────────────────────────────────────────────── -->
<nav class="nav">
  <div class="nav-left">
    <div class="logo">&#127754;</div>
    <div>
      <span class="nav-title">Water Level Anomaly Monitor</span>
      <span class="nav-file" id="nav-file">— no dataset loaded —</span>
    </div>
  </div>
  <div class="nav-right">
    <span id="live-badge" class="badge idle"><span class="dot" style="animation:none"></span>IDLE</span>
    
    <div style="display:flex;align-items:center;gap:6px;background:var(--card);border:1px solid var(--bdr2);padding:5px 10px;border-radius:6px;font-size:12px">
      <span style="color:var(--t2)">Rate:</span>
      <select id="rate-select" onchange="changeRate(this.value)" style="background:transparent;border:none;color:var(--t1);font-family:inherit;font-size:12px;outline:none;cursor:pointer;font-weight:600">
        <option value="0.2">0.2/s</option>
        <option value="0.5">0.5/s</option>
        <option value="1.0" selected>1.0/s</option>
        <option value="2.0">2.0/s</option>
        <option value="5.0">5.0/s</option>
        <option value="10.0">10/s</option>
        <option value="20.0">20/s</option>
        <option value="50.0">50/s</option>
      </select>
    </div>

    <button class="btn primary" onclick="openLoader()">&#128193; Load Dataset</button>
    <button class="btn" id="btn-pause" onclick="togglePause()" disabled>&#9646;&#9646; Pause</button>
    <button class="btn red" onclick="stopSim()" id="btn-stop" disabled>&#9632; Stop</button>
  </div>
</nav>

<!-- ── DATASET LOADER OVERLAY ─────────────────────────────────────────────── -->
<div class="loader-overlay" id="loader-overlay">
  <div class="loader-box">
    <div class="loader-title">&#128193; Load Dataset</div>
    <div class="loader-sub">Select a discovered CSV or enter a custom file path. The simulation runs 1 sensor row per second.</div>

    <div class="loader-section">
      <div class="loader-section-title">Discovered CSV files</div>
      <div class="file-list" id="file-list">
        <div style="color:var(--t3);font-size:12px;padding:8px">Scanning…</div>
      </div>
    </div>

    <div class="loader-section">
      <div class="loader-section-title">Custom path</div>
      <div class="path-row">
        <input class="path-input" id="path-input" type="text"
               placeholder="C:/path/to/your/data.csv"
               oninput="onPathType()" />
      </div>
      <div class="loader-err" id="loader-err"></div>
    </div>

    <div class="loader-footer">
      <button class="btn" onclick="closeLoader()">Cancel</button>
      <button class="btn primary" id="btn-load" onclick="submitLoad()" disabled>
        &#9654; Start Simulation
      </button>
    </div>
  </div>
</div>

<!-- ── PAGE CONTENT ──────────────────────────────────────────────────────── -->
<div id="idle-view">
  <div class="idle-screen">
    <div class="idle-icon">&#127754;</div>
    <div class="idle-title">No dataset loaded</div>
    <div class="idle-sub">Click <strong>Load Dataset</strong> in the top bar to select a CSV file and start the real-time anomaly detection simulation.</div>
    <button class="btn primary" style="margin-top:8px" onclick="openLoader()">&#128193; Load Dataset</button>
  </div>
</div>

<div id="main-view" style="display:none">
  <div class="page">
    <div id="banner"></div>

    <!-- Progress -->
    <div class="prog-wrap">
      <div class="prog-hdr">
        <span class="prog-label">Dataset Replay Progress</span>
        <div class="prog-right">
          <span class="prog-rows" id="prog-rows">0 / 0 rows</span>
          <span class="prog-pct"  id="prog-pct">0.00%</span>
        </div>
      </div>
      <div class="prog-bg"><div class="prog-fill" id="prog-fill"></div></div>
    </div>

    <!-- KPIs -->
    <div class="kpi-row">
      <div class="kpi" style="--kl:#5e7cf5;--kc:#5e7cf5">
        <div class="kpi-lbl">Displayed Value</div>
        <div class="kpi-val" id="k-disp">—</div>
        <div class="kpi-sub" id="k-disp-sub">—</div>
        <div class="kpi-ico">&#128207;</div>
      </div>
      <div class="kpi" style="--kl:#f59e0b;--kc:#f59e0b">
        <div class="kpi-lbl">Raw Sensor</div>
        <div class="kpi-val" id="k-raw">—</div>
        <div class="kpi-sub">distance from sensor</div>
        <div class="kpi-ico">&#128268;</div>
      </div>
      <div class="kpi" style="--kl:#ef4444;--kc:#ef4444">
        <div class="kpi-lbl">Anomaly Score</div>
        <div class="kpi-val" id="k-prob">—</div>
        <div class="kpi-sub" id="k-anom-flag">MLP classifier</div>
        <div class="kpi-ico">&#9888;</div>
      </div>
      <div class="kpi" style="--kl:#22c55e;--kc:#22c55e">
        <div class="kpi-lbl">Anomalies Detected</div>
        <div class="kpi-val" id="k-anoms">0</div>
        <div class="kpi-sub">cumulative</div>
        <div class="kpi-ico">&#128270;</div>
      </div>
      <div class="kpi" style="--kl:#a78bfa;--kc:#a78bfa">
        <div class="kpi-lbl">Sensor Timestamp</div>
        <div class="kpi-val" id="k-ts" style="font-size:12px;padding-top:6px">—</div>
        <div class="kpi-sub">current row time</div>
        <div class="kpi-ico">&#128336;</div>
      </div>
    </div>

    <!-- Main chart -->
    <div class="chart-panel">
      <div class="chart-hdr">
        <span class="chart-title">Water Level — Distance from Sensor (m)</span>
        <div class="legend">
          <div class="leg"><div class="leg-line" style="background:#f59e0b;border-top:2px dashed #f59e0b;height:0"></div>Raw Sensor</div>
          <div class="leg"><div class="leg-line" style="background:#5e7cf5"></div>Displayed (raw / predicted)</div>
          <div class="leg" style="color:#ef4444">&#10005; Anomaly</div>
        </div>
      </div>
      <div id="main-chart"></div>
    </div>

    <!-- Bottom -->
    <div class="bottom">
      <div class="log-panel">
        <div class="log-hdr">
          <span>Event Log</span>
          <span id="log-cnt" style="font-size:11px;color:var(--t2)">0 events</span>
        </div>
        <div class="log-body" id="log-body"></div>
      </div>
      <div class="stats">
        <div style="font-size:12px;font-weight:600">Session Statistics</div>
        <hr/>
        <div class="stat-row"><span class="stat-lbl">Rows processed</span><span class="stat-val" id="s-rows">0</span></div>
        <div class="stat-row"><span class="stat-lbl">Anomaly rate</span>    <span class="stat-val" id="s-rate">—</span></div>
        <div class="stat-row"><span class="stat-lbl">Avg raw WL</span>      <span class="stat-val" id="s-avg-raw">—</span></div>
        <div class="stat-row"><span class="stat-lbl">Avg displayed WL</span><span class="stat-val" id="s-avg-corr">—</span></div>
        <div class="stat-row"><span class="stat-lbl">Peak raw WL</span>     <span class="stat-val" id="s-peak">—</span></div>
        <hr/>
        <div style="font-size:11px;font-weight:600">Correction Source</div>
        <div class="src-bars">
          <div>
            <div class="src-bar-lbl"><span style="color:#22c55e">Raw (normal)</span><span id="pct-raw">0%</span></div>
            <div class="src-bg"><div class="src-fill" id="fill-raw" style="background:#22c55e"></div></div>
          </div>
          <div>
            <div class="src-bar-lbl"><span style="color:#5e7cf5">MLP prediction</span><span id="pct-mlp">0%</span></div>
            <div class="src-bg"><div class="src-fill" id="fill-mlp" style="background:#5e7cf5"></div></div>
          </div>
          <div>
            <div class="src-bar-lbl"><span style="color:#f59e0b">Diurnal fallback</span><span id="pct-diu">0%</span></div>
            <div class="src-bg"><div class="src-fill" id="fill-diu" style="background:#f59e0b"></div></div>
          </div>
        </div>
      </div>
    </div>
  </div><!-- /page -->
</div><!-- /main-view -->

<script>
// ── Chart constants ───────────────────────────────────────────────────────────
const BG='#12151c', GRID='#1e2333', FONT='#6b7694';
const baseLayout={
  paper_bgcolor:BG, plot_bgcolor:BG,
  font:{color:FONT,family:'Inter,sans-serif',size:11},
  margin:{t:8,b:44,l:58,r:16},
  hovermode:'x unified',
  xaxis:{gridcolor:GRID,zerolinecolor:GRID,tickfont:{size:10},type:'date',tickformat:'%b %d\n%H:%M'},
};
const mainLayout={
  ...baseLayout,
  yaxis:{gridcolor:GRID,zerolinecolor:GRID,title:{text:'Distance (m)',font:{size:11}},
         range:[-0.05,4.7],tickfont:{size:10}},
  showlegend:false,
  shapes:[
    {type:'line',x0:0,x1:1,xref:'paper',y0:4.45,y1:4.45,line:{color:'rgba(239,68,68,.22)',width:1,dash:'dot'}},
    {type:'line',x0:0,x1:1,xref:'paper',y0:0.05,y1:0.05,line:{color:'rgba(239,68,68,.22)',width:1,dash:'dot'}},
  ],
};

const tRaw ={x:[],y:[],mode:'lines',line:{color:'#f59e0b',width:1,dash:'dot'},opacity:.65,type:'scatter'};
const tCorr={x:[],y:[],mode:'lines',line:{color:'#5e7cf5',width:2.2},type:'scatter'};
const tAnom={x:[],y:[],mode:'markers',marker:{color:'#ef4444',size:7,symbol:'x',line:{color:'#ef4444',width:2}},type:'scatter'};

function initCharts(){
  Plotly.newPlot('main-chart',[tRaw,tCorr,tAnom],mainLayout,{responsive:true,displaylogo:false});
}

// ── App state ─────────────────────────────────────────────────────────────────
let paused=false, simRunning=false;
let logCount=0, rowCount=0, totalRows=0;
let rawSum=0, corrSum=0, rawPeak=0;
let srcRaw=0, srcMlp=0, srcDiu=0;
let selectedPath=null;

// ── SSE ───────────────────────────────────────────────────────────────────────
const evtSrc = new EventSource('/stream');

evtSrc.onmessage = function(e){
  const d = JSON.parse(e.data);

  if(d.type==='reset'){
    resetDashboard(d);
    return;
  }
  if(d.type==='error'){
    showBanner('err','Error: '+d.msg);
    setBadge('idle');
    document.getElementById('btn-pause').disabled=true;
    document.getElementById('btn-stop').disabled=true;
    simRunning=false;
    return;
  }
  if(d.type==='done'){
    setBadge('done');
    showBanner('ok','Simulation complete — '+d.total+' rows, '+d.anomalies+' anomalies.');
    document.getElementById('btn-pause').disabled=true;
    document.getElementById('btn-stop').disabled=true;
    simRunning=false;
    return;
  }
  if(d.type!=='tick') return;

  rowCount=d.idx+1;
  rawSum +=d.wl_raw; corrSum+=d.wl_corr;
  rawPeak=Math.max(rawPeak,d.wl_raw);
  if(d.source==='Raw') srcRaw++;
  else if(d.source==='MLP') srcMlp++;
  else srcDiu++;

  const t=d.time;
  Plotly.extendTraces('main-chart',{x:[[t],[t]],y:[[d.wl_raw],[d.wl_corr]]},[0,1]);
  if(d.is_anom) Plotly.extendTraces('main-chart',{x:[[t]],y:[[d.wl_corr]]},[2]);

  if(d.is_anom) addLog(d);

  // KPIs
  const src=d.is_anom?(d.source==='MLP'?'MLP predicted':'Diurnal predicted'):'raw sensor';
  $('k-disp').textContent    = d.wl_corr.toFixed(3)+' m';
  $('k-disp-sub').textContent= src;
  $('k-raw').textContent     = d.wl_raw.toFixed(3)+' m';
  $('k-prob').textContent    = (d.prob*100).toFixed(1)+'%';
  const fl=$('k-anom-flag');
  fl.textContent  = d.is_anom?'ANOMALY':'normal';
  fl.style.color  = d.is_anom?'#ef4444':'';
  $('k-anoms').textContent   = d.anom_cnt;
  $('k-ts').textContent      = d.time.replace('T',' ');
  $('prog-pct').textContent  = d.progress.toFixed(2)+'%';
  $('prog-fill').style.width = d.progress+'%';
  $('prog-rows').textContent = rowCount+' / '+totalRows+' rows';
  $('s-rows').textContent    = rowCount;
  $('s-rate').textContent    = (d.anom_cnt/rowCount*100).toFixed(1)+'%';
  $('s-avg-raw').textContent = (rawSum/rowCount).toFixed(3)+' m';
  $('s-avg-corr').textContent= (corrSum/rowCount).toFixed(3)+' m';
  $('s-peak').textContent    = rawPeak.toFixed(3)+' m';

  const tot=srcRaw+srcMlp+srcDiu;
  function pct(v){return tot>0?(v/tot*100).toFixed(1):0;}
  [['raw',srcRaw],['mlp',srcMlp],['diu',srcDiu]].forEach(([k,v])=>{
    $('pct-'+k).textContent=pct(v)+'%';
    $('fill-'+k).style.width=pct(v)+'%';
  });
};

evtSrc.onerror=()=>showBanner('err','Connection lost — refresh to reconnect.');

// ── Reset dashboard when new dataset loads ────────────────────────────────────
function resetDashboard(d){
  rowCount=0; totalRows=d.total; rawSum=0; corrSum=0; rawPeak=0;
  srcRaw=0; srcMlp=0; srcDiu=0; logCount=0;
  document.getElementById('log-body').innerHTML='';
  $('log-cnt').textContent='0 events';
  $('prog-fill').style.width='0%';
  $('prog-pct').textContent='0.00%';
  $('prog-rows').textContent='0 / '+d.total+' rows';
  ['k-disp','k-raw','k-prob','k-anoms'].forEach(id=>$(id).textContent='—');
  $('k-ts').textContent='—';
  $('k-anom-flag').textContent='MLP classifier'; $('k-anom-flag').style.color='';
  $('pct-raw').textContent=$('pct-mlp').textContent=$('pct-diu').textContent='0%';
  $('fill-raw').style.width=$('fill-mlp').style.width=$('fill-diu').style.width='0%';

  // Reinit charts with empty traces
  Plotly.react('main-chart',[
    {...tRaw,x:[],y:[]},{...tCorr,x:[],y:[]},{...tAnom,x:[],y:[]}
  ],mainLayout,{responsive:true,displaylogo:false});

  if (d.rate) {
    setRateDropdown(d.rate);
  }
  $('nav-file').textContent=d.name;
  setBadge('live');
  simRunning=true;
  document.getElementById('btn-pause').disabled=false;
  document.getElementById('btn-stop').disabled=false;
  paused=false;
  document.getElementById('btn-pause').textContent='⏸ Pause';
  document.getElementById('idle-view').style.display='none';
  document.getElementById('main-view').style.display='block';
  showBanner('info','Loaded '+d.name+' ('+d.total+' rows) — simulating '+d.start.slice(0,10)+' to '+d.end.slice(0,10));
  setTimeout(hideBanner,5000);
}

// ── Loader UI ─────────────────────────────────────────────────────────────────
function openLoader(){
  document.getElementById('loader-overlay').style.display='flex';
  document.getElementById('loader-err').style.display='none';
  fetchCsvList();
}
function closeLoader(){
  document.getElementById('loader-overlay').style.display='none';
}

async function fetchCsvList(){
  const list=document.getElementById('file-list');
  list.innerHTML='<div style="color:var(--t3);font-size:12px;padding:8px">Scanning…</div>';
  const res=await fetch('/csvs');
  const data=await res.json();
  list.innerHTML='';
  if(!data.length){
    list.innerHTML='<div style="color:var(--t3);font-size:12px;padding:8px">No CSV files found in data/ or models/</div>';
    return;
  }
  data.forEach(f=>{
    const el=document.createElement('div');
    el.className='file-item';
    el.dataset.path=f.path;
    el.innerHTML=`
      <span class="file-folder">${f.folder}</span>
      <span class="file-name">${f.name}</span>
      <span class="file-size">${f.size}</span>`;
    el.onclick=()=>selectFile(el,f.path);
    list.appendChild(el);
  });
}

function selectFile(el,path){
  document.querySelectorAll('.file-item').forEach(e=>e.classList.remove('selected'));
  el.classList.add('selected');
  selectedPath=path;
  document.getElementById('path-input').value=path;
  document.getElementById('btn-load').disabled=false;
  document.getElementById('loader-err').style.display='none';
}

function onPathType(){
  const v=document.getElementById('path-input').value.trim();
  selectedPath=v||null;
  document.querySelectorAll('.file-item').forEach(e=>e.classList.remove('selected'));
  document.getElementById('btn-load').disabled=!v;
}

async function submitLoad(){
  const path=(document.getElementById('path-input').value||'').trim();
  if(!path) return;
  const errEl=document.getElementById('loader-err');
  errEl.style.display='none';
  document.getElementById('btn-load').disabled=true;
  document.getElementById('btn-load').textContent='Loading…';
  const res=await fetch('/load',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({path}),
  });
  const data=await res.json();
  if(data.ok){
    closeLoader();
    // UI update happens via SSE 'reset' event
  } else {
    errEl.textContent='Error: '+data.error;
    errEl.style.display='block';
  }
  document.getElementById('btn-load').disabled=false;
  document.getElementById('btn-load').textContent='&#9654; Start Simulation';
}

async function changeRate(val){
  const rate = parseFloat(val);
  await fetch('/control', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({action: 'set_rate', rate: rate})
  });
}

function setRateDropdown(rateVal) {
  const rateSel = $('rate-select');
  if (!rateSel) return;
  const rateStr = rateVal.toString();
  let exists = false;
  for (let i = 0; i < rateSel.options.length; i++) {
    if (rateSel.options[i].value === rateStr) {
      exists = true;
      break;
    }
  }
  if (!exists) {
    const opt = document.createElement('option');
    opt.value = rateStr;
    opt.textContent = rateVal.toFixed(1) + '/s';
    rateSel.appendChild(opt);
  }
  rateSel.value = rateStr;
}

// ── Controls ──────────────────────────────────────────────────────────────────
async function togglePause(){
  if(!simRunning) return;
  paused=!paused;
  await fetch('/control',{method:'POST',headers:{'Content-Type':'application/json'},
                body:JSON.stringify({action:paused?'pause':'resume'})});
  document.getElementById('btn-pause').textContent=paused?'▶ Resume':'⏸ Pause';
  setBadge(paused?'paused':'live');
  paused?showBanner('info','Paused.'):hideBanner();
}

async function stopSim(){
  if(!simRunning) return;
  await fetch('/control',{method:'POST',headers:{'Content-Type':'application/json'},
                body:JSON.stringify({action:'stop'})});
  simRunning=false; paused=false;
  setBadge('idle');
  document.getElementById('btn-pause').disabled=true;
  document.getElementById('btn-stop').disabled=true;
  showBanner('info','Simulation stopped.');
}

// ── Badge ─────────────────────────────────────────────────────────────────────
function setBadge(state){
  const b=document.getElementById('live-badge');
  const dot=b.querySelector('.dot');
  const labels={live:'LIVE',paused:'PAUSED',idle:'IDLE',done:'DONE'};
  b.className='badge '+state;
  dot.style.animation=state==='live'?'blink 1.2s infinite':'none';
  b.innerHTML=`<span class="dot" style="animation:${state==='live'?'blink 1.2s infinite':'none'}"></span>${labels[state]||state}`;
}

// ── Log ───────────────────────────────────────────────────────────────────────
const MAX_LOG=300;
function addLog(d){
  logCount++;
  $('log-cnt').textContent=logCount+' events';
  const body=$('log-body');
  const row=document.createElement('div');
  row.className='log-row';
  const cls=d.source==='Raw'?'tag-raw':d.source==='MLP'?'tag-mlp':'tag-diu';
  row.innerHTML=`
    <span class="log-time">${d.time.replace('T',' ')}</span>
    <span class="tag ${cls}">${d.source}</span>
    <span class="log-vals">raw=${d.wl_raw.toFixed(3)}m &rarr; ${d.wl_corr.toFixed(3)}m</span>
    <span class="log-prob">p=${(d.prob*100).toFixed(0)}%</span>`;
  body.insertBefore(row,body.firstChild);
  if(body.children.length>MAX_LOG) body.removeChild(body.lastChild);
}

// ── Utilities ─────────────────────────────────────────────────────────────────
function $(id){return document.getElementById(id)}
function showBanner(t,m){const b=$('banner');b.className=t;b.textContent=m;b.style.display='block'}
function hideBanner(){$('banner').style.display='none'}

// ── Init ──────────────────────────────────────────────────────────────────────
initCharts();

// Auto-open loader if no simulation is running
fetch('/status').then(r=>r.json()).then(s=>{
  if(!s.running) openLoader();
  if(s.rate) {
    setRateDropdown(s.rate);
  }
});
</script>
</body>
</html>"""

# ── Flask routes ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)

@app.route("/stream")
def stream():
    client_q: queue.Queue = queue.Queue(maxsize=600)
    with g_lock:
        g_clients.append(client_q)

    def generate():
        try:
            while True:
                try:
                    msg = client_q.get(timeout=25)
                    yield msg
                except queue.Empty:
                    yield ": keepalive\n\n"
        except GeneratorExit:
            with g_lock:
                if client_q in g_clients:
                    g_clients.remove(client_q)

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.route("/csvs")
def list_csvs():
    return jsonify(discover_csvs())

@app.route("/load", methods=["POST"])
def load():
    body = request.get_json(force=True)
    path = body.get("path", "").strip()
    if not path:
        return jsonify({"ok": False, "error": "No path provided."})
    # Normalise slashes
    path = os.path.normpath(path)
    if not os.path.isfile(path):
        return jsonify({"ok": False, "error": f"File not found: {path}"})
    if not path.lower().endswith(".csv"):
        return jsonify({"ok": False, "error": "File must be a .csv"})
    start_simulation(path)
    return jsonify({"ok": True})

@app.route("/control", methods=["POST"])
def control():
    body = request.get_json(force=True)
    act  = body.get("action", "")
    if act == "pause":   g_state["paused"] = True
    elif act == "resume": g_state["paused"] = False
    elif act == "stop":   stop_simulation()
    elif act == "set_rate":
        try:
            r = float(body.get("rate", 1.0))
            if r > 0:
                with g_lock:
                    g_state["rate"] = r
        except Exception:
            pass
    return jsonify({"ok": True})

@app.route("/status")
def status():
    return jsonify({k: g_state[k] for k in
                    ("running","paused","current_row","total_rows","anomaly_count","csv_name","error","rate")})

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    import argparse, webbrowser
    p = argparse.ArgumentParser(description="Real-time MLP+Diurnal dashboard")
    p.add_argument("--input", default=None, help="CSV path to auto-load on startup")
    p.add_argument("--port",  type=int, default=5050)
    p.add_argument("--rate",  type=float, default=1.0, help="Initial data rate in points/sec (default: 1.0)")
    args = p.parse_args()

    g_state["rate"] = args.rate

    if not os.path.exists(MODEL_PATH):
        print(f"[ERROR] Model not found: {MODEL_PATH}"); sys.exit(1)

    # Pre-load model weights so first request is instant
    try:
        get_or_load_model()
    except Exception as e:
        print(f"[ERROR] Failed to load model: {e}"); sys.exit(1)

    # Auto-start if --input provided
    if args.input:
        p2 = os.path.normpath(args.input)
        if not os.path.isfile(p2):
            print(f"[ERROR] Input file not found: {p2}"); sys.exit(1)
        start_simulation(p2)

    url = f"http://localhost:{args.port}"
    print(f"\n{'='*52}")
    print(f"  Water Level Anomaly Dashboard")
    print(f"  Open: {url}")
    print(f"  Tip : Click 'Load Dataset' to pick any CSV")
    print(f"{'='*52}\n")

    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(host="0.0.0.0", port=args.port, threaded=True, debug=False)

if __name__ == "__main__":
    main()
