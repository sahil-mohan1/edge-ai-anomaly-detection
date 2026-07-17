# HLK-LD2413 Communication Note

This document summarizes the communication protocol and interface settings for the HLK-LD2413 miniaturized high-precision liquid level detection millimeter wave sensor.

## Hardware Interface
- **Communication Type:** UART (Serial) at TTL level (3.3V).
- **Pin Connections (J1 Header):**
  - **Pin 3 (OT1):** UART_TX (Sensor Transmit -> Host Receive)
  - **Pin 4 (RX):** UART_RX (Host Transmit -> Sensor Receive)
  - **Pin 1 (3V3):** 3.3V Power Input
  - **Pin 2 (GND):** Ground

## Serial Port Configuration
To communicate with the sensor or read the data stream, the serial port must be configured with the following default settings:
- **Baud Rate:** 115200
- **Data Bits:** 8
- **Stop Bits:** 1
- **Parity Bit:** None (No parity)

## Data Representation
- **Byte Order:** All data frames and command values use **Little-Endian** format.
- **Reporting Cycle:** The default data reporting cycle is 160 ms (configurable between 50 ms and 1000 ms).
- **Unit of Measurement:** The sensor firmware natively reports the distance in **millimeters (mm)** as a 32-bit floating point number. (Note: the official host tool displays this in cm).

## Debugging and Visualization
The sensor can be interfaced directly via a USB-to-TTL adapter board (Connect Sensor TX to Adapter RX, and Sensor RX to Adapter TX). 
Hi-link provides an official host computer tool (`HLK-LD2413_Tool`) which allows for visualizing the real-time distance curve and configuring parameters such as the minimum/maximum detection distance and reporting cycle. Note that third-party serial terminals (like PuTTY or TeraTerm) cannot be used concurrently with the official visualizer tool.
