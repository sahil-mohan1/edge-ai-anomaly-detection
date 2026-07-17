"""
run_pipeline.py
---------------
Entry point for the SNARIMAX + ARFR hybrid anomaly correction pipeline.

Usage
-----
  python run_pipeline.py                          # run with live plot window
  python run_pipeline.py --no-plot               # suppress the plot window
  python run_pipeline.py --input  data/my.csv    # custom input
  python run_pipeline.py --output data/out.csv   # custom output
  python run_pipeline.py --retrain               # force full retrain

Resume behaviour
----------------
  On second+ run the pipeline automatically loads the saved model and only
  processes rows AFTER the last processed timestamp, so the model is never
  trained twice on the same data.

Output CSV columns
------------------
  Time                    - original timestamp string
  errorcode               - raw sensor error code
  Water_Level_Raw         - original sensor reading
  Water_Level_Corrected   - cleaned / imputed value
  SNARIMAX_Pred           - one-step forecast from SNARIMAX
  ARFR_Pred               - one-step forecast from ARFR
  Ensemble_Pred           - weighted combination used for correction
  Residual                - |Ensemble_Pred - Water_Level_Raw|
  Is_Anomaly              - True if the raw value was replaced
  Correction_Source       - why the reading was kept or replaced

Requirements
------------
  pip install river pandas matplotlib
"""

import argparse
import os
import sys
import time
from pathlib import Path

import pandas as pd

# Allow importing the models package from the project root
sys.path.insert(0, str(Path(__file__).parent))

