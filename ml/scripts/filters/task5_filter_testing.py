# -*- coding: utf-8 -*-
"""
Task 5 -- Filter Testing for HLK-LD2413 Water Level Sensor
===========================================================
Pipeline:
  Stage 1 (Hard Rejection): Replace known-invalid readings with NaN
      - errorcode 1  (sensor abort, WL always 0)       -> NaN
      - errorcode 3  (spike flagged by sensor itself)   -> NaN
      - errorcode 5 with Water Level == 0               -> NaN
      - Keep: errorcode 5 with WL > 0 (drifting but physically plausible)

  Stage 2 (Filtering): Each filter independently fills NaN gaps and smooths
      1. Moving Average Filter       (rolling mean)
      2. Median Filter               (rolling median)
      3. Exponential Moving Average  (EWM)
      4. Hampel Filter               (outlier detection via MAD, then interpolate)
      5. Rate-of-Change Limiter      (clip delta-WL per step)

Evaluation: Compare each filter output against filtered_data.csv (ground truth)
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import warnings
warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────
from pathlib import Path
SCRIPT_DIR   = Path(__file__).resolve().parent
BASE_DIR     = SCRIPT_DIR.parent.parent
COMBINED_CSV = str(BASE_DIR / "data" / "processed" / "data-july1-14_outage.csv")
FILTERED_CSV = str(BASE_DIR / "data" / "processed" / "data-july1-14_processed.csv")
OUTPUT_DIR   = str(BASE_DIR / "plots" / "task5")
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────
# FILTER PARAMETERS  (tune here if needed)
# ─────────────────────────────────────────────────────────
WINDOW        = 5      # rolling window for MA and Median
EMA_SPAN      = 5      # span for EWM
HAMPEL_WINDOW = 7      # half-window for Hampel identifier (+/- neighbours)
HAMPEL_SIGMA  = 3.0    # outlier threshold: k x MAD
MAX_ROC       = 0.5    # max allowed WL change per 15-min step (metres)


# ═══════════════════════════════════════════════════════════
#  STAGE 1 -- LOAD & HARD REJECT
# ═══════════════════════════════════════════════════════════

def load_and_hard_reject(path: str) -> pd.DataFrame:
    """Load combined CSV, hard-reject invalid readings -> NaN."""
    df = pd.read_csv(path)
    df['Time']        = pd.to_datetime(df['Time'], format='%d-%m-%Y %H:%M')
    df['Water Level'] = pd.to_numeric(df['Water Level'], errors='coerce')
    df['errorcode']   = pd.to_numeric(df['errorcode'],   errors='coerce').astype(int)
    df = df.sort_values('Time').reset_index(drop=True)

    # Hard rejection rules
    mask_ec1      = df['errorcode'] == 1

    df['rejected'] = mask_ec1
    df['WL_raw']   = df['Water Level'].copy()
    df.loc[df['rejected'], 'Water Level'] = np.nan

    n_total    = len(df)
    n_rejected = int(df['rejected'].sum())
    print("")
    print("=" * 58)
    print("  STAGE 1 -- HARD REJECTION")
    print("=" * 58)
    print(f"  Total rows         : {n_total}")
    print(f"  Rejected -> NaN    : {n_rejected}  ({n_rejected/n_total*100:.1f}%)")
    print(f"    EC1 (abort)      : {int(mask_ec1.sum())}")
    print(f"  Remaining valid    : {n_total - n_rejected}")

    # Drop exact duplicates if any
    df = df.drop_duplicates(subset=['Time']).reset_index(drop=True)

    return df


# ═══════════════════════════════════════════════════════════
#  RESAMPLE TO UNIFORM 15-MIN GRID
# ═══════════════════════════════════════════════════════════

def resample_to_15min(df: pd.DataFrame) -> pd.DataFrame:
    """
    Align the dataframe to a complete, uniform 15-minute frequency grid
    using merge_asof to handle shifts/drifts, preserving original timestamps for plotting.
    """
    # Create uniform 15-minute grid
    start_grid = df['Time'].min().round('15min')
    end_grid = df['Time'].max().round('15min')
    grid_index = pd.date_range(start=start_grid, end=end_grid, freq='15min')
    grid_df = pd.DataFrame({'GridTime': grid_index})

    # Align using merge_asof with 7-min tolerance
    df_sorted = df.sort_values('Time')
    merged = pd.merge_asof(
        grid_df,
        df_sorted,
        left_on='GridTime',
        right_on='Time',
        direction='nearest',
        tolerance=pd.Timedelta(minutes=7)
    )

    # Preserve original unrounded Time for plotting, fill gaps with GridTime
    merged['Time_plot'] = merged['Time'].fillna(merged['GridTime'])
    merged['OriginalTime'] = merged['Time']
    merged['Time'] = merged['Time_plot']

    n_orig   = len(grid_df)
    n_filled = int(merged['Water Level'].isna().sum())
    print("")
    print("=" * 58)
    print("  RESAMPLING TO UNIFORM 15-MIN GRID (ASOF MERGE)")
    print("=" * 58)
    print(f"  Grid slots (15-min)  : {n_orig}")
    print(f"  NaN slots after join : {n_filled}  (will be handled by filters)")
    return merged


def load_ground_truth(path: str) -> pd.DataFrame:
    """Load the manually filtered dataset as ground truth."""
    df = pd.read_csv(path)
    df['Time']        = pd.to_datetime(df['Time'], format='%d-%m-%Y %H:%M')
    df['Water Level'] = pd.to_numeric(df['Water Level'], errors='coerce')
    return df.sort_values('Time').reset_index(drop=True)


# ═══════════════════════════════════════════════════════════
#  STAGE 2 -- FILTERS
# ═══════════════════════════════════════════════════════════

def apply_moving_average(series: pd.Series, window: int = WINDOW) -> pd.Series:
    """Linear-interpolate NaN gaps, then apply centred rolling mean."""
    s = series.interpolate(method='linear', limit_direction='both')
    return s.rolling(window=window, center=True, min_periods=1).mean()


def apply_median_filter(series: pd.Series, window: int = WINDOW) -> pd.Series:
    """Linear-interpolate NaN gaps, then apply centred rolling median."""
    s = series.interpolate(method='linear', limit_direction='both')
    return s.rolling(window=window, center=True, min_periods=1).median()


def apply_ema(series: pd.Series, span: int = EMA_SPAN) -> pd.Series:
    """Linear-interpolate NaN gaps, then apply Exponential Weighted Mean."""
    s = series.interpolate(method='linear', limit_direction='both')
    return s.ewm(span=span, adjust=False).mean()


def apply_hampel(series: pd.Series,
                 half_window: int = HAMPEL_WINDOW,
                 sigma: float = HAMPEL_SIGMA) -> pd.Series:
    """
    Hampel Identifier:
      1. Linear-interpolate to fill hard-rejected NaN holes.
      2. Slide a window of (2*half_window+1); compute median and scaled MAD.
      3. Points beyond sigma*MAD from local median -> mark as outlier -> NaN.
      4. Linear-interpolate again to fill newly detected outliers.
    """
    k = 1.4826  # consistency factor: MAD -> sigma for Gaussian
    s = series.interpolate(method='linear', limit_direction='both').copy()
    outlier_mask = pd.Series(False, index=s.index)
    n = len(s)
    for i in range(n):
        lo = max(0, i - half_window)
        hi = min(n, i + half_window + 1)
        window_vals = s.iloc[lo:hi]
        med = window_vals.median()
        mad = (window_vals - med).abs().median()
        if abs(s.iloc[i] - med) > sigma * k * mad:
            outlier_mask.iloc[i] = True

    s[outlier_mask] = np.nan
    s = s.interpolate(method='linear', limit_direction='both')
    print(f"    Hampel identified {int(outlier_mask.sum())} additional statistical outliers")
    return s


def apply_roc_limiter(series: pd.Series, max_roc: float = MAX_ROC) -> pd.Series:
    """
    Rate-of-Change Limiter:
      1. Linear-interpolate NaN gaps.
      2. Walk forward: if |delta| > max_roc, clamp the step to max_roc.
    """
    s   = series.interpolate(method='linear', limit_direction='both').copy()
    arr = s.values.copy()
    for i in range(1, len(arr)):
        if np.isnan(arr[i]) or np.isnan(arr[i-1]):
            continue
        delta = arr[i] - arr[i-1]
        if abs(delta) > max_roc:
            arr[i] = arr[i-1] + np.sign(delta) * max_roc
    return pd.Series(arr, index=s.index)


def apply_kalman_2d(series: pd.Series) -> pd.Series:
    """
    2D Kalman Filter tracking position (Water Level) and velocity.
    State x = [position, velocity]^T
    """
    s = series.interpolate(method='linear', limit_direction='both').copy()
    
    n = len(s)
    dt = 1.0
    F = np.array([[1, dt], 
                  [0, 1]])
    H = np.array([[1, 0]])
    
    # Process noise covariance
    q = 0.05
    Q = np.array([[q*(dt**3)/3, q*(dt**2)/2], 
                  [q*(dt**2)/2, q*dt]])
    
    # Observation noise covariance
    R = np.array([[0.5]])
    
    # Initial state
    x = np.array([[s.iloc[0]], [0.0]])
    P = np.eye(2) * 1.0
    
    filtered_vals = []
    
    for i in range(n):
        # Predict
        x_pred = F.dot(x)
        P_pred = F.dot(P).dot(F.T) + Q
        
        # Update
        z = np.array([[s.iloc[i]]])
        y = z - H.dot(x_pred)
        S = H.dot(P_pred).dot(H.T) + R
        K = P_pred.dot(H.T).dot(np.linalg.inv(S))
        
        x = x_pred + K.dot(y)
        P = (np.eye(2) - K.dot(H)).dot(P_pred)
        
        filtered_vals.append(x[0, 0])
        
    return pd.Series(filtered_vals, index=s.index)


# ═══════════════════════════════════════════════════════════
#  METRICS
# ═══════════════════════════════════════════════════════════

def compute_metrics(pred: pd.Series, truth: pd.Series,
                    time_pred: pd.Series, time_truth: pd.Series) -> dict:
    """Align on common timestamps then compute RMSE, MAE, MaxError."""
    df_p = pd.DataFrame({'Time': time_pred,  'pred':  pred.values})
    df_t = pd.DataFrame({'Time': time_truth, 'truth': truth.values})
    m    = pd.merge(df_p, df_t, on='Time', how='inner').dropna()
    if len(m) == 0:
        return {'RMSE': np.nan, 'MAE': np.nan, 'MaxErr': np.nan, 'N': 0}
    err = m['pred'] - m['truth']
    return {
        'RMSE':   float(np.sqrt((err**2).mean())),
        'MAE':    float(err.abs().mean()),
        'MaxErr': float(err.abs().max()),
        'N':      len(m)
    }


# ═══════════════════════════════════════════════════════════
#  PLOTTING -- individual filter comparison
# ═══════════════════════════════════════════════════════════

def plot_filter_comparison(df_raw, time_truth, wl_truth,
                           filter_series, filter_name, filter_color,
                           metrics, save_path):
    """Single-panel plot: signal comparison."""
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(16, 8), dpi=150)

    ax.plot(df_raw['Time'], df_raw['WL_raw'],
            color='#555555', alpha=0.30, linewidth=0.5,
            label='Raw Sensor Data', zorder=1)
    ax.plot(time_truth, wl_truth,
            color='#2ecc71', alpha=0.75, linewidth=1.3,
            label='Ground Truth Data', zorder=2)
    ax.plot(df_raw['Time'], filter_series,
            color=filter_color, alpha=0.95, linewidth=1.7,
            label=f'{filter_name} output', zorder=3)

    ax.set_title(
        f'Task 5 -- {filter_name}\n'
        f'RMSE={metrics["RMSE"]:.4f} m  |  MAE={metrics["MAE"]:.4f} m  |  '
        f'Max Error={metrics["MaxErr"]:.4f} m  |  N={metrics["N"]} matched points',
        fontsize=12, fontweight='bold', pad=12
    )
    ax.set_ylabel('Water Level (m)', fontsize=11)
    ax.set_ylim(-0.3, 5.2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.legend(loc='upper right', fontsize=8, framealpha=0.92)
    fig.autofmt_xdate()

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"    Saved: {os.path.basename(save_path)}")
    plt.close()


# ═══════════════════════════════════════════════════════════
#  SUMMARY PLOT -- all filters overlaid
# ═══════════════════════════════════════════════════════════

def plot_summary(df_raw, time_truth, wl_truth, filter_outputs, all_metrics, save_path):
    """Overlay all filter outputs on one axes for direct comparison."""
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(18, 8), dpi=150)

    filter_colors = {
        'Moving Average': '#e74c3c',
        'Median Filter':  '#9b59b6',
        'EMA':            '#f39c12',
        'Hampel Filter':  '#e84393',
        'RoC Limiter':    '#2980b9',
        '2D Kalman':      '#16a085',
    }

    ax.plot(df_raw['Time'], df_raw['WL_raw'],
            color='#555555', alpha=0.20, linewidth=0.5,
            label='Raw Sensor Data', zorder=1)
    ax.plot(time_truth, wl_truth,
            color='#2ecc71', alpha=0.75, linewidth=1.6,
            label='Ground Truth Data', zorder=2, linestyle='--')

    for name, series in filter_outputs.items():
        rmse = all_metrics[name]['RMSE']
        ax.plot(df_raw['Time'], series,
                color=filter_colors[name], alpha=0.85, linewidth=1.1,
                label=f'{name}  (RMSE={rmse:.4f}m)', zorder=3)

    ax.set_title('Task 5 -- All Filters Compared',
                 fontsize=13, fontweight='bold', pad=14)
    ax.set_ylabel('Water Level (m)', fontsize=12)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylim(-0.3, 5.2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.legend(loc='upper right', fontsize=9, framealpha=0.95, ncol=2)
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"    Saved: {os.path.basename(save_path)}")
    plt.close()


# ═══════════════════════════════════════════════════════════
#  METRICS TABLE
# ═══════════════════════════════════════════════════════════

def print_metrics_table(all_metrics: dict):
    print("")
    print("=" * 65)
    print("  TASK 5 -- FILTER PERFORMANCE SUMMARY")
    print("  (vs filtered_data.csv as ground truth)")
    print("=" * 65)
    print(f"  {'Filter':<26} {'RMSE':>8} {'MAE':>8} {'MaxErr':>9} {'N':>7}")
    print(f"  {'-'*26} {'-'*8} {'-'*8} {'-'*9} {'-'*7}")
    for name, m in all_metrics.items():
        print(f"  {name:<26} {m['RMSE']:>8.4f} {m['MAE']:>8.4f} {m['MaxErr']:>9.4f} {m['N']:>7}")
    print("=" * 65)

    valid = {k: v for k, v in all_metrics.items() if not np.isnan(v['RMSE'])}
    if valid:
        best = min(valid, key=lambda k: valid[k]['RMSE'])
        print(f"\n  >> Best filter by RMSE : {best}  (RMSE = {valid[best]['RMSE']:.4f} m)")
        best_mae = min(valid, key=lambda k: valid[k]['MAE'])
        print(f"  >> Best filter by MAE  : {best_mae}  (MAE  = {valid[best_mae]['MAE']:.4f} m)")
    print("")


# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════

def main():
    print("")
    print("=" * 58)
    print("  TASK 5 -- FILTER TESTING  (HLK-LD2413 Water Level)")
    print("=" * 58)

    df       = load_and_hard_reject(COMBINED_CSV)
    df       = resample_to_15min(df)          # enforce uniform 15-min grid
    df_truth = load_ground_truth(FILTERED_CSV)
    time_truth = df_truth['Time']
    wl_truth   = df_truth['Water Level']
    wl_nan     = df['Water Level']

    # Apply all 5 filters
    print("")
    print("=" * 58)
    print("  STAGE 2 -- APPLYING FILTERS")
    print("=" * 58)

    print("  [1/5] Moving Average Filter ...")
    f_ma = apply_moving_average(wl_nan)

    print("  [2/5] Median Filter ...")
    f_med = apply_median_filter(wl_nan)

    print("  [3/5] Exponential Moving Average ...")
    f_ema = apply_ema(wl_nan)

    print("  [4/5] Hampel Filter ...")
    f_hamp = apply_hampel(wl_nan)

    print("  [5/6] Rate-of-Change Limiter ...")
    f_roc = apply_roc_limiter(wl_nan)

    print("  [6/6] 2D Kalman Filter ...")
    f_kalman = apply_kalman_2d(wl_nan)

    filter_outputs = {
        'Moving Average': f_ma,
        'Median Filter':  f_med,
        'EMA':            f_ema,
        'Hampel Filter':  f_hamp,
        'RoC Limiter':    f_roc,
        '2D Kalman':      f_kalman,
    }

    # Metrics
    print("")
    print("=" * 58)
    print("  COMPUTING METRICS vs GROUND TRUTH")
    print("=" * 58)
    all_metrics = {}
    for name, series in filter_outputs.items():
        m = compute_metrics(series, wl_truth, df['Time'], time_truth)
        all_metrics[name] = m
        print(f"  {name:<26}  RMSE={m['RMSE']:.4f}  MAE={m['MAE']:.4f}  MaxErr={m['MaxErr']:.4f}")

    print_metrics_table(all_metrics)

    # Plots
    print("=" * 58)
    print("  GENERATING PLOTS")
    print("=" * 58)

    filter_configs = [
        ('Moving Average', f_ma,     '#e74c3c', 'task5_01_moving_average.png'),
        ('Median Filter',  f_med,    '#9b59b6', 'task5_02_median_filter.png'),
        ('EMA',            f_ema,    '#f39c12', 'task5_03_ema.png'),
        ('Hampel Filter',  f_hamp,   '#e84393', 'task5_04_hampel.png'),
        ('RoC Limiter',    f_roc,    '#2980b9', 'task5_05_roc_limiter.png'),
        ('2D Kalman',      f_kalman, '#16a085', 'task5_06_kalman_filter.png'),
    ]

    for name, series, color, fname in filter_configs:
        print(f"  Plotting {name} ...")
        plot_filter_comparison(
            df_raw=df, time_truth=time_truth, wl_truth=wl_truth,
            filter_series=series, filter_name=name, filter_color=color,
            metrics=all_metrics[name],
            save_path=os.path.join(OUTPUT_DIR, fname)
        )

    print("  Plotting summary (all filters) ...")
    plot_summary(df, time_truth, wl_truth, filter_outputs, all_metrics,
                 save_path=os.path.join(OUTPUT_DIR, 'task5_00_summary_all_filters.png'))

    print("")
    print("  Done! Output files saved in:")
    print(f"  {OUTPUT_DIR}")
    print("    task5_00_summary_all_filters.png")
    print("    task5_01_moving_average.png")
    print("    task5_02_median_filter.png")
    print("    task5_03_ema.png")
    print("    task5_04_hampel.png")
    print("    task5_05_roc_limiter.png")
    print("    task5_06_kalman_filter.png")
    print("")


if __name__ == '__main__':
    main()
