import argparse
import json
import pandas as pd
import numpy as np
import os

def main():
    parser = argparse.ArgumentParser(description="Generate dataset with a simulated outage.")
    parser.add_argument('--input', type=str, required=True, help='Path to the input processed CSV file')
    parser.add_argument('--output_csv', type=str, default=None, help='Path to output CSV dataset')
    parser.add_argument('--output_header', type=str, default=None, help='Path to output C++ header file')
    parser.add_argument('--output_metadata', type=str, default=None, help='Path to output JSON metadata file')
    parser.add_argument('--start', type=str, required=True, help='Start datetime of the outage (e.g. "27-06-2026 00:00" or "2026-06-27 00:00")')
    parser.add_argument('--end', type=str, required=True, help='End datetime of the outage (e.g. "30-06-2026 00:00" or "2026-06-30 00:00")')
    parser.add_argument('--errorcode', type=int, default=5, help='Error code to set during the outage (default 5)')

    args = parser.parse_args()

    print(f"Loading processed data from: {args.input}")
    df = pd.read_csv(args.input)
    
    # Parse Time to datetime objects for filtering
    if 'Time' not in df.columns:
        raise ValueError("Input CSV must contain a 'Time' column. Cannot continue without it.")
        
    df['Time_datetime'] = pd.to_datetime(df['Time'], errors='coerce', dayfirst=True)

    # Clean up baseline by forward/backward filling any random missing values
    if 'Water Level' in df.columns:
        df['Water Level'] = df['Water Level'].ffill().bfill()
        
    start_dt = pd.to_datetime(args.start, dayfirst=True)
    end_dt = pd.to_datetime(args.end, dayfirst=True)

    print(f"Applying outage from {start_dt} to {end_dt}")
    
    outage_mask = (df['Time_datetime'] >= start_dt) & (df['Time_datetime'] < end_dt)
    outage_count = outage_mask.sum()
    print(f"Number of samples in outage period: {outage_count}")

    if outage_count == 0:
        print("Warning: No samples found matching the outage date range!")
    
    # Identify indices for metadata
    outage_indices = df.index[outage_mask].tolist()
    if outage_indices:
        outage_start_idx = outage_indices[0]
        outage_length = len(outage_indices)
    else:
        outage_start_idx = 0
        outage_length = 0

    # Apply outage values
    if outage_count > 0:
        df.loc[outage_mask, 'Water Level'] = 0.0
        if 'errorcode' in df.columns:
            df.loc[outage_mask, 'errorcode'] = args.errorcode
        else:
            df['errorcode'] = 0
            df.loc[outage_mask, 'errorcode'] = args.errorcode

    # --- Generate CSV ---
    if args.output_csv:
        cols = ['Time', 'errorcode', 'Water Level'] if 'Time' in df.columns else ['errorcode', 'Water Level']
        df_output = df[cols]
        os.makedirs(os.path.dirname(args.output_csv) if os.path.dirname(args.output_csv) else '.', exist_ok=True)
        df_output.to_csv(args.output_csv, index=False)
        print(f"CSV saved to: {args.output_csv}")

    # --- Generate JSON Metadata ---
    if args.output_metadata:
        os.makedirs(os.path.dirname(args.output_metadata) if os.path.dirname(args.output_metadata) else '.', exist_ok=True)
        with open(args.output_metadata, 'w') as f:
            json.dump({'outage_start_idx': int(outage_start_idx), 'outage_length': int(outage_length)}, f)
        print(f"Metadata saved to: {args.output_metadata}")

    # --- Generate C++ Header ---
    if args.output_header:
        os.makedirs(os.path.dirname(args.output_header) if os.path.dirname(args.output_header) else '.', exist_ok=True)
        
        first_time = df['Time_datetime'].iloc[0]
        start_min_counter = (first_time.dayofweek * 1440) + (first_time.hour * 60) + first_time.minute
        
        with open(args.output_header, 'w') as f:
            f.write("#ifndef TEST_DATASET_H\n")
            f.write("#define TEST_DATASET_H\n\n")
            f.write(f"const int TEST_DATA_LENGTH = {len(df)};\n")
            f.write(f"const uint32_t test_start_min_counter = {start_min_counter};\n\n")
            
            f.write("const float test_water_levels[] = {\n")
            vals = df['Water Level'].values
            for i in range(0, len(vals), 10):
                chunk = vals[i:i+10]
                f.write("    " + ", ".join([f"{v:.4f}f" if not np.isnan(v) else "0.0f" for v in chunk]) + ",\n")
            f.write("};\n\n")
            
            f.write("const int test_errorcodes[] = {\n")
            errs = df['errorcode'].values
            for i in range(0, len(errs), 10):
                chunk = errs[i:i+10]
                f.write("    " + ", ".join([str(int(e)) for e in chunk]) + ",\n")
            f.write("};\n\n")
            
            f.write("#endif // TEST_DATASET_H\n")
        print(f"C++ header saved to: {args.output_header}")

if __name__ == '__main__':
    main()
