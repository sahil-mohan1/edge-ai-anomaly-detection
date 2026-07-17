import serial
import time
import pandas as pd
import argparse
import re

def main():
    parser = argparse.ArgumentParser(description="Send water level and error code via serial to STM32")
    parser.add_argument("--port", type=str, default="COM9", help="Serial port (e.g., COM3, /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate")
    parser.add_argument("--dataset", type=str, default=r"C:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\data\processed\data-july1-14_outage.csv", help="Path to the test dataset")
    parser.add_argument("--delay", type=float, default=60, help="Delay between sending data points in seconds")
    parser.add_argument("--output", type=str, default="stm32output.txt", help="Output file to save MCU responses")
    parser.add_argument("--start-row", type=int, default=0, help="Row index to start reading from the dataset (0-indexed)")
    args = parser.parse_args()

    print(f"Loading dataset from: {args.dataset}")
    try:
        df = pd.read_csv(args.dataset)
    except Exception as e:
        print(f"Failed to load dataset: {e}")
        return

    if 'Time' not in df.columns or 'Water Level' not in df.columns or 'errorcode' not in df.columns:
        print("Dataset missing required columns: 'Time', 'Water Level', or 'errorcode'")
        return
        
    if args.start_row > 0:
        if args.start_row >= len(df):
            print(f"Error: --start-row {args.start_row} is out of bounds for dataset with {len(df)} rows.")
            return
        df = df.iloc[args.start_row:]
        print(f"Starting from row {args.start_row}. {len(df)} rows remaining to send.")

    print(f"Opening serial port {args.port} at {args.baud} baud...")
    try:
        ser = serial.Serial(args.port, args.baud, timeout=1)
        time.sleep(2)  # Wait for connection to establish
    except Exception as e:
        print(f"Failed to open serial port: {e}")
        return

    out_file = open(args.output, 'w')
    print(f"Saving MCU output to: {args.output}")

    # We will handle everything in the loop now, based on MCU prompts.
    # To start, we might still send the first timestamp if the MCU is already waiting.
    # But it's safer to just let the loop handle it if the MCU prompts for it.
    # Let's send the first timestamp just in case the MCU missed our prompt check.
    start_timestamp = df.iloc[0]['Time']
    print(f"Sending initial starting timestamp: {start_timestamp}")
    start_timestamp_clean = str(start_timestamp).replace(" ", "_")
    ser.write(f"{start_timestamp_clean}\n".encode('utf-8'))
    
    current_index = 0

    raw_wls = []
    pred_wls = []
    anomalies = []

    # Infinite loop over dataset
    print("Starting data transmission loop. Press Ctrl+C to stop and plot early...")
    try:
        while current_index < len(df):
            if ser.in_waiting > 0:
                try:
                    response = ser.readline().decode('utf-8', errors='ignore').strip()
                    if response:
                        print(f"MCU: {response}")
                        out_file.write(response + "\n")
                        out_file.flush()

                        # Parse values for plotting
                        match = re.search(r"WL_Raw:\s*([\d\.]+),\s*Pred_WL:\s*([\d\.]+),\s*Anomaly:\s*(\d)", response)
                        if match:
                            raw_wls.append(float(match.group(1)))
                            pred_wls.append(float(match.group(2)))
                            anomalies.append(int(match.group(3)))

                        # Check if MCU is asking for timestamp
                        if "Enter starting timestamp" in response:
                            ts = df.iloc[current_index]['Time']
                            ts_clean = str(ts).replace(" ", "_")
                            print(f"Sending timestamp: {ts_clean}")
                            ser.write(f"{ts_clean}\n".encode('utf-8'))

                        # Check if MCU is asking for data
                        elif "Enter raw water level and error code:" in response:
                            row = df.iloc[current_index]
                            water_level = row['Water Level']
                            error_code = int(row['errorcode'])
                            
                            data_str = f"{water_level} {error_code}\n"
                            print(f"Sending [{current_index+1}/{len(df)}]: {data_str.strip()}")
                            ser.write(data_str.encode('utf-8'))
                            current_index += 1

                except Exception as e:
                    break
            else:
                time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nTransmission interrupted by user.")
    
    finally:
        out_file.close()
        ser.close()
        print("Finished serial communication.")
        
        # Save data required for plotting to CSV
        if len(raw_wls) > 0:
            csv_filename = args.output.replace('.txt', '_plot_data.csv')
            if '.txt' not in args.output:
                csv_filename = args.output + '_plot_data.csv'
                
            print(f"Saving plot data to: {csv_filename}")
            
            plot_df = pd.DataFrame({
                'Raw_Water_Level': raw_wls,
                'Predicted_Water_Level': pred_wls,
                'Anomaly': anomalies
            })
            plot_df.to_csv(csv_filename, index=False)
            print("Data saved successfully.")
        else:
            print("No valid data points received from MCU to save.")

if __name__ == "__main__":
    main()
