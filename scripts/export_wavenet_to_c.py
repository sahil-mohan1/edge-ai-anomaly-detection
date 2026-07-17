import os
import pandas as pd
import numpy as np

def convert_model_to_c_array(tflite_path, header_path, array_name):
    with open(tflite_path, 'rb') as f:
        model_data = f.read()

    with open(header_path, 'w') as f:
        f.write(f"#ifndef {array_name.upper()}_H\n")
        f.write(f"#define {array_name.upper()}_H\n\n")
        f.write(f"const unsigned char {array_name}[] = {{\n")
        
        hex_data = [f"0x{b:02x}" for b in model_data]
        for i in range(0, len(hex_data), 12):
            f.write("  " + ", ".join(hex_data[i:i+12]) + ",\n")
            
        f.write("};\n\n")
        f.write(f"const unsigned int {array_name}_len = {len(model_data)};\n\n")
        f.write("#endif\n")

def convert_dataset_to_c_array(csv_path, header_path):
    df = pd.read_csv(csv_path)
    
    df['Time_datetime'] = pd.to_datetime(df['Time'], format="%d-%m-%Y %H:%M")
    df = (df.set_index('Time_datetime')
            .resample('15min').ffill()
            .reset_index())
            
    # Try to find relevant columns, assuming 'Water Level' and 'errorcode'
    if 'Water Level' in df.columns:
        wl_data = df['Water Level'].ffill().bfill().values
    elif 'WaterLevel' in df.columns:
        wl_data = df['WaterLevel'].ffill().bfill().values
    else:
        wl_data = df.iloc[:, 2].ffill().bfill().values

    if 'errorcode' in df.columns:
        ec_data = df['errorcode'].fillna(0).values
    elif 'ErrorCode' in df.columns:
        ec_data = df['ErrorCode'].fillna(0).values
    else:
        ec_data = np.zeros_like(wl_data)
        
    # Limit dataset size to avoid massive header file (e.g. 500 lines max for testing)
    max_len = min(500, len(wl_data))
    
    with open(header_path, 'w') as f:
        f.write("#ifndef TEST_DATASET_H\n")
        f.write("#define TEST_DATASET_H\n\n")
        
        f.write(f"const unsigned int TEST_DATA_LENGTH = {max_len};\n\n")
        
        f.write("const float test_water_levels[] = {\n")
        for i in range(max_len):
            f.write(f"  {wl_data[i]}f,\n")
        f.write("};\n\n")
        
        f.write("const int test_errorcodes[] = {\n")
        for i in range(max_len):
            f.write(f"  {int(ec_data[i])},\n")
        f.write("};\n\n")
        
        f.write("#endif\n")

if __name__ == "__main__":
    tflite_model = r"c:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\models\saved\water_level_wavenet.tflite"
    out_model_header = r"c:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\hardware_projects\platformio_wavenet_esp32\include\wavenet_model_data.h"
    convert_model_to_c_array(tflite_model, out_model_header, "water_level_wavenet_tflite")
    
    dataset_csv = r"c:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\data\processed\data-may26-june18_processed.csv"
    out_dataset_header = r"c:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\hardware_projects\platformio_wavenet_esp32\include\test_dataset.h"
    convert_dataset_to_c_array(dataset_csv, out_dataset_header)
    print("Exported model and dataset to C arrays.")
