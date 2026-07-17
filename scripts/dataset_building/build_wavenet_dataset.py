# -*- coding: utf-8 -*-
"""
build_wavenet_dataset.py
------------------------
Builds training data for the WaveNet water level predictor.

Each sample:
  X_seq  : (96, 7) float32  — [wl_norm, recent_diurnal_norm, day_sin, day_cos, weekday_sin, weekday_cos, is_weekend]
                              wl_norm = wl_raw / 4.5, time features from real timestamps.
  y      : (1,)   float32  — next clean water level, normalised to [0, 1] (wl_clean / 4.5).
  y_mask : (1,)   float32  — 1.0 if y is valid (clean, in-bounds), else 0.0.

Synthetic outage injection (same strategy as build_large_training_dataset.py):
  - Only the wl_norm channel is corrupted with a slowly decaying AR simulation.
  - Time-feature channels (columns 2–5) always contain the REAL timestamp values.
  - This teaches the model to rely on time features when wl history is unreliable.

Output: data/processed/wavenet_dataset.npz
"""

import math
import random
import sys
import numpy as np
import pandas as pd
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────────────────
BASE_DIR = "c:/Users/sahil/Desktop/ICFOSS/Anomaly Detection"
RAW_CSV  = f"{BASE_DIR}/data/processed/combined_data.csv"
FILT_CSV = f"{BASE_DIR}/data/processed/filtered_data.csv"
OUT_NPZ  = f"{BASE_DIR}/data/processed/wavenet_dataset.npz"

WINDOW_SIZE         = 96     # 24 h at 15-min intervals
WL_MAX              = 4.5    # metres (normalisation divisor)
PHYSICAL_MIN        = 0.05
PHYSICAL_MAX        = 4.45
DATE_FMT            = "%d-%m-%Y %H:%M"
N_CHANNELS          = 7

N_SYNTHETIC_OUTAGES = 7
MIN_OUTAGE_STEPS    = 96     # 1 day
MAX_OUTAGE_STEPS    = 288    # 3 days
MIN_CLEAN_WINDOW    = WINDOW_SIZE + 16   # buffer for window placement
AR_DECAY            = 0.97
AR_NOISE            = 0.02
ODN_CAP             = 192    # 2 days to reach full outage status

# ── Helpers ──────────────────────────────────────────────────────────────────

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


