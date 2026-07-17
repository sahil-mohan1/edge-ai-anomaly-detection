import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from itertools import groupby
from operator import itemgetter

# Path to the processed outage dataset
file_path = r'c:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\data\processed\data-june6-july1_outage.csv'

# Load the data
print(f"Loading data from: {file_path}")
df = pd.read_csv(file_path)

# Convert Time to datetime
df['Datetime'] = pd.to_datetime(df['Time'], format='%d-%m-%Y %H:%M')

# Plot setup
plt.figure(figsize=(12, 6))

# Plot the water level
plt.plot(df['Datetime'], df['Water Level'], label='Water Level (Distance from sensor)', color='#1f77b4', linewidth=1.5)

# Find outage indices/regions where errorcode == 5
outage_mask = df['errorcode'] == 5
if outage_mask.any():
    outage_indices = df[outage_mask].index
    # Group contiguous indices to draw span regions
    legend_added = False
    for k, g in groupby(enumerate(outage_indices), lambda ix: ix[0] - ix[1]):
        group = list(map(itemgetter(1), g))
        start_time = df['Datetime'].iloc[group[0]]
        end_time = df['Datetime'].iloc[group[-1]]
        
        label = 'Simulated Outage (errorcode=5)' if not legend_added else ""
        plt.axvspan(start_time, end_time, color='red', alpha=0.18, label=label)
        legend_added = True

# Formatting the plot
plt.title('Water Level with Simulated Outage - June 24 to July 1', fontsize=14, fontweight='bold', pad=15)
plt.xlabel('Date & Time', fontsize=12)
plt.ylabel('Distance from Sensor (m)', fontsize=12)

# Format x-axis to show dates nicely
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d-%b %H:%M'))
plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))
plt.gcf().autofmt_xdate() # Rotate date labels

plt.grid(True, linestyle='--', alpha=0.6)
plt.legend(loc='upper right', frameon=True)
plt.tight_layout()

print("Displaying matplotlib window...")
plt.show()
