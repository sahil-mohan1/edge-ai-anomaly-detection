import os

path = r'c:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\scripts\filters\task5_filter_testing.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update paths
content = content.replace('"combined_data.csv"', '"data-july1-14_outage.csv"')
content = content.replace('"filtered_data.csv"', '"data-july1-14_processed.csv"')

# 2. Update hard rejection logic
old_reject = '''    # Hard rejection rules
    mask_ec1      = df['errorcode'] == 1
    mask_ec3      = df['errorcode'] == 3
    mask_ec5_zero = (df['errorcode'] == 5) & (df['Water Level'] == 0)

    df['rejected'] = mask_ec1 | mask_ec3 | mask_ec5_zero'''
new_reject = '''    # Hard rejection rules
    mask_ec1      = df['errorcode'] == 1

    df['rejected'] = mask_ec1'''
content = content.replace(old_reject, new_reject)

# 3. Update plot_filter_comparison
old_plot_filter = '''def plot_filter_comparison(df_raw, time_truth, wl_truth,
                           filter_series, filter_name, filter_color,
                           metrics, save_path):
    """Two-panel plot: signal comparison (top) + residual bar chart (bottom)."""
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), dpi=150,
                             gridspec_kw={'height_ratios': [3, 1]})
    ax = axes[0]

    ax.plot(df_raw['Time'], df_raw['WL_raw'],
            color='#555555', alpha=0.30, linewidth=0.5,
            label='Raw data (combined_data.csv)', zorder=1)
    ax.plot(df_raw['Time'], df_raw['Water Level'],
            color='#e67e22', alpha=0.50, linewidth=0.8,
            label='After hard rejection (NaN gaps)', zorder=2)
    ax.plot(time_truth, wl_truth,
            color='#2ecc71', alpha=0.75, linewidth=1.3,
            label='Ground truth (filtered_data.csv)', zorder=3)
    ax.plot(df_raw['Time'], filter_series,
            color=filter_color, alpha=0.95, linewidth=1.7,
            label=f'{filter_name} output', zorder=4)

    ax.set_title(
        f'Task 5 -- {filter_name}\\n'
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

    # Residual panel
    ax2 = axes[1]
    df_f = pd.DataFrame({'Time': df_raw['Time'], 'filter': filter_series.values})
    df_t = pd.DataFrame({'Time': time_truth,      'truth':  wl_truth.values})
    res  = pd.merge(df_f, df_t, on='Time', how='inner').dropna()
    if not res.empty:
        residual = res['filter'] - res['truth']
        ax2.bar(res['Time'], residual, color=filter_color, alpha=0.5, width=0.008)
        ax2.axhline(0, color='black', linewidth=0.9, linestyle='--')
        ax2.fill_between(res['Time'], residual, 0, alpha=0.15, color=filter_color)
    ax2.set_ylabel('Residual (m)', fontsize=10)
    ax2.set_ylim(-2.0, 2.0)
    ax2.set_xlabel('Date', fontsize=11)
    ax2.set_title('Residual  =  Filter Output minus Ground Truth', fontsize=9)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    ax2.xaxis.set_major_locator(mdates.AutoDateLocator())

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"    Saved: {os.path.basename(save_path)}")
    plt.close()'''
new_plot_filter = '''def plot_filter_comparison(df_raw, time_truth, wl_truth,
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
        f'Task 5 -- {filter_name}\\n'
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
    plt.close()'''
content = content.replace(old_plot_filter, new_plot_filter)

# 4. Update plot_summary
old_summary = '''    ax.plot(df_raw['Time'], df_raw['WL_raw'],
            color='#555555', alpha=0.20, linewidth=0.5,
            label='Raw (combined_data)', zorder=1)
    ax.plot(time_truth, wl_truth,
            color='#2ecc71', alpha=0.75, linewidth=1.6,
            label='Ground truth (filtered_data)', zorder=2, linestyle='--')

    for name, series in filter_outputs.items():
        rmse = all_metrics[name]['RMSE']
        ax.plot(df_raw['Time'], series,
                color=filter_colors[name], alpha=0.85, linewidth=1.1,
                label=f'{name}  (RMSE={rmse:.4f}m)', zorder=3)

    ax.set_title('Task 5 -- All Filters Compared  |  Input: combined_data.csv  ->  NaN Rejection  ->  Filter',
                 fontsize=13, fontweight='bold', pad=14)'''
new_summary = '''    ax.plot(df_raw['Time'], df_raw['WL_raw'],
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
                 fontsize=13, fontweight='bold', pad=14)'''
content = content.replace(old_summary, new_summary)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated task5_filter_testing.py successfully.')
