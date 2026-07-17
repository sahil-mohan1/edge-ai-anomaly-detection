import pandas as pd
import numpy as np

def analyze_gaps(csv_path):
    print(f"Reading dataset: {csv_path}")
    # Load the CSV
    df = pd.read_csv(csv_path)
    
    # Clean and parse Time
    df['Time_parsed'] = pd.to_datetime(df['Time'].str.strip(), format='%d-%m-%Y %H:%M')
    
    # Sort just in case it is out of order
    df = df.sort_values(by='Time_parsed').reset_index(drop=True)
    
    total_rows = len(df)
    start_time = df['Time_parsed'].min()
    end_time = df['Time_parsed'].max()
    
    print(f"Total rows in dataset: {total_rows}")
    print(f"Start Time: {start_time}")
    print(f"End Time: {end_time}")
    
    # Calculate difference between consecutive rows
    df['delta'] = df['Time_parsed'].diff()
    
    # The first row will have NaT, fill it or drop it for delta analysis
    deltas = df['delta'].dropna()
    
    # Convert deltas to minutes
    deltas_min = deltas.dt.total_seconds() / 60
    
    # Print basic statistics of deltas
    print("\n--- Time Delta Statistics ---")
    print(f"Expected frequency: 15 minutes")
    print(f"Minimum delta: {deltas_min.min()} minutes")
    print(f"Maximum delta: {deltas_min.max()} minutes")
    print(f"Mean delta: {deltas_min.mean():.2f} minutes")
    print(f"Median delta: {deltas_min.median()} minutes")
    
    # Distribute the deltas
    print("\n--- Distribution of Time Deltas ---")
    delta_counts = deltas_min.value_counts().sort_index()
    for delta, count in delta_counts.items():
        if delta == 15:
            print(f"  15 minutes (Expected): {count} times ({count/len(deltas)*100:.2f}%)")
        else:
            print(f"  {delta:.1f} minutes: {count} times ({count/len(deltas)*100:.2f}%)")
            
    # Identify gaps (deltas > 15 minutes)
    gaps = df[df['delta'] > pd.Timedelta(minutes=15)].copy()
    num_gaps = len(gaps)
    print(f"\nTotal number of gaps (delta > 15 mins): {num_gaps}")
    
    # Calculate overall missing data
    # Expected number of 15-minute intervals between start and end time
    total_duration = end_time - start_time
    expected_intervals = int(total_duration.total_seconds() / (15 * 60)) + 1
    missing_records = expected_intervals - total_rows
    missing_pct = (missing_records / expected_intervals) * 100
    
    print("\n--- Missing Data Summary ---")
    print(f"Expected intervals (if strictly 15-min): {expected_intervals}")
    print(f"Actual recorded intervals: {total_rows}")
    print(f"Missing records: {missing_records} ({missing_pct:.2f}%)")
    
    if num_gaps > 0:
        print("\n--- Top 15 Largest Gaps ---")
        gaps['gap_duration_mins'] = gaps['delta'].dt.total_seconds() / 60
        top_gaps = gaps.sort_values(by='gap_duration_mins', ascending=False).head(15)
        
        print(f"{'Gap Size':<15} | {'Gap Start (Previous Row)':<20} | {'Gap End (Current Row)':<20}")
        print("-" * 65)
        for idx, row in top_gaps.iterrows():
            current_time = row['Time_parsed']
            prev_time = current_time - row['delta']
            gap_size_str = f"{row['gap_duration_mins']:.0f} mins"
            print(f"{gap_size_str:<15} | {prev_time.strftime('%d-%m-%Y %H:%M'):<20} | {current_time.strftime('%d-%m-%Y %H:%M'):<20}")
            
        # Analyze temporal distribution of gaps (e.g., hour of day)
        gaps['hour'] = gaps['Time_parsed'].dt.hour
        print("\n--- Gaps by Hour of Day (When gaps ended) ---")
        hour_counts = gaps['hour'].value_counts().sort_index()
        for hr, cnt in hour_counts.items():
            print(f"  Hour {hr:02d}:00 - {cnt} gaps")

if __name__ == '__main__':
    from pathlib import Path
    csv_path = Path(__file__).resolve().parent.parent / "data" / "processed" / "combined_data.csv"
    analyze_gaps(csv_path)
