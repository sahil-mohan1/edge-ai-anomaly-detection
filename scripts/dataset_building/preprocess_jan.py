import pandas as pd
import numpy as np

input_path = r'c:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\data\raw\data-jan15-jan22.csv'
output_path = r'c:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\data\processed\data-jan15-jan22_processed.csv'

df = pd.read_csv(input_path)
df.columns = ['Time', 'value_str']

df['Time'] = pd.to_datetime(df['Time']).dt.strftime('%d-%m-%Y %H:%M')

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
        return np.nan

df['Water Level'] = df['value_str'].apply(convert_value)
df['errorcode'] = 0

df = df[['Time', 'errorcode', 'Water Level']]

df.to_csv(output_path, index=False)
print(f"Processed data saved to {output_path}")
