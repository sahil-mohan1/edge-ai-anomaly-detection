import pandas as pd
import numpy as np

files = [
    'data/processed/combined_data.csv',
    'data/processed/data-may26-june18_processed.csv'
]

for file in files:
    try:
        print(f"\n--- Analyzing {file.split('/')[-1]} (Filtering 0.0 anomalies) ---")
        df = pd.read_csv(file)
        
        # Mask for clean data: water level > 0.0 and errorcode == 0
        valid_mask = df['Water Level'] > 0.0
        if 'errorcode' in df.columns:
            valid_mask = valid_mask & (df['errorcode'] == 0)
            
        df_valid = df[valid_mask].copy()
        
        # We only want to compare points that were actually successive in the original data
        df_valid['original_idx'] = df_valid.index
        df_valid['water_diff'] = df_valid['Water Level'].diff().abs()
        df_valid['idx_diff'] = df_valid['original_idx'].diff()
        
        # Only keep differences where the original index difference is exactly 1
        successive_diffs = df_valid[df_valid['idx_diff'] == 1]['water_diff'].dropna()
        
        avg_change = successive_diffs.mean()
        min_change = successive_diffs.min()
        max_change = successive_diffs.max()
        median_change = successive_diffs.median()
        p95 = successive_diffs.quantile(0.95)
        p99 = successive_diffs.quantile(0.99)
        
        print(f"Total Valid Successive Pairs: {len(successive_diffs)}")
        print(f"Average Change: {avg_change:.5f} m")
        print(f"Median Change:  {median_change:.5f} m")
        print(f"95th %ile:      {p95:.5f} m")
        print(f"99th %ile:      {p99:.5f} m")
        print(f"Min Change:     {min_change:.5f} m")
        print(f"Max Change:     {max_change:.5f} m")
            
    except Exception as e:
        print(f"Could not process {file}: {e}")
