import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

OUTPUT_DIR = r"c:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\plots\task5"
CSV_RAW = r'c:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\data\processed\data-july1-14_outage.csv'
CSV_TRUTH = r'c:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\data\processed\data-july1-14_processed.csv'

df = pd.read_csv(CSV_RAW)
df['Time'] = pd.to_datetime(df['Time'], format='%d-%m-%Y %H:%M')
df['Water Level'] = pd.to_numeric(df['Water Level'], errors='coerce')
df['errorcode'] = pd.to_numeric(df['errorcode'], errors='coerce').astype(int)
df = df.sort_values('Time').reset_index(drop=True)

df['is_spike'] = df['errorcode'] == 5
df['rejected'] = df['errorcode'] == 1
df['WL_raw'] = df['Water Level'].copy()
df.loc[df['rejected'], 'Water Level'] = np.nan

start_grid = df['Time'].min().round('15min')
end_grid = df['Time'].max().round('15min')
grid_index = pd.date_range(start=start_grid, end=end_grid, freq='15min')
grid_df = pd.DataFrame({'GridTime': grid_index})

df_sorted = df.sort_values('Time')
df = pd.merge_asof(grid_df, df_sorted, left_on='GridTime', right_on='Time', direction='nearest', tolerance=pd.Timedelta(minutes=7))
df['Time'] = df['Time'].fillna(df['GridTime'])

gt = pd.read_csv(CSV_TRUTH)
gt['Time'] = pd.to_datetime(gt['Time'], format='%d-%m-%Y %H:%M')
gt['Water Level'] = pd.to_numeric(gt['Water Level'], errors='coerce')

def metrics(pred_series):
    df_p = pd.DataFrame({'Time': df['Time'], 'pred': pred_series.values, 'is_spike': df['is_spike']})
    merged = pd.merge(df_p, gt[['Time', 'Water Level']].rename(columns={'Water Level': 'truth'}), on='Time', how='inner').dropna(subset=['pred', 'truth'])
    merged = merged[merged['is_spike'] == True]
    if merged.empty: return dict(RMSE=np.nan, MAE=np.nan, MaxErr=np.nan, N=0)
    err = merged['pred'] - merged['truth']
    return dict(RMSE=float(np.sqrt((err**2).mean())), MAE=float(err.abs().mean()), MaxErr=float(err.abs().max()), N=len(merged))

wl_base = df['Water Level'].interpolate(method='linear', limit_direction='both')
wl_ma = wl_base.rolling(window=5, center=True, min_periods=1).mean()
wl_med = wl_base.rolling(window=5, center=True, min_periods=1).median()
wl_ema = wl_base.ewm(span=5, adjust=False).mean()

k_mad = 1.4826
wl_h = wl_base.copy()
outlier_mask = pd.Series(False, index=wl_h.index)
for i in range(len(wl_h)):
    lo = max(0, i - 7)
    hi = min(len(wl_h), i + 7 + 1)
    win = wl_h.iloc[lo:hi]
    med = win.median()
    mad = (win - med).abs().median()
    if abs(wl_h.iloc[i] - med) > 3.0 * k_mad * mad:
        outlier_mask.iloc[i] = True
wl_h[outlier_mask] = np.nan
wl_hamp = wl_h.interpolate(method='linear', limit_direction='both')

arr = wl_base.values.copy()
for i in range(1, len(arr)):
    if np.isnan(arr[i]) or np.isnan(arr[i-1]): continue
    delta = arr[i] - arr[i-1]
    if abs(delta) > 0.5: arr[i] = arr[i-1] + np.sign(delta) * 0.5
wl_roc = pd.Series(arr, index=df.index)

filter_outputs = {
    'Moving Average': (wl_ma, '#e74c3c'),
    'Median Filter':  (wl_med, '#9b59b6'),
    'EMA':            (wl_ema, '#f39c12'),
    'Hampel Filter':  (wl_hamp, '#e84393'),
    'RoC Limiter':    (wl_roc, '#2980b9'),
}

time_truth = gt['Time']
wl_truth = gt['Water Level']

# 1. Summary plot
plt.style.use('seaborn-v0_8-whitegrid')
fig, ax = plt.subplots(figsize=(18, 8), dpi=150)
ax.plot(df['Time'], df['WL_raw'], color='#555555', alpha=0.20, linewidth=0.5, label='Raw Sensor Data', zorder=1)
ax.plot(time_truth, wl_truth, color='#2ecc71', alpha=0.75, linewidth=1.6, label='Ground Truth Data', zorder=2, linestyle='--')
for name, (series, color) in filter_outputs.items():
    m = metrics(series)
    ax.plot(df['Time'], series, color=color, alpha=0.85, linewidth=1.1, label=f'{name}  (RMSE={m["RMSE"]:.4f}m)', zorder=3)
ax.set_title('Task 5 -- All Filters Compared', fontsize=13, fontweight='bold', pad=14)
ax.set_ylabel('Water Level (m)', fontsize=12)
ax.set_xlabel('Date', fontsize=12)
ax.set_ylim(-0.3, 5.2)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
ax.legend(loc='upper right', fontsize=9, framealpha=0.95, ncol=2)
fig.autofmt_xdate()
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "task5_00_summary_all_filters.png"), dpi=150, bbox_inches='tight')
plt.close()

# 2. Hampel plot
fig, axes = plt.subplots(2, 1, figsize=(16, 10), dpi=150, gridspec_kw={'height_ratios': [3, 1]})
ax = axes[0]
ax.plot(df['Time'], df['WL_raw'], color='#555555', alpha=0.30, linewidth=0.5, label='Raw Sensor Data', zorder=1)
ax.plot(time_truth, wl_truth, color='#2ecc71', alpha=0.75, linewidth=1.3, label='Ground Truth Data', zorder=3)
m = metrics(wl_hamp)
ax.plot(df['Time'], wl_hamp, color='#e84393', alpha=0.95, linewidth=1.7, label=f'Hampel Filter output', zorder=4)
ax.set_title(f'Task 5 -- Hampel Filter\nRMSE={m["RMSE"]:.4f} m  |  MAE={m["MAE"]:.4f} m  |  Max Error={m["MaxErr"]:.4f} m  |  N={m["N"]} matched points', fontsize=12, fontweight='bold', pad=12)
ax.set_ylabel('Water Level (m)', fontsize=11)
ax.set_ylim(-0.3, 5.2)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
ax.legend(loc='upper right', fontsize=8, framealpha=0.92)
fig.autofmt_xdate()
ax2 = axes[1]
df_f = pd.DataFrame({'Time': df['Time'], 'filter': wl_hamp.values})
df_t = pd.DataFrame({'Time': time_truth, 'truth': wl_truth.values})
res = pd.merge(df_f, df_t, on='Time', how='inner').dropna()
if not res.empty:
    residual = res['filter'] - res['truth']
    ax2.bar(res['Time'], residual, color='#e84393', alpha=0.5, width=0.008)
    ax2.axhline(0, color='black', linewidth=0.9, linestyle='--')
    ax2.fill_between(res['Time'], residual, 0, alpha=0.15, color='#e84393')
ax2.set_ylabel('Residual (m)', fontsize=10)
ax2.set_ylim(-2.0, 2.0)
ax2.set_xlabel('Date', fontsize=11)
ax2.set_title('Residual  =  Filter Output minus Ground Truth', fontsize=9)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "task5_04_hampel.png"), dpi=150, bbox_inches='tight')
plt.close()
