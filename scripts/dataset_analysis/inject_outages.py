import pandas as pd
import numpy as np
import os

workspace_dir = r'c:\Users\sahil\Desktop\ICFOSS\Anomaly Detection'
input_path = os.path.join(workspace_dir, 'data', 'processed', 'data-july1-14_processed.csv')
output_path = os.path.join(workspace_dir, 'data', 'processed', 'data-july1-14_outage.csv')

df = pd.read_csv(input_path)
df['Time'] = pd.to_datetime(df['Time'], format='%d-%m-%Y %H:%M')

# Set up long outages
# July 3-4
long_outage_1_mask = (df['Time'] >= '2026-07-03') & (df['Time'] < '2026-07-05')
df.loc[long_outage_1_mask, 'errorcode'] = 1
df.loc[long_outage_1_mask, 'Water Level'] = 0

# July 9 14:28 to July 12 14:28
long_outage_2_mask = (df['Time'] >= '2026-07-09 14:28') & (df['Time'] < '2026-07-12 14:28')
df.loc[long_outage_2_mask, 'errorcode'] = 1
df.loc[long_outage_2_mask, 'Water Level'] = 0

# Set up short outages
# Find indices that are not already part of long outages
available_indices = df[~df['errorcode'].isin([1])].index.tolist()

np.random.seed(42) # For reproducibility
num_short_outages = 20

for _ in range(num_short_outages):
    if not available_indices:
        break
    
    # Pick a random start index
    start_idx = np.random.choice(available_indices)
    
    # Decide length: 1 or 2
    length = np.random.choice([1, 2])
    
    # Apply outage
    for i in range(start_idx, start_idx + length):
        if i in df.index and df.loc[i, 'errorcode'] != 1:
            df.loc[i, 'errorcode'] = 5
            df.loc[i, 'Water Level'] = 0
            if i in available_indices:
                available_indices.remove(i)

df['Time'] = df['Time'].dt.strftime('%d-%m-%Y %H:%M')
df.to_csv(output_path, index=False)
print(f"Dataset generated at {output_path}")
