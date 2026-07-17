import pandas as pd
import numpy as np
import os

def main():
    print("Loading training data to extract diurnal profile...")
    df = pd.read_csv(r"c:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\data\processed\training_dataset.csv")
    df['Time_datetime'] = pd.to_datetime(df['Time'], format="%d-%m-%Y %H:%M")
    
    # Calculate weekly diurnal means exactly as in plot_mlp_diurnal.py
    day_idx = (df['Time_datetime'].dt.dayofweek + 1) % 7 # Sunday=0, Monday=1, ...
    df['weekly_bin'] = day_idx * 96 + df['Time_datetime'].dt.hour * 4 + df['Time_datetime'].dt.minute // 15
    
    normal_samples = df[(df['is_anomaly'] == 0) & (df['wl_clean'] > 0)]
    diurnal_means = normal_samples.groupby('weekly_bin')['wl_clean'].mean().reindex(range(672))
    
    baseline_normal = 1.34
    diurnal_means = diurnal_means.interpolate(limit_direction='both').fillna(baseline_normal).values
    
    # Export to C++ header
    header_path = r"c:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\platformio_esp32_ar_mlp\include\diurnal_profile.h"
    os.makedirs(os.path.dirname(header_path), exist_ok=True)
    
    with open(header_path, "w") as f:
        f.write("#ifndef DIURNAL_PROFILE_H\n")
        f.write("#define DIURNAL_PROFILE_H\n\n")
        f.write("// Weekly diurnal profile extracted from training dataset\n")
        f.write("// Bins are 15-minute intervals starting from Sunday 00:00 (Total 672 bins)\n")
        f.write("const float diurnal_profile_means[672] = {\n")
        
        for i in range(0, 672, 8):
            chunk = diurnal_means[i:i+8]
            f.write("    " + ", ".join([f"{v:.4f}f" for v in chunk]) + ",\n")
            
        f.write("};\n\n")
        f.write("#endif // DIURNAL_PROFILE_H\n")
        
    print(f"Exported diurnal_profile.h to {header_path}")

if __name__ == '__main__':
    main()
