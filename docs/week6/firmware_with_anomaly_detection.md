# Firmware with Anomaly Detection

This document summarizes the integration of the edge anomaly detection model into the main LoRaWAN firmware. The complete project is located in the `hardware_projects/E5_hlk_RLS` directory.

### Project Overview
The firmware is built for the STM32WLE5 MCU (LoRa-E5) and serves two primary functions:
1. **Anomaly Detection**: Running the water level sensor data through the deployed neural network using the X-CUBE-AI library.
2. **LoRaWAN Connectivity**: Encoding the sensor data, anomalies, and logs into a custom payload format and transmitting it via the LoRa-E5 module.

### Implementation Details
The application logic is primarily contained within `LoRaWAN/App/lora_app.c`. 

*   **AI Processing**: 
    The network processing is invoked through `STM32CubeAI_Studio_AI_Process()`. This function feeds the raw sensor data into the model, computes the anomaly predictions, and updates the state variables like the `error_code`.
*   **Payload Construction**: 
    The `SendTxData()` function takes the resulting `error_code`, along with the current battery level and historical distance logs, and formats them into a Big Endian byte buffer (`AppData.Buffer`). 
*   **Transmission**: 
    Finally, `LmHandlerSend(&AppData, ...)` is called to schedule the data packet for LoRaWAN transmission.

By combining the AI model directly on the MCU that handles the LoRa stack, this architecture provides a low-power, edge-intelligent solution capable of identifying and reporting anomalies in real-time.
