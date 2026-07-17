import pandas as pd
import os

def combine_datasets():
    # Define file paths
    from pathlib import Path
    script_dir = Path(__file__).resolve().parent
    raw_dir = script_dir.parent / "data" / "raw"
    processed_dir = script_dir.parent / "data" / "processed"

    errorcode_path = raw_dir / "-data-12_09_43 - Copy.csv"
    water_level_path = raw_dir / "-data-12_19_49 - Copy.csv"
    output_path = processed_dir / "combined_data.csv"

    print("Loading datasets...")
    # Load the datasets
    df_err = pd.read_csv(errorcode_path)
    df_water = pd.read_csv(water_level_path)

    # Clean column names (strip whitespace and drop unnamed/empty columns caused by trailing commas)
    df_err = df_err.loc[:, ~df_err.columns.str.contains('^Unnamed')]
    df_err.columns = df_err.columns.str.strip()

    df_water = df_water.loc[:, ~df_water.columns.str.contains('^Unnamed')]
    df_water.columns = df_water.columns.str.strip()

    print(f"Errorcode columns: {list(df_err.columns)}")
    print(f"Water level columns: {list(df_water.columns)}")

    # Clean the errorcode column: remove 'm' and strip whitespaces
    if 'errorcode' in df_err.columns:
        df_err['errorcode'] = df_err['errorcode'].astype(str).str.replace('m', '', regex=False).str.strip()
    else:
        print("Warning: 'errorcode' column not found in errorcode dataset!")

    # Parse timestamps
    # Date format in CSVs is like "20-02-2026 11:34" -> %d-%m-%Y %H:%M
    df_err['Time_parsed'] = pd.to_datetime(df_err['Time'].str.strip(), format='%d-%m-%Y %H:%M', errors='coerce')
    df_water['Time_parsed'] = pd.to_datetime(df_water['Time'].str.strip(), format='%d-%m-%Y %H:%M', errors='coerce')

    # Target start timestamp: 20-02-2026 14:49
    start_time = pd.to_datetime("20-02-2026 14:49", format='%d-%m-%Y %H:%M')

    # Filter both datasets to start from 20-02-2026 14:49
    df_err_filtered = df_err[df_err['Time_parsed'] >= start_time].copy()
    df_water_filtered = df_water[df_water['Time_parsed'] >= start_time].copy()

    # Deduplicate timestamps to ensure a clean 1-to-1 mapping
    df_err_filtered = df_err_filtered.drop_duplicates(subset=['Time_parsed'], keep='first')
    df_water_filtered = df_water_filtered.drop_duplicates(subset=['Time_parsed'], keep='first')

    print(f"Deduplicated rows in errorcode dataset starting from {start_time}: {len(df_err_filtered)}")
    print(f"Deduplicated rows in water level dataset starting from {start_time}: {len(df_water_filtered)}")

    # Merge on the parsed Time column
    # We drop the temporary 'Time' string from the water level dataset to avoid duplicate column conflict
    df_water_filtered = df_water_filtered.drop(columns=['Time'])

    merged_df = pd.merge(df_err_filtered, df_water_filtered, on='Time_parsed', how='inner')

    # Sort by timestamp
    merged_df = merged_df.sort_values(by='Time_parsed')

    # Format the final output: keep clean string representation of Time
    merged_df['Time'] = merged_df['Time_parsed'].dt.strftime('%d-%m-%Y %H:%M')
    
    # Drop temporary parsing column
    merged_df = merged_df.drop(columns=['Time_parsed'])

    # Clean the Water Level column to float (converting mm to m if present, or stripping ' m')
    if 'Water Level' in merged_df.columns:
        def clean_water_level(val):
            if pd.isna(val):
                return val
            val_str = str(val).strip().lower()
            parsed_val = None
            if val_str.endswith('mm'):
                try:
                    parsed_val = float(val_str.replace('mm', '').strip()) / 1000.0
                except ValueError:
                    return val
            elif val_str.endswith('m'):
                try:
                    parsed_val = float(val_str.replace('m', '').strip())
                except ValueError:
                    return val
            else:
                try:
                    parsed_val = float(val_str)
                except ValueError:
                    return val
            
            if parsed_val is not None:
                # Convert raw distance from sensor to actual water level height
                # (Sensor is mounted at 4.5m height, measuring downwards)
                return round(4.5 - parsed_val, 4)
            return val
        
        merged_df['Water Level'] = merged_df['Water Level'].apply(clean_water_level)

    # Reorder columns to have Time first
    cols = ['Time', 'errorcode', 'Water Level']
    # Ensure all target columns are in the merged df before reordering
    cols = [c for c in cols if c in merged_df.columns]
    merged_df = merged_df[cols]

    print(f"Merged dataset row count: {len(merged_df)}")
    print("Preview of combined dataset:")
    print(merged_df.head(10))

    # Save to CSV
    merged_df.to_csv(output_path, index=False)
    print(f"Successfully saved combined dataset to {output_path}")

    # Maintain separate datasets for normal and abnormal conditions
    # Normal: errorcode is '0'
    # Abnormal: errorcode is anything other than '0'
    normal_df = merged_df[merged_df['errorcode'] == '0']
    abnormal_df = merged_df[merged_df['errorcode'] != '0']

    normal_path = processed_dir / "normal_data.csv"
    abnormal_path = processed_dir / "abnormal_data.csv"

    normal_df.to_csv(normal_path, index=False)
    abnormal_df.to_csv(abnormal_path, index=False)

    print(f"Successfully saved normal dataset ({len(normal_df)} rows) to {normal_path}")
    print(f"Successfully saved abnormal dataset ({len(abnormal_df)} rows) to {abnormal_path}")

if __name__ == '__main__':
    combine_datasets()
