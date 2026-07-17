import os
import re
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def parse_stm32_output(file_path):
    """
    Parses the STM32 serial output text file and extracts inference metrics,
    predictions, raw values, and performance statistics.
    """
    records = []
    current_record = {}
    
    # Regex patterns matching the STM32 serial output format
    inference_re = re.compile(r'---- Inference number (\d+) ----')
    duration_dwt_re = re.compile(r'duration DWT\s*:\s*([\d.]+)\s*ms')
    duration_sys_re = re.compile(r'duration SysTick\s*:\s*([\d.]+)\s*ms')
    cycles_re = re.compile(r'CPU cycles\s*:\s*(\d+)')
    cycles_avg_re = re.compile(r'CPU cycles \(avg\):\s*(\d+)')
    row_re = re.compile(r'Row (\d+):\s*WL_Raw:\s*([\d.-]+),\s*Pred_WL:\s*([\d.-]+),\s*Anomaly:\s*(\d+)\s*\(Prob:\s*([\d.e-]+)\)')
    
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        sys.exit(1)
        
    print(f"Reading and parsing STM32 output file: {file_path}")
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line_str = line.strip()
            
            # Start of a new inference block
            inf_match = inference_re.search(line_str)
            if inf_match:
                if current_record and 'row' in current_record:
                    records.append(current_record)
                current_record = {'inference_num': int(inf_match.group(1))}
                continue
                
            # Parse timing duration from DWT
            dur_dwt_match = duration_dwt_re.search(line_str)
            if dur_dwt_match:
                current_record['duration_dwt'] = float(dur_dwt_match.group(1))
                continue
                
            # Parse timing duration from SysTick
            dur_sys_match = duration_sys_re.search(line_str)
            if dur_sys_match:
                current_record['duration_systick'] = float(dur_sys_match.group(1))
                continue
                
            # Parse CPU cycles
            cyc_match = cycles_re.search(line_str)
            if cyc_match:
                current_record['cpu_cycles'] = int(cyc_match.group(1))
                continue
                
            # Parse average CPU cycles
            cyc_avg_match = cycles_avg_re.search(line_str)
            if cyc_avg_match:
                current_record['cpu_cycles_avg'] = int(cyc_avg_match.group(1))
                continue
                
            # Parse prediction row data (contains raw and predicted water level)
            row_match = row_re.search(line_str)
            if row_match:
                current_record['row'] = int(row_match.group(1))
                current_record['wl_raw'] = float(row_match.group(2))
                current_record['pred_wl'] = float(row_match.group(3))
                current_record['anomaly'] = int(row_match.group(4))
                current_record['prob'] = float(row_match.group(5))
                
                # Each row line completes the current inference data block
                records.append(current_record)
                current_record = {}
                continue
                
        # Append the final block if it was not completed by a row line
        if current_record and 'row' in current_record:
            records.append(current_record)
            
    df = pd.DataFrame(records)
    print(f"Successfully parsed {len(df)} inference records.")
    return df

