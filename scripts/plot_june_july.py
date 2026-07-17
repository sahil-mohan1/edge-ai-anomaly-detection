import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Path to the processed dataset
file_path = r'c:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\data\processed\data-june6-july1_processed.csv'

# Load the data
print(f"Loading data from: {file_path}")
df = pd.read_csv(file_path)

# Convert Time to datetime
df['Datetime'] = pd.to_datetime(df['Time'], format='%d-%m-%Y %H:%M')

# Plot setup
plt.figure(figsize=(12, 6))
plt.plot(df['Datetime'], df['Water Level'], label='Water Level (Distance from sensor)', color='#1f77b4', linewidth=1.5)

# Formatting the plot
plt.title('Water Level (Distance from Sensor) - June 24 to July 1', fontsize=14, fontweight='bold', pad=15)
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
