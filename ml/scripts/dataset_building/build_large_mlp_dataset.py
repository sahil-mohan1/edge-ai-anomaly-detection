"""
build_large_training_dataset.py
--------------------------
Builds a dataset for the Large AR-MLP with expanded Fourier features.

V1: Expanded Fourier features for the original Large AR-MLP model.
(V2 synthetic outages removed).

Output: data/processed/large_training_dataset.csv
"""

import argparse
import math
import random
import sys
from collections import deque
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATE_FMT    = "%d-%m-%Y %H:%M"
N_LAGS      = 8
DEFAULT_OUT = "c:/Users/sahil/Desktop/ICFOSS/Anomaly Detection/data/processed/large_training_dataset.csv"
MAX_CONSISTENCY_STEP_M = 0.35

RAW_CSV      = "c:/Users/sahil/Desktop/ICFOSS/Anomaly Detection/data/processed/combined_data.csv"
FILTERED_CSV = "c:/Users/sahil/Desktop/ICFOSS/Anomaly Detection/data/processed/filtered_data.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_raw(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["_ts"] = pd.to_datetime(df["Time"], format=DATE_FMT, dayfirst=True)
    df = df.sort_values("_ts").reset_index(drop=True)
    df = df.rename(columns={"Water Level": "wl_raw"})
    return df

def load_filtered(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["_ts"] = pd.to_datetime(df["Time"], format=DATE_FMT, dayfirst=True)
    df = df.sort_values("_ts").reset_index(drop=True)
    df = df.rename(columns={"Water Level": "wl_clean_src"})
    return df

def build_time_features(ts: pd.Timestamp) -> dict:
    mins_day = ts.hour * 60 + ts.minute
    day_frac = mins_day / 1440.0
    half_day_frac = mins_day / 720.0
    quarter_day_frac = mins_day / 360.0
    eighth_day_frac = mins_day / 180.0
    
    # Weekly features
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

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_dataset(out_path: str) -> None:
    print("\n" + "=" * 60)
    print("  Building Large MLP Training Dataset")
    print("=" * 60)

    print("\n[1/7] Loading source files ...")
    raw = load_raw(RAW_CSV)
    filt = load_filtered(FILTERED_CSV)

    print("\n[2/7] Computing anomaly labels ...")
    clean_ts_set = set(filt["_ts"])
    raw["is_anomaly"] = raw["_ts"].apply(lambda t: 0 if t in clean_ts_set else 1)

    filt_map = dict(zip(filt["_ts"], filt["wl_clean_src"]))
    raw["wl_clean"] = raw["_ts"].apply(lambda t: filt_map.get(t, float("nan")))

    # --- Pass 1: Build records WITHOUT random spike injection ---
    # This keeps clean windows intact for outage placement
    print("\n[3/7] Building lag and time features (without random spikes) ...")
    lag_buf      = deque([0.0] * N_LAGS, maxlen=N_LAGS)
    prev_ec      = 0
    records      = []

    for _, row in raw.iterrows():
        ts        = row["_ts"]
        ec        = int(row["errorcode"])
        wl_raw    = float(row["wl_raw"])
        is_anom   = int(row["is_anomaly"])
        wl_clean  = row["wl_clean"]

        if is_anom == 0 and ec in [5]:
            last_clean = lag_buf[-1] if lag_buf else 0.0
            if last_clean > 0.0 and abs(wl_raw - last_clean) > MAX_CONSISTENCY_STEP_M:
                is_anom = 1
                wl_clean = float("nan")

        # NOTE: Random spike injection is DEFERRED to after outage placement

        lags = {f"wl_lag_{i+1}": val for i, val in enumerate(reversed(lag_buf))}
        time_feat = build_time_features(ts)

        rec = {
            "Time"          : row["Time"],
            "errorcode"     : ec,
            "wl_raw"        : wl_raw,
            "is_anomaly"    : is_anom,
            "wl_clean"      : wl_clean,
            "errorcode_norm": float(ec) / 5.0,
            "wl_raw_norm"   : float(wl_raw) / 4.5,
            **lags,
            **time_feat,
            "prev_errorcode": float(prev_ec) / 5.0,
        }
        records.append(rec)

        if not is_anom and not pd.isna(wl_clean):
            lag_buf.append(float(wl_clean))

        prev_ec = ec

    # --- Pass 2: Apply random spike injection to non-outage clean rows ---
    print(f"\n[4/7] Injecting random synthetic spikes ...")
    spike_count = 0
    for rec in records:
        # Only spike non-anomaly rows
        if rec["is_anomaly"] == 0:
            if random.random() < 0.02:  # 2% chance
                rec["is_anomaly"] = 1
                rec["wl_clean"] = float("nan")
                rec["wl_raw"] = 0.0
                rec["wl_raw_norm"] = 0.0
                spike_count += 1
    print(f"  Injected {spike_count} random spikes")

    print(f"\n[5/7] Computing dataset statistics ...")
    n_anom = sum(1 for r in records if r["is_anomaly"] == 1)
    print(f"  Total anomalies  : {n_anom} ({100*n_anom/len(records):.1f}%)")

    df_out = pd.DataFrame(records)

    print(f"\n[6/7] Saving training dataset ...")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(out_path, index=False)

    print(f"\n  Saved -> '{out_path}'")
    print(f"  Total rows    : {len(df_out):,}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", "-o", default=DEFAULT_OUT)
    args = parser.parse_args()
    build_dataset(args.out)
