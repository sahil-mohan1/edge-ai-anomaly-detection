import pandas as pd
import numpy as np

input_path = r'c:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\data\raw\data-july1-14.csv'
output_path = r'c:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\data\processed\data-july1-14_processed_full.csv'

print(f"Reading raw data from: {input_path}")
df = pd.read_csv(input_path)
print(f"Initial shape: {df.shape}")

# Rename columns
df.columns = ['Time', 'value_str']

# Convert Time to datetime objects to ensure sorting and filtering
df['Datetime'] = pd.to_datetime(df['Time'])

# Sort chronologically just in case
df = df.sort_values(by='Datetime').reset_index(drop=True)

# Format the Time column as '%d-%m-%Y %H:%M'
df['Time'] = df['Datetime'].dt.strftime('%d-%m-%Y %H:%M')

# Function to parse string value and convert to distance from sensor (4.5 - wl)
def convert_value(val_str):
    if pd.isna(val_str):
        return np.nan
    val_str = str(val_str).strip().lower()
    try:
        if 'mm' in val_str:
            val = float(val_str.replace('mm', '').strip()) / 1000.0
        elif 'm' in val_str:
            val = float(val_str.replace('m', '').strip())
        else:
            val = float(val_str)
        
        dist = 4.5 - val
        return round(dist, 3)
    except Exception as e:
        print(f"Error parsing value '{val_str}': {e}")
        return np.nan

df['Water Level'] = df['value_str'].apply(convert_value)
df['errorcode'] = 0

# Select required columns in the exact order as other processed files
df_processed = df[['Time', 'errorcode', 'Water Level']]

print(f"Processed shape: {df_processed.shape}")
print("First 5 rows of processed data:")
print(df_processed.head())

df_processed.to_csv(output_path, index=False)
print(f"Processed data saved to {output_path}")
