import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

def generate_plots():
    # Define paths
    from pathlib import Path
    script_dir = Path(__file__).resolve().parent
    csv_path = script_dir.parent.parent / "data" / "processed" / "combined_data.csv"
    plots_dir = script_dir.parent.parent / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    output_img_path = plots_dir / "water_level_anomalies.png"

    if not csv_path.exists():
        print(f"Error: {csv_path} not found.")
        return

    # Load dataset
    print("Loading data...")
    df = pd.read_csv(csv_path)
    
    # Parse dates and numeric columns
    df['Time_parsed'] = pd.to_datetime(df['Time'], format='%d-%m-%Y %H:%M')
    df['Water Level'] = pd.to_numeric(df['Water Level'], errors='coerce')
    df['errorcode'] = df['errorcode'].astype(str)

    # Sort by time
    df = df.sort_values(by='Time_parsed')

    # Split into normal and abnormal for plotting
    normal_df = df[df['errorcode'] == '0']
    abnormal_df = df[df['errorcode'] != '0']

    print(f"Total rows: {len(df)}")
    print(f"Normal readings: {len(normal_df)}")
    print(f"Abnormal readings: {len(abnormal_df)}")

    # Set up styling for a clean, modern aesthetic
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(14, 7), dpi=300)

    # 1. Plot normal water level line
    ax.plot(df['Time_parsed'], df['Water Level'], color='#1f77b4', alpha=0.5, label='Water Level Trend', linewidth=1.2)
    
    # 2. Scatter plot for normal readings
    ax.scatter(normal_df['Time_parsed'], normal_df['Water Level'], color='#2ca02c', s=8, alpha=0.6, label='Normal (ErrorCode 0)')
    
    # 3. Scatter plot for abnormal readings (different colors for different error codes if possible)
    error_colors = {
        '1': '#d62728',  # 0 abort (red)
        '2': '#ff7f0e',  # sensor timeout (orange)
        '3': '#9467bd',  # spike detected (purple)
        '4': '#bcbd22',  # exceed limit (olive)
        '5': '#e377c2'   # sensor unstable (pink)
    }
    error_labels = {
        '1': 'ErrorCode 1 (0 abort)',
        '2': 'ErrorCode 2 (sensor timeout)',
        '3': 'ErrorCode 3 (spike detected)',
        '4': 'ErrorCode 4 (exceed limit)',
        '5': 'ErrorCode 5 (sensor unstable)'
    }

    for err_code in ['1', '2', '3', '4', '5']:
        err_sub = abnormal_df[abnormal_df['errorcode'] == err_code]
        if not err_sub.empty:
            color = error_colors.get(err_code, '#7f7f7f')
            label = error_labels.get(err_code, f'Error Code {err_code}')
            ax.scatter(err_sub['Time_parsed'], err_sub['Water Level'], color=color, s=25, marker='x', label=label, zorder=5)

    # Styling labels and title
    ax.set_title('HLK-LD2413 Sensor: Water Level and Anomalies Time Series', fontsize=16, fontweight='bold', pad=15)
    ax.set_xlabel('Timestamp', fontsize=12, labelpad=10)
    ax.set_ylabel('Water Level (meters)', fontsize=12, labelpad=10)
    
    # Format X-axis timestamps beautifully
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b %H:%M'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.tick_params(axis='both', labelsize=6)
    fig.autofmt_xdate() # Rotation

    # Set Y limit with some padding
    ax.set_ylim(-0.1, 5.0)

    # Add descriptive text box
    info_text = (
        f"Data Summary:\n"
        f"• Total readings: {len(df)}\n"
        f"• Normal (Code 0): {len(normal_df)} ({len(normal_df)/len(df)*100:.1f}%)\n"
        f"• Anomalies (Code != 0): {len(abnormal_df)} ({len(abnormal_df)/len(df)*100:.1f}%)\n"
        f"• Peak anomaly limit: 4.50 m"
    )
    props = dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.9, edgecolor='#cccccc')
    ax.text(0.02, 0.02, info_text, transform=ax.transAxes, fontsize=6, verticalalignment='bottom', bbox=props)

    # Legend
    ax.legend(
        loc='lower right', 
        frameon=True, 
        facecolor='white', 
        edgecolor='#cccccc', 
        fontsize=6,
        labelspacing=0.3,
        handlelength=1.0,
        borderpad=0.4
    )

    # Tight layout, save, and show window
    plt.tight_layout()
    plt.savefig(output_img_path, dpi=300)
    print(f"Plot saved successfully to {output_img_path}")
    print("Opening Matplotlib GUI window...")
    plt.show()
    plt.close()

if __name__ == '__main__':
    generate_plots()