from models import HybridCorrector
from models import config as cfg
from models.model_store import (
    delete_model, get_last_timestamp, load_model, model_exists, save_model
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATE_FORMAT = "%d-%m-%Y %H:%M"


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_data(path: str) -> pd.DataFrame:
    """Load and validate the combined_data CSV."""
    df = pd.read_csv(path)

    required = {"Time", "errorcode", "Water Level"}
    missing  = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in input CSV: {missing}")

    df["_ts"] = pd.to_datetime(df["Time"], format=DATE_FORMAT, dayfirst=True)
    df = df.sort_values("_ts").reset_index(drop=True)

    print(f"  Loaded {len(df):,} rows from '{path}'")
    print(f"  Date range: {df['_ts'].min()} -> {df['_ts'].max()}")
    print(f"  Error code distribution:")
    for code, count in sorted(df["errorcode"].value_counts().items()):
        label = cfg.ERROR_CODE_LABELS.get(int(code), "unknown")
        pct   = count / len(df) * 100
        print(f"    EC={code} ({label:16s}): {count:5,}  ({pct:.1f}%)")

    return df


def save_results(results: list, output_path: str) -> None:
    """Save the list of CorrectionResult objects to a CSV file."""
    records = [
        {
            "Time":                  r.timestamp.strftime(DATE_FORMAT),
            "errorcode":             r.errorcode,
            "Water_Level_Raw":       round(r.original_value,  4),
            "Water_Level_Corrected": round(r.corrected_value, 4),
            "SNARIMAX_Pred":         round(r.snarimax_pred,   4),
            "ARFR_Pred":             round(r.arfr_pred,       4),
            "Ensemble_Pred":         round(r.ensemble_pred,   4),
            "Residual":              round(r.residual,        4),
            "Is_Anomaly":            r.is_anomaly,
            "Correction_Source":     r.correction_src,
        }
        for r in results
    ]
    out_df = pd.DataFrame(records)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    out_df.to_csv(output_path, index=False)
    print(f"\n  Saved corrected data -> '{output_path}'")


# ---------------------------------------------------------------------------
# Plot (opens in a new window)
# ---------------------------------------------------------------------------

def plot_results(results: list) -> None:
    """
    Opens a new matplotlib window showing:
      Panel 1 – Raw vs Corrected water level with anomaly markers
      Panel 2 – SNARIMAX, ARFR and Ensemble predictions vs Corrected
      Panel 3 – Residual over time with threshold line
    """
    try:
        import matplotlib
        matplotlib.use("TkAgg")          # force a real window backend on Windows
    except Exception:
        pass                             # fall back to whatever is available

    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    timestamps    = [r.timestamp         for r in results]
    raw_vals      = [r.original_value     for r in results]
    corr_vals     = [r.corrected_value    for r in results]
    sna_preds     = [r.snarimax_pred      for r in results]
    arfr_preds    = [r.arfr_pred          for r in results]
    ens_preds     = [r.ensemble_pred      for r in results]
    residuals     = [r.residual           for r in results]

    anom_ts       = [r.timestamp          for r in results if r.is_anomaly]
    anom_raw      = [r.original_value     for r in results if r.is_anomaly]
    anom_corr     = [r.corrected_value    for r in results if r.is_anomaly]

    # Load filtered data if available
    filtered_ts = []
    filtered_vals = []
    filtered_path = "data/processed/filtered_data.csv"
    if os.path.exists(filtered_path):
        try:
            f_df = pd.read_csv(filtered_path)
            f_df["_ts"] = pd.to_datetime(f_df["Time"], format="%d-%m-%Y %H:%M", dayfirst=True)
            f_df = f_df.sort_values("_ts")
            filtered_ts = f_df["_ts"].tolist()
            filtered_vals = f_df["Water Level"].tolist()
        except Exception as e:
            print(f"  Warning: Could not load filtered data for plotting: {e}")

    fig, axes = plt.subplots(3, 1, figsize=(16, 11), sharex=True)
    fig.suptitle(
        "SNARIMAX + ARFR  Hybrid Anomaly Correction\nWater Level Sensor Data",
        fontsize=13, fontweight="bold", y=0.98
    )

    # ---- Panel 1: Raw vs Corrected ----
    ax1 = axes[0]
    ax1.plot(timestamps, raw_vals,  color="#e05c5c", linewidth=0.7,
             label="Raw (sensor)", alpha=0.6, zorder=2)
    ax1.plot(timestamps, corr_vals, color="#3a86ff", linewidth=1.1,
             label="Corrected", alpha=0.95, zorder=4)
    if filtered_ts:
        ax1.plot(filtered_ts, filtered_vals, color="#2ca02c", linewidth=0.9,
                 linestyle="--", label="Filtered Data", alpha=0.7, zorder=3)
    if anom_ts:
        ax1.scatter(anom_ts, anom_raw,  color="#e05c5c", s=18, marker="x",
                    zorder=5, label="Anomaly (raw)", linewidths=1.2)
        ax1.scatter(anom_ts, anom_corr, color="#ff9f1c", s=14, marker="o",
                    zorder=6, label="Anomaly (corrected)", alpha=0.85)
    ax1.set_ylabel("Water Level (m)")
    ax1.set_title("Raw vs Corrected Water Level", fontsize=10, loc="left")
    ax1.legend(loc="upper right", fontsize=8, ncol=2)
    ax1.grid(True, alpha=0.25)

    # ---- Panel 2: Model Predictions ----
    ax2 = axes[1]
    ax2.plot(timestamps, corr_vals,  color="#3a86ff", linewidth=1.1,
             label="Corrected", alpha=0.9, zorder=4)
    ax2.plot(timestamps, sna_preds,  color="#06d6a0", linewidth=0.8,
             label="SNARIMAX pred", alpha=0.75, linestyle="--", zorder=3)
    ax2.plot(timestamps, arfr_preds, color="#f4a261", linewidth=0.8,
             label="ARFR pred", alpha=0.75, linestyle=":", zorder=3)
    ax2.plot(timestamps, ens_preds,  color="#8338ec", linewidth=0.9,
             label="Ensemble pred", alpha=0.8, linestyle="-.", zorder=3)
    ax2.set_ylabel("Water Level (m)")
    ax2.set_title("Model Predictions vs Corrected", fontsize=10, loc="left")
    ax2.legend(loc="upper right", fontsize=8, ncol=2)
    ax2.grid(True, alpha=0.25)

    # ---- Panel 3: Residual ----
    ax3 = axes[2]
    ax3.fill_between(timestamps, residuals,
                     color="#8338ec", alpha=0.4, label="|Ensemble - Raw|")
    ax3.axhline(cfg.RESIDUAL_THRESHOLD_M, color="#e05c5c", linestyle="--",
                linewidth=0.9,
                label=f"EC=5 threshold ({cfg.RESIDUAL_THRESHOLD_M} m)")
    ax3.set_ylabel("Residual (m)")
    ax3.set_xlabel("Time")
    ax3.set_title("Prediction Residual", fontsize=10, loc="left")
    ax3.legend(loc="upper right", fontsize=8)
    ax3.grid(True, alpha=0.25)

    # ---- X-axis formatting ----
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m %H:%M"))
    fig.autofmt_xdate(rotation=30)
    plt.tight_layout(rect=[0, 0, 1, 0.97])

    # Save PNG alongside plot window
    plot_path = "plots/correction_plot.png"
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    print(f"  Plot saved -> '{plot_path}'")

    plt.show(block=True)       # opens a new window; script waits until closed


# ---------------------------------------------------------------------------
# Main pipeline runner
# ---------------------------------------------------------------------------

def run(input_path: str, output_path: str,
        show_plot: bool = True,
        resume: bool = True,
        retrain: bool = False) -> None:

    print("\n" + "=" * 55)
    print("  SNARIMAX + ARFR  Hybrid Correction Pipeline")
    print("=" * 55)

    # ---- Load all data ----
    print("\n[1/4] Loading data ...")
    df = load_data(input_path)

    # ---- Initialise or restore corrector ----
    print("\n[2/4] Initialising models ...")
    corrector  = None
    last_ts    = None

    if resume and not retrain and model_exists():
        print("  Found saved model -- resuming from checkpoint:")
        corrector = load_model()
        last_ts   = get_last_timestamp()

    if corrector is None:
        if retrain:
            print("  --retrain flag set: training from scratch.")
            delete_model()
        else:
            print("  No saved model found -- training from scratch.")
        corrector = HybridCorrector()
        last_ts   = None

    print(f"  SNARIMAX params : {cfg.SNARIMAX_PARAMS}")
    print(f"  ARFR    params  : {cfg.ARFR_PARAMS}")
    print(f"  Ensemble weights: SNARIMAX={cfg.SNARIMAX_WEIGHT}  ARFR={cfg.ARFR_WEIGHT}")

    # ---- Filter to only NEW rows when resuming ----
    if last_ts is not None:
        new_df = df[df["_ts"] > last_ts].reset_index(drop=True)
        if new_df.empty:
            print(f"\n  No new data after last checkpoint ({last_ts}).")
            print("  Nothing to process. Exiting.")
            return
        n_skipped = len(df) - len(new_df)
        print(f"\n  Skipping {n_skipped:,} already-seen rows (last checkpoint: {last_ts})")
        df = new_df
    else:
        print(f"\n  Processing all {len(df):,} rows from scratch.")

    # ---- Stream through data ----
    print(f"\n[3/4] Processing {len(df):,} readings ...")
    results = []
    t0 = time.perf_counter()

    for _, row in df.iterrows():
        result = corrector.process(
            timestamp   = row["_ts"],
            errorcode   = int(row["errorcode"]),
            water_level = float(row["Water Level"]),
        )
        results.append(result)

        if len(results) % 1000 == 0:
            elapsed = time.perf_counter() - t0
            rate    = len(results) / elapsed
            print(f"  ... {len(results):,} / {len(df):,}  ({rate:.0f} rows/s)", end="\r")

    elapsed = time.perf_counter() - t0
    print(f"  Done -- {len(results):,} rows in {elapsed:.2f}s "
          f"({len(results)/elapsed:.0f} rows/s)          ")

    # ---- Print summary ----
    print("\n[4/4] Results")
    print(corrector.summary())

    # ---- Save model state (with last processed timestamp) ----
    print("\n  Saving trained model ...")
    save_model(corrector, last_timestamp=df["_ts"].iloc[-1])

    # ---- Save corrected CSV ----
    save_results(results, output_path)

    # ---- Show plot in new window ----
    if show_plot:
        print("\n  Opening plot window ...")
        plot_results(results)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SNARIMAX + ARFR hybrid water-level anomaly correction"
    )
    parser.add_argument(
        "--input",  "-i",
        default = cfg.INPUT_CSV,
        help    = f"Path to input CSV (default: {cfg.INPUT_CSV})"
    )
    parser.add_argument(
        "--output", "-o",
        default = cfg.OUTPUT_CSV,
        help    = f"Path to save corrected CSV (default: {cfg.OUTPUT_CSV})"
    )
    parser.add_argument(
        "--no-plot",
        action  = "store_true",
        help    = "Suppress the plot window (plot is shown by default)"
    )
    parser.add_argument(
        "--retrain",
        action  = "store_true",
        help    = "Force full retrain from scratch, ignoring any saved model"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(
        input_path  = args.input,
        output_path = args.output,
        show_plot   = not args.no_plot,
        resume      = True,
        retrain     = args.retrain,
    )