def main():
    # Resolve the default input path relative to this script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Workspace root is 2 levels up from scripts/plots/
    workspace_root = os.path.dirname(os.path.dirname(script_dir))
    default_file_path = os.path.join(workspace_root, 'hardware_projects', 'stm32output.txt')
    
    # Allow overriding file path via command line argument
    file_path = sys.argv[1] if len(sys.argv) > 1 else default_file_path
    
    # Parse output data
    df = parse_stm32_output(file_path)
    
    if df.empty:
        print("No valid inference records parsed. Exiting.")
        return
        
    # Print summary metrics to console
    anomalies_df = df[df['anomaly'] == 1]
    avg_dwt = df['duration_dwt'].mean()
    avg_cycles = df['cpu_cycles'].mean()
    
    print("\n" + "="*50)
    print("                SUMMARY METRICS")
    print("="*50)
    print(f"Total Inferences Evaluated : {len(df)}")
    print(f"Total Anomalies Detected   : {len(anomalies_df)}")
    print(f"Average Inference Time     : {avg_dwt:.3f} ms")
    print(f"Average CPU Cycles         : {int(avg_cycles):,}")
    if not anomalies_df.empty:
        print("\nDetected Anomalies:")
        for idx, row in anomalies_df.iterrows():
            print(f" - Inference #{int(row['inference_num'])} (Row {int(row['row'])}): "
                  f"Raw WL = {row['wl_raw']:.3f}m, Pred WL = {row['pred_wl']:.3f}m (Prob: {row['prob']:.4f})")
    print("="*50 + "\n")
    
    # ------------------ STYLING & MATPLOTLIB SETUP ------------------
    plt.style.use('dark_background')
    
    # Configure custom dark theme properties
    plt.rcParams['figure.facecolor'] = '#121214'
    plt.rcParams['axes.facecolor'] = '#1a1a1f'
    plt.rcParams['grid.color'] = '#2d2d3a'
    plt.rcParams['grid.linestyle'] = '--'
    plt.rcParams['grid.alpha'] = 0.5
    plt.rcParams['text.color'] = '#e0e0e0'
    plt.rcParams['axes.labelcolor'] = '#e0e0e0'
    plt.rcParams['xtick.color'] = '#a0a0a5'
    plt.rcParams['ytick.color'] = '#a0a0a5'
    plt.rcParams['axes.edgecolor'] = '#2d2d3a'
    plt.rcParams['font.sans-serif'] = ['Inter', 'Arial', 'DejaVu Sans', 'sans-serif']
    
    # Create the figure and subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    fig.canvas.manager.set_window_title('STM32 Model Serial Output Visualizer')
    
    x_axis = df['inference_num']
    
    # ------------------ SUBPLOT 1: WATER LEVEL ------------------
    # Raw sensor data line
    ax1.plot(x_axis, df['wl_raw'], label='Raw Sensor (WL_Raw)', color='#ff9f1c', linewidth=1.5, alpha=0.85)
    # Model predictions line
    ax1.plot(x_axis, df['pred_wl'], label='AR-MLP Prediction (Pred_WL)', color='#00b4d8', linewidth=2.0)
    
    # Highlight anomalies with red markers
    if not anomalies_df.empty:
        ax1.scatter(anomalies_df['inference_num'], anomalies_df['wl_raw'], 
                    color='#e63946', s=120, marker='x', zorder=5, label='Detected Anomaly', linewidths=2.5)
        # Add a light red shadow around anomaly points
        ax1.scatter(anomalies_df['inference_num'], anomalies_df['wl_raw'], 
                    color='#e63946', s=300, marker='o', zorder=4, alpha=0.2)
                    
    ax1.set_title('Water Level Predictions & Anomaly Detections', fontsize=12, fontweight='bold', color='#ffffff', loc='left', pad=10)
    ax1.set_ylabel('Water Level (m)', fontsize=10)
    ax1.grid(True)
    ax1.legend(loc='upper right', framealpha=0.8, edgecolor='#2d2d3a', facecolor='#121214')
    
    # ------------------ SUBPLOT 2: ANOMALY PROBABILITY ------------------
    ax2.plot(x_axis, df['prob'], color='#9d4edd', linewidth=1.8, label='Anomaly Probability')
    ax2.fill_between(x_axis, df['prob'], 0, color='#9d4edd', alpha=0.15)
    
    # Draw threshold line at 0.5
    ax2.axhline(0.5, color='#e63946', linestyle=':', alpha=0.8, linewidth=1.5, label='Anomaly Threshold (0.5)')
    
    ax2.set_title('Anomaly Probability (Keras Classifier)', fontsize=12, fontweight='bold', color='#ffffff', loc='left', pad=10)
    ax2.set_ylabel('Probability', fontsize=10)
    ax2.set_ylim(-0.05, 1.05)
    ax2.grid(True)
    ax2.legend(loc='upper right', framealpha=0.8, edgecolor='#2d2d3a', facecolor='#121214')
    
    # Shared X axis details
    ax2.set_xlabel('Inference Number', fontsize=10, labelpad=10)
    
    # Add stats overlay text box in figure space (bottom left corner)
    stats_text = (
        f"Total Inferences: {len(df)}\n"
        f"Anomalies: {len(anomalies_df)}\n"
        f"Avg Duration: {avg_dwt:.3f} ms\n"
        f"Avg Cycles: {int(avg_cycles):,}"
    )
    fig.text(0.02, 0.02, stats_text, color='#a0a0a5', fontsize=9,
             bbox=dict(boxstyle="round,pad=0.5", fc="#1a1a1f", ec="#2d2d3a", alpha=0.8))
    
    plt.tight_layout()
    # Leave room for the stats overlay box at the bottom
    plt.subplots_adjust(bottom=0.10)

    # ------------------ INTERACTIVE MOUSE cursor ------------------
    # Vertical cursor line indicators across all plots
    vlines = [
        ax1.axvline(x=x_axis.iloc[0], color='#ffffff', linestyle=':', alpha=0.7, visible=False),
        ax2.axvline(x=x_axis.iloc[0], color='#ffffff', linestyle=':', alpha=0.7, visible=False)
    ]
    
    # Tooltip box
    tooltip = ax1.annotate("", xy=(0, 0), xytext=(15, 15), textcoords="offset points",
                           bbox=dict(boxstyle="round,pad=0.5", fc="#1e1e24", ec="#4e4e62", alpha=0.95),
                           color="#e0e0e0", fontsize=9, fontweight='medium',
                           arrowprops=dict(arrowstyle="->", color="#4e4e62"))
    tooltip.set_visible(False)
    
    def on_mouse_move(event):
        if not event.inaxes or event.xdata is None:
            # Hide lines and tooltip
            for vline in vlines:
                vline.set_visible(False)
            tooltip.set_visible(False)
            fig.canvas.draw_idle()
            return
            
        x_val = event.xdata
        
        # Get nearest inference index
        idx = (df['inference_num'] - x_val).abs().idxmin()
        row = df.loc[idx]
        inf_num = row['inference_num']
        
        # Update vertical lines
        for vline in vlines:
            vline.set_xdata([inf_num, inf_num])
            vline.set_visible(True)
            
        # Tooltip text
        anom_str = "YES" if row['anomaly'] == 1 else "NO"
        text = (
            f"Inference: {int(row['inference_num'])} (Row {int(row['row'])})\n"
            f"  Raw WL      : {row['wl_raw']:.3f} m\n"
            f"  Pred WL     : {row['pred_wl']:.3f} m\n"
            f"  Difference  : {abs(row['wl_raw'] - row['pred_wl']):.3f} m\n"
            f"  Anomaly     : {anom_str} (Prob: {row['prob']:.4f})\n"
            f"  Time (DWT)  : {row['duration_dwt']:.3f} ms\n"
            f"  CPU Cycles  : {int(row['cpu_cycles'])} (avg: {int(row['cpu_cycles_avg'])})"
        )
        
        tooltip.set_text(text)
        
        # position tooltip relative to cursor
        tooltip.xy = (inf_num, event.ydata)
        tooltip.axes = event.inaxes
        tooltip.set_visible(True)
        
        fig.canvas.draw_idle()
        
    def on_click(event):
        if not event.inaxes or event.xdata is None:
            return
        idx = (df['inference_num'] - event.xdata).abs().idxmin()
        row = df.loc[idx]
        
        anom_str = "YES" if row['anomaly'] == 1 else "NO"
        print(f"\n[Inference {int(row['inference_num'])} details clicked]")
        print(f"  Dataset Row Index  : {int(row['row'])}")
        print(f"  Raw Water Level    : {row['wl_raw']:.3f} m")
        print(f"  Predicted Level    : {row['pred_wl']:.3f} m")
        print(f"  Difference (Error) : {abs(row['wl_raw'] - row['pred_wl']):.3f} m")
        print(f"  Anomaly Detected   : {anom_str} (probability: {row['prob']:.4f})")
        print(f"  CPU Execution cycles: {int(row['cpu_cycles'])} (average: {int(row['cpu_cycles_avg'])})")
        print(f"  DWT Duration       : {row['duration_dwt']:.3f} ms")
        print(f"  SysTick Duration   : {row['duration_systick']:.3f} ms")

    # Connect interactivity events
    fig.canvas.mpl_connect('motion_notify_event', on_mouse_move)
    fig.canvas.mpl_connect('button_press_event', on_click)
    
    print("Opening interactive matplotlib window. Hover to inspect values, click to print details in console.")
    plt.show()

if __name__ == '__main__':
    main()
