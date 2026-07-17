import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

def generate_filtered_plots():
    # Define paths
    from pathlib import Path
    script_dir = Path(__file__).resolve().parent
    csv_path = script_dir.parent / "data" / "processed" / "combined_data.csv"
    plots_dir = script_dir.parent / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    output_img_workspace = plots_dir / "water_level_filtered.png"
    artifact_dir = r"C:\Users\sahil\.gemini\antigravity-ide\brain\4670d6be-5fde-4c3e-88b8-36fc4515c6c2"
    output_img_artifact = os.path.join(artifact_dir, "water_level_filtered.png")

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

    total_rows = len(df)
    
    # Counts before filtering
    cnt_1 = len(df[df['errorcode'] == '1'])
    cnt_3 = len(df[df['errorcode'] == '3'])
    cnt_5_total = len(df[df['errorcode'] == '5'])
    cnt_5_zero = len(df[(df['errorcode'] == '5') & (df['Water Level'] == 0)])
    cnt_5_drift = cnt_5_total - cnt_5_zero

    # Apply filtering
    print("Applying filters...")
    df_filtered = df[
        (df['errorcode'] != '1') &
        (df['errorcode'] != '3') &
        ~((df['errorcode'] == '5') & (df['Water Level'] == 0))
    ]
    
    filtered_rows = len(df_filtered)
    removed_rows = total_rows - filtered_rows

    # Save the filtered dataset to CSV
    filtered_csv_path = script_dir.parent / "data" / "processed" / "filtered_data.csv"
    df_to_save = df_filtered.drop(columns=['Time_parsed'])
    df_to_save.to_csv(filtered_csv_path, index=False)

    print("\n--- Filtering Summary ---")
    print(f"Original dataset: {total_rows} rows")
    print(f"Removed ErrorCode 1 (0 abort): {cnt_1} rows")
    print(f"Removed ErrorCode 3 (spike detected): {cnt_3} rows")
    print(f"Removed ErrorCode 5 with Water Level 0: {cnt_5_zero} rows")
    print(f"Retained ErrorCode 5 drifting (Water Level > 0): {cnt_5_drift} rows")
    print(f"Total rows removed: {removed_rows} ({removed_rows/total_rows*100:.1f}%)")
    print(f"Filtered dataset size: {filtered_rows} rows")
    print(f"Filtered dataset saved to: {filtered_csv_path}")

    # Set up styling for a clean, modern aesthetic
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(14, 7), dpi=300)

    # 1. Plot filtered water level trend line
    ax.plot(df_filtered['Time_parsed'], df_filtered['Water Level'], color='#1f77b4', alpha=0.4, label='Water Level Trend Line', linewidth=1.0)
    
    # 2. Scatter plot for normal readings (ErrorCode 0)
    normal_df = df_filtered[df_filtered['errorcode'] == '0']
    ax.scatter(normal_df['Time_parsed'], normal_df['Water Level'], color='#2ca02c', s=8, alpha=0.5, label='Normal (ErrorCode 0)')
    
    # 3. Scatter plot for remaining unstable readings (ErrorCode 5 with drifting values)
    drift_df = df_filtered[df_filtered['errorcode'] == '5']
    if not drift_df.empty:
        ax.scatter(drift_df['Time_parsed'], drift_df['Water Level'], color='#ec4899', s=18, marker='x', label='ErrorCode 5 (sensor unstable - drifting)', zorder=5)

    # Styling labels and title
    ax.set_title('HLK-LD2413 Sensor: Filtered Water Level Time Series (Anomalous Flatlines Removed)', fontsize=15, fontweight='bold', pad=15)
    ax.set_xlabel('Timestamp', fontsize=12, labelpad=10)
    ax.set_ylabel('Water Level (meters)', fontsize=12, labelpad=10)
    
    # Format X-axis timestamps beautifully
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b %H:%M'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate() # Rotation

    # Set Y limit with some padding
    # Let's adjust limits to show the actual range of real values (which range between 0.3m and 4.2m)
    ax.set_ylim(-0.1, 4.5)

    # Add descriptive text box
    info_text = (
        f"Filtered Summary:\n"
        f"• Original count: {total_rows}\n"
        f"• Current count: {filtered_rows}\n"
        f"• Removed anomalies: {removed_rows}\n"
        f"  - Error 1 (0 abort): {cnt_1}\n"
        f"  - Error 3 (spike): {cnt_3}\n"
        f"  - Error 5 (unstable @ 0m): {cnt_5_zero}\n"
        f"• Retained drifting (Error 5): {cnt_5_drift}"
    )
    props = dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.9, edgecolor='#cccccc')
    ax.text(0.02, 0.05, info_text, transform=ax.transAxes, fontsize=3, verticalalignment='bottom', bbox=props)

    # Legend
    ax.legend(
        loc='upper right', 
        frameon=True, 
        facecolor='white', 
        edgecolor='#cccccc', 
        fontsize=3,
        labelspacing=0.3,
        handlelength=1.0,
        borderpad=0.4
    )

    # Tight layout, save
    plt.tight_layout()
    
    # Save to workspace
    plt.savefig(output_img_workspace, dpi=300)
    print(f"Plot saved to workspace: {output_img_workspace}")

    # Save to artifacts
    if not os.path.exists(artifact_dir):
        os.makedirs(artifact_dir, exist_ok=True)
    plt.savefig(output_img_artifact, dpi=300)
    print(f"Plot saved to conversation artifacts: {output_img_artifact}")
    
    # Display window
    print("Opening Matplotlib GUI window...")
    plt.show()

    # Close plots
    plt.close()

if __name__ == '__main__':
    generate_filtered_plots()