def find_clean_windows(is_clean: np.ndarray, min_len: int):
    windows = []
    run_s = None
    for i, c in enumerate(is_clean):
        if c:
            if run_s is None: run_s = i
        else:
            if run_s is not None:
                if (i - run_s) >= min_len: windows.append((run_s, i - run_s))
                run_s = None
    if run_s is not None and (len(is_clean) - run_s) >= min_len:
        windows.append((run_s, len(is_clean) - run_s))
    return windows


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Building WaveNet Training Dataset")
    print("=" * 60)

    # ── [1] Load & align CSVs ────────────────────────────────────────────────
    print("\n[1/5] Loading source CSVs...")
    raw  = pd.read_csv(RAW_CSV)
    filt = pd.read_csv(FILT_CSV)

    raw['_ts']  = pd.to_datetime(raw['Time'],  format=DATE_FMT, dayfirst=True)
    filt['_ts'] = pd.to_datetime(filt['Time'], format=DATE_FMT, dayfirst=True)

    clean_map = dict(zip(filt['_ts'], filt['Water Level'].astype(float)))

    raw['wl_raw']   = raw['Water Level'].astype(float)
    raw['wl_clean'] = raw['_ts'].map(clean_map)   # NaN where no clean value exists

    # Resample to strict 15-min grid (forward-fill data gaps)
    raw = (raw.set_index('_ts')
              .resample('15min')
              .first()
              .reset_index()
              .rename(columns={'_ts': 'ts'}))

    raw['wl_raw']   = raw['wl_raw'].ffill().bfill()
    raw['wl_clean'] = raw['wl_clean'].ffill(limit=2)  # allow short gaps only

    N = len(raw)
    print(f"  {N:,} rows  |  {raw['ts'].min()} to {raw['ts'].max()}")

    # ── [2] Build per-step feature matrix ────────────────────────────────────
    print("\n[2/5] Computing feature arrays...")

    wl_raw_np   = raw['wl_raw'].values.astype(np.float32)
    wl_clean_np = raw['wl_clean'].values.astype(np.float32)

    wl_norm_np = np.clip(wl_raw_np / WL_MAX, 0.0, 1.0).astype(np.float32)
    tf_np      = np.array([time_feats(t) for t in raw['ts']], dtype=np.float32)  # (N, 5)

    # Calculate dynamic diurnal rolling profile (EMA, alpha=0.2)
    # Track the average of the last few days' usage for the current time of day
    recent_diurnal = np.zeros(N, dtype=np.float32)
    profile = np.zeros(96, dtype=np.float32)
    
    # Initialize perfectly with the first 24 hours of data
    for i in range(min(96, N)):
        ts = raw['ts'].iloc[i]
        slot = (ts.hour * 60 + ts.minute) // 15
        val = wl_clean_np[i]
        if not np.isnan(val) and PHYSICAL_MIN < val < PHYSICAL_MAX:
            profile[slot] = min(max(val / WL_MAX, 0.0), 1.0)
        else:
            profile[slot] = 0.3
            
    for i in range(N):
        ts = raw['ts'].iloc[i]
        slot = (ts.hour * 60 + ts.minute) // 15
        val = wl_clean_np[i]
        if not np.isnan(val) and PHYSICAL_MIN < val < PHYSICAL_MAX:
            val_norm = min(max(val / WL_MAX, 0.0), 1.0)
            profile[slot] = 0.2 * val_norm + 0.8 * profile[slot]
        recent_diurnal[i] = profile[slot]

    # feat[i] = [wl_norm, recent_diurnal_norm, day_sin, day_cos, weekday_sin, weekday_cos, is_weekend]
    feat = np.concatenate([wl_norm_np[:, None], recent_diurnal[:, None], tf_np], axis=1).astype(np.float32)  # (N, 7)

    # ── [3] Inject synthetic multi-day outages ────────────────────────────────
    print(f"\n[3/5] Injecting {N_SYNTHETIC_OUTAGES} synthetic outages...")

    is_clean_mask = (
        ~np.isnan(wl_clean_np) &
        (wl_clean_np > PHYSICAL_MIN) &
        (wl_clean_np < PHYSICAL_MAX)
    )
    global_mean_norm = float(np.nanmean(wl_clean_np[is_clean_mask])) / WL_MAX

    windows = find_clean_windows(is_clean_mask, MIN_CLEAN_WINDOW)
    print(f"  Found {len(windows)} clean windows ≥ {MIN_CLEAN_WINDOW} steps")
    for ws, wl in windows:
        print(f"    rows {ws}–{ws+wl}  ({wl} steps = {wl/96:.1f} days)")

    placed = 0
    used   = []
    margin = WINDOW_SIZE + 4

    for _ in range(N_SYNTHETIC_OUTAGES * 30):
        if placed >= N_SYNTHETIC_OUTAGES or not windows:
            break

        ws, wl_len = random.choice(windows)
        r = random.random()
        if r < 0.3:
            L = random.randint(MIN_OUTAGE_STEPS, MIN_OUTAGE_STEPS + 48)
        elif r < 0.7:
            L = random.randint(MIN_OUTAGE_STEPS + 48, MAX_OUTAGE_STEPS - 48)
        else:
            L = random.randint(MAX_OUTAGE_STEPS - 48, MAX_OUTAGE_STEPS)

        if L + 2 * margin > wl_len:
            continue

        os_ = random.randint(ws + margin, ws + wl_len - L - margin)
        oe  = os_ + L

        if any(os_ < re + margin and oe > rs - margin for rs, re in used):
            continue

        # Simulate corrupted wl values (AR decay towards global mean)
        pre_vals = feat[max(0, os_ - 8):os_, 0]
        sim = float(np.mean(pre_vals)) if len(pre_vals) > 0 else global_mean_norm

        for step in range(L):
            idx = os_ + step
            sim = AR_DECAY * sim + (1.0 - AR_DECAY) * global_mean_norm
            sim += float(np.random.normal(0.0, AR_NOISE))
            sim  = max(0.0, min(1.0, sim))

            feat[idx, 0] = sim                        # corrupt wl channel only

        used.append((os_, oe))
        placed += 1
        print(f"    Outage {placed}: rows {os_}–{oe} ({L} steps = {L/96:.1f} days)")

    print(f"  Placed {placed}/{N_SYNTHETIC_OUTAGES} outages")

    # ── [4] Build sliding windows ─────────────────────────────────────────────
    print("\n[4/5] Building sliding window sequences...")

    n_samples = N - WINDOW_SIZE
    X_seq  = np.zeros((n_samples, WINDOW_SIZE, N_CHANNELS), dtype=np.float32)
    y_arr  = np.empty((n_samples,),               dtype=np.float32)
    y_mask = np.empty((n_samples,),               dtype=np.float32)

    for i in range(n_samples):
        target    = wl_clean_np[i + WINDOW_SIZE]
        valid     = (not np.isnan(target)) and (PHYSICAL_MIN < target < PHYSICAL_MAX)

        X_seq[i]  = feat[i : i + WINDOW_SIZE]         # (96, 7)
        y_arr[i]  = (float(target) / WL_MAX) if valid else 0.0   # normalised [0,1]
        y_mask[i] = 1.0 if valid else 0.0

    n_val = int(y_mask.sum())
    print(f"  Total samples  : {n_samples:,}")
    print(f"  Valid targets  : {n_val:,}")

    # ── [5] Save ──────────────────────────────────────────────────────────────
    print("\n[5/5] Saving compressed dataset...")
    Path(OUT_NPZ).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT_NPZ,
                        X_seq=X_seq,
                        y=y_arr,     y_mask=y_mask)

    size_mb = Path(OUT_NPZ).stat().st_size / 1024 / 1024
    print(f"\n  Saved → {OUT_NPZ}  ({size_mb:.1f} MB)")
    print(f"  X_seq  : {X_seq.shape}  float32")
    print(f"  y      : {y_arr.shape}  float32  (normalised [0,1])")
    print(f"  y_mask : {y_mask.shape} float32")
    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()
