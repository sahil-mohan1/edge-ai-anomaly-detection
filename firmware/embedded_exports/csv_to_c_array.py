import pandas as pd
import time
import datetime

datasets = [
    r"C:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\data\processed\data-may26-june18_processed.csv",
    r"C:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\data\processed\data-june6-july1_processed.csv",
    r"C:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\data\processed\data-jan15-jan22_processed.csv"
]

print("Select dataset:")
print("0: May 26 - June 18")
print("1: June 6 - July 1")
print("2: Jan 15 - Jan 22")
dataset_idx = int(input("Enter choice (0, 1, or 2): "))

start_row = int(input("Enter starting row number (will read 100 rows): "))

df = pd.read_csv(datasets[dataset_idx])
df = df.iloc[start_row : start_row + 100]

header_path = r"C:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\hardware_projects\waterlevel1\AI\App\test_data.h"

with open(header_path, "w") as f:
    f.write("#ifndef TEST_DATA_H\n")
    f.write("#define TEST_DATA_H\n\n")
    f.write("#include <stdint.h>\n\n")
    
    f.write("typedef struct {\n")
    f.write("    uint32_t ts;\n")
    f.write("    uint8_t errorcode;\n")
    f.write("    float wl_raw;\n")
    f.write("} SensorDataPoint;\n\n")
    
    f.write(f"#define TEST_DATA_LENGTH {len(df)}\n\n")
    
    f.write("const SensorDataPoint test_data[TEST_DATA_LENGTH] = {\n")
    
    for index, row in df.iterrows():
        # Parse timestamp "dd-mm-yyyy HH:MM"
        time_str = row['Time']
        dt = datetime.datetime.strptime(time_str, "%d-%m-%Y %H:%M")
        # Ensure it works in standard C library localtime logic (time_t)
        ts = int(dt.timestamp())
        
        err = int(row['errorcode'])
        wl = float(row['Water Level'])
        

        f.write(f"    {{ {ts}, {err}, {wl}f }},\n")
        
    f.write("};\n\n")
    f.write("#endif // TEST_DATA_H\n")

print(f"Successfully wrote {len(df)} rows to {header_path}")
