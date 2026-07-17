import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def main():
    # Paths definition
    workspace_dir = r'c:\Users\sahil\Desktop\ICFOSS\Anomaly Detection'
    processed_dir = os.path.join(workspace_dir, 'data', 'processed')
    default_path = 'combined_data.csv'
    
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    else:
        input_path = default_path
        
    # Generate list of paths to check (with and without .csv extension)
    input_paths_to_try = [input_path]
    if not input_path.lower().endswith('.csv'):
        input_paths_to_try.append(input_path + '.csv')
        
    file_path = None
    for ip in input_paths_to_try:
        possible_paths = [
            ip,                                                # 1. As given (absolute or relative to CWD)
            os.path.join(workspace_dir, ip),                   # 2. Relative to workspace root
            os.path.join(processed_dir, ip),                   # 3. Relative to data/processed
            os.path.join(processed_dir, os.path.basename(ip))  # 4. Filename only inside data/processed
        ]
        for p in possible_paths:
            if os.path.exists(p) and os.path.isfile(p):
                file_path = p
                break
        if file_path:
            break
            
    if not file_path:
        print(f"Error: Could not locate dataset file for '{input_path}'.")
        print(f"Usage: python plot_datasets.py [csv_filename_or_path]")
        return

    print(f"Loading data from: {file_path}")
    
    try:
        df = pd.read_csv(file_path, parse_dates=['Time'], dayfirst=True)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return
        
    if 'Time' not in df.columns or 'Water Level' not in df.columns:
        print("Error: CSV must contain 'Time' and 'Water Level' columns.")
        print(f"Available columns: {list(df.columns)}")
        return
        
    # Sort by time
    df = df.sort_values('Time')
    
    # Plotting
    plt.figure(figsize=(15, 6))
    # Plotting just the Water Level, ignoring other fields
    plt.plot(df['Time'], df['Water Level'], color='blue', linewidth=1, label='Water Level')
    
    file_name = os.path.basename(file_path)
    plt.title(f'Water Level over Time ({file_name})')
    plt.xlabel('Time')
    plt.ylabel('Distance (m)')
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    
    ax = plt.gca()
    ax.format_coord = lambda x, y: mdates.num2date(x).strftime('%Y-%m-%d %H:%M:%S')
    
    # Show the interactive plot window
    print("Opening Matplotlib GUI window...")
    plt.show()

if __name__ == '__main__':
    main()
