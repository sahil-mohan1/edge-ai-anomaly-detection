import pandas as pd

df = pd.read_csv('data/processed/combined_data.csv')
valid_mask = (df['Water Level'] > 0.0) & (df['errorcode'] == 0)
df_valid = df[valid_mask].copy()

df_valid['original_idx'] = df_valid.index
df_valid['water_diff'] = df_valid['Water Level'].diff().abs()
df_valid['idx_diff'] = df_valid['original_idx'].diff()

successive = df_valid[df_valid['idx_diff'] == 1]
max_idx = successive['water_diff'].idxmax()

print(f"Maximum legitimate change of {successive.loc[max_idx, 'water_diff']:.3f}m occurred at index {max_idx}")
print("\nSurrounding Context in Raw Data:")
print(df.loc[max_idx-2:max_idx+2].to_string())
