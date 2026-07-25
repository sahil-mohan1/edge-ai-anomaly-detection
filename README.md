# 🌊 Edge AI Water-Level Anomaly Detection & Correction

> **Intelligent Edge Computing for Resilient Environmental Monitoring**

This repository contains the complete end-to-end implementation of an **Edge AI-driven anomaly detection and data reconstruction system** for water-level monitoring. Built around the ultra-low-power **STM32WLE5 (LoRa-E5)** platform, this project pushes machine learning inference directly to the sensor node, ensuring that only high-quality, validated data is transmitted over LoRaWAN.

By moving intelligence to the edge, this system drastically reduces bandwidth usage, minimizes cloud compute dependencies, and extends the battery life of remote environmental sensors.

---

## 🚀 Key Innovations & Features

- **On-Device Inference**: Deploys a custom, ultra-lightweight **Autoregressive Multi-Layer Perceptron (AR-MLP)** directly onto the microcontroller using STMicroelectronics' `X-CUBE-AI`.
- **Dual-Branch Neural Network Architecture**: 
  - **Classification Branch**: Actively detects physical glitches, hardware faults, and environmental noise in real-time (achieving **95.1% precision** and **97.3% recall**).
  - **Regression Branch**: Autoregressively reconstructs and forecasts missing data during prolonged sensor outages using a 16-step sliding window (achieving a highly accurate **RMSE of 0.88m**).
- **Extreme Hardware Efficiency**: The entire compiled `network` model utilizes just **~35 KB of Flash memory** and executes in a blistering **3-6 ms per inference**, easily fitting within the strict constraints of the LoRa-E5 module.
- **LoRaWAN Optimization**: Encodes the AI-validated, cleaned data into a minimal binary payload, maximizing the efficiency of the LoRaWAN (ChirpStack/TTN) transmission window.
- **Hybrid System Architecture**: A seamlessly integrated monorepo containing both the Python-based Machine Learning pipeline and the C-based Embedded Firmware.

---

## 📂 Repository Architecture

This project is structured as a monorepo, cleanly separating the machine learning research environment from the embedded deployment firmware.

### `1. /ml` — Machine Learning & Data Pipeline
The intelligence engine of the project. This Python environment is used to process raw sensor data, train the neural networks, and export the resulting weights for embedded deployment.
- **Data Engineering**: Scripts for time-series feature engineering, gap analysis, and simulated outage generation.
- **Model Training**: Implementation and training of the AR-MLP, CNN, and legacy baseline models (e.g., SNARIMAX, ARFR).
- **Embedded Exports**: Automated toolchains to convert trained `.keras` / `.tflite` models into optimized C-headers for STM32.
- 📖 **[Read the ML Documentation](ml/README.md)**

### `2. /firmware` — Embedded Edge Deployment
The physical execution layer. This contains the C/C++ source code configured for the **STM32CubeIDE** to run on the LoRa-E5 module.
- **X-CUBE-AI Integration**: Wraps the exported neural network into the main FreeRTOS application loop.
- **Sensor Drivers**: Interfaces directly with the HLK Radar Level Sensor to capture real-time distance metrics.
- **LoRaWAN Stack**: Integrates the ST SubGHz PHY and MAC layer to securely transmit the validated payload.
- 📖 **[Read the Firmware Documentation](firmware/README.md)**

### `3. /docs` — Research & Documentation
Contains comprehensive project reports, feasibility studies, testing logs, and payload decoder formats (ChirpStack JavaScript codecs) spanning the development lifecycle.

---

## ⚙️ System Workflow

1. **Data Acquisition**: The HLK radar sensor captures raw water-level distances.
2. **Feature Extraction**: The MCU processes the raw data, computing historical lags, cyclic Fourier features, and time-deltas.
3. **Edge Inference (AR-MLP)**: 
   - *Is the reading anomalous?* The classification branch flags it.
   - *Is the sensor offline?* The regression branch reconstructs the missing data based on learned temporal patterns.
4. **LoRaWAN Transmission**: Only the clean, validated (or accurately reconstructed) reading is packaged into a compact binary format and transmitted to the gateway.

---

## 🛠️ Getting Started

To dive into the specific components of this project, please refer to the detailed guides in their respective directories:

* 🧠 **Want to train or evaluate the models?** Navigate to the **[`ml/` directory](ml/README.md)** and follow the Python setup instructions.
* ⚡ **Want to flash the hardware?** Navigate to the **[`firmware/` directory](firmware/README.md)** and open the project in STM32CubeIDE.
