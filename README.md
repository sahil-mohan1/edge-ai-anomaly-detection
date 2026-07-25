# 🌊 Edge AI Water-Level Anomaly Detection & Correction

> **Intelligent Edge Computing for Resilient Environmental Monitoring**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![STM32](https://img.shields.io/badge/MCU-STM32WLE5-03234B?logo=stmicroelectronics&logoColor=white)
![LoRaWAN](https://img.shields.io/badge/LoRaWAN-ChirpStack-00BFFF?logo=lorawan&logoColor=white)
![TensorFlow Lite](https://img.shields.io/badge/TensorFlow_Lite-Edge_AI-FF6F00?logo=tensorflow&logoColor=white)
![Firmware](https://img.shields.io/badge/Firmware-C%2FC%2B%2B-00599C?logo=cplusplus&logoColor=white)
![Sensor](https://img.shields.io/badge/Sensor-24GHz_mmWave-009688)
![Flash Usage](https://img.shields.io/badge/Flash_Usage-~35_KB-9333EA)
![Latency](https://img.shields.io/badge/Inference_Latency-3--6_ms-E11D48)
![License](https://img.shields.io/badge/License-MIT-D97706)

This repository contains the complete end-to-end implementation of an **Edge AI-driven anomaly detection and data reconstruction system** for water-level monitoring. Built around the ultra-low-power **STM32WLE5 (LoRa-E5)** platform, this project pushes machine learning inference directly to the sensor node, neutralizing sensor unreliability at the source.

---

## 🧠 Neural Network Model Architecture

The core edge AI model is a custom **Dual-Branch Autoregressive Multi-Layer Perceptron (AR-MLP)** optimized for embedded time-series classification and trajectory reconstruction.

### Architecture Overview

To prevent dirty sensor readings (e.g. drop-to-zero spikes or hardware fault codes) from corrupting forecasting logic, the network uses a **split-feature dual-branch topology**:

1. **Classification Branch (Anomaly & Outage Detection)**: Processes all 23 features (including raw distance and hardware status) to compute the anomaly probability $P_{\text{anomaly}} \in [0, 1]$.
2. **Regression Branch (Autoregressive Reconstruction)**: Strips out volatile raw distance and error codes, taking only historical lags ($t-1 \dots t-8$) and cyclic temporal Fourier features. It calculates the reconstructed clean water level $\hat{y}_{\text{water}}$.
3. **Autoregressive Feedback Loop**: When an anomaly is detected ($P_{\text{anomaly}} > 0.5$), the system replaces the invalid sensor reading with $\hat{y}_{\text{water}}$ and feeds it back into the sliding window for subsequent inference steps.


### Layer Specifications & Topology

| Layer Name | Input / Feature Group | Activation | Output Shape | Parameters & Description |
| :--- | :--- | :--- | :--- | :--- |
| `features` | All 23 Input Features | — | `(None, 23)` | Normalised time-series feature vector |
| `hidden1_cls` | All 23 Features | ReLU | `(None, 64)` | Classification feature extraction |
| `hidden2_cls` | `hidden1_cls` | ReLU | `(None, 32)` | Intermediate anomaly pattern extraction |
| `anomaly` | `hidden2_cls` | Sigmoid | `(None, 1)` | Anomaly decision score $P(\text{Anomaly})$ |
| `hidden1_reg` | Lags & Time Features (2:23) | ReLU | `(None, 64)` | Noise-isolated temporal reconstruction |
| `hidden2_reg` | `hidden1_reg` | ReLU | `(None, 32)` | Intermediate time-series representation |
| `hidden3_reg` | `hidden2_reg` | ReLU | `(None, 16)` | Latent regression embedding |
| `wl` | `hidden3_reg` | Linear | `(None, 1)` | Water-level regression estimation |
| `output` | `[anomaly, wl]` | — | `(None, 2)` | Concatenated dual-branch output head |

### 23 Input Features Breakdown

```text
[0]  errorcode_norm     : Normalized native mmWave sensor status code
[1]  wl_raw_norm        : Normalized raw distance measurement from sensor
[2..9]  wl_lag_1..8     : 8 historical water-level steps (t-1 to t-8)
[10..19] cyclic_fourier : Sine/Cosine encodings for 1-week, 1-day, 12-hr, 6-hr, & 3-hr cycles
[20] weekly_bin_norm    : Scaled weekly cycle position
[21] day_of_week        : Categorical day representation
[22] prev_errorcode     : Historical hardware state indicator
```

---

## 🚀 Key Innovations & Features

- **On-Device Inference**: Deploys a custom, ultra-lightweight **Autoregressive Multi-Layer Perceptron (AR-MLP)** directly onto the microcontroller using STMicroelectronics' `X-CUBE-AI`.
- **Dual-Branch Neural Network Architecture**: 
  - **Classification Branch**: Actively detects physical glitches, hardware faults, and environmental noise in real-time (achieving **95.1% precision** and **97.3% recall**).
  - **Regression Branch**: Autoregressively reconstructs and forecasts missing data during prolonged sensor outages using a 16-step sliding window (achieving a highly accurate **RMSE of 0.88m**).
- **Extreme Hardware Efficiency**: The entire compiled `network` model utilizes just **~35 KB of Flash memory** and executes in a blistering **3-6 ms per inference**.
- **LoRaWAN Optimization**: Encodes the AI-validated, cleaned data into a minimal binary payload, saving tremendous bandwidth and extending battery life.

---

## 💻 Tech Stack & Hardware

### Hardware Components
* **Microcontroller / Radio**: LoRa-E5 (STM32WLE5JC) featuring an ARM Cortex-M4 core (256 KB Flash, 64 KB SRAM).
* **Sensor**: HLK-LD2413 24GHz Millimeter Wave (mmWave) Radar.
* **Power**: Li-Ion/Li-Po battery with ADC monitoring.

### Software & Frameworks
* **Edge AI Toolchain**: STMicroelectronics STM32Cube.AI, STM32CubeIDE (C/C++).
* **Machine Learning**: Python 3.12, TensorFlow / Keras.
* **Networking**: LoRaWAN Protocol, ChirpStack v3 Network Server.

---

---

## ⚠️ Known Limitations

* **Sensor Unreliability**: The HLK-LD2413 is prone to physical glitches. Surface turbulence, signal scattering, or physical vibration often cause transient spikes or sustained "drop-to-zero" flatlines. This system mathematically combats these errors, but the baseline hardware's physical limitations persist.
* **Restricted Training Horizon**: The current edge model was trained on datasets spanning strictly from February to May. It currently lacks full awareness of extreme seasonal flow dynamics (e.g., peak monsoon floods vs. dry season droughts).

---

## 🔮 Future Work & Roadmap

* **Seasonal Pattern Learning**: Expand the training dataset to encompass a full 1-year cycle. This will significantly improve the model's baseline accuracy by teaching it natural tidal and long-term seasonal patterns.
* **Targeted Fine-Tuning**: Curate highly clean, low-noise datasets (e.g., June data) for regression fine-tuning to sharpen exactly forecasted water levels.
* **Firmware Over-The-Air (FUOTA)**: Implement FUOTA capabilities over LoRaWAN to seamlessly retrain and deploy newly compiled model weights to edge devices in the field without manual intervention.

---

## 📂 Repository Architecture

This monorepo cleanly separates the machine learning research environment from the embedded deployment firmware.

### `1. /ml` — Machine Learning & Data Pipeline
Contains the Python-based data processing, model training, and evaluation scripts.
* Includes scripts to build datasets from raw sensor logs.
* Trains the dual-branch AR-MLP and CNN models.
* Generates C-compatible headers (weights and test harnesses) for deployment.
* 📖 **[Read the ML Documentation](ml/README.md)**

### `2. /firmware` — Embedded Edge Deployment
Contains the embedded edge AI firmware for the LoRa-E5 module.
* Deploys the trained models using **STMicroelectronics X-CUBE-AI**.
* Reads distance data from the HLK radar level sensor.
* Runs the AR-MLP model dynamically to filter out physical glitches and simulated outages.
* Encodes the cleaned data and transmits it securely via the LoRaWAN MAC stack.
* 📖 **[Read the Firmware Documentation](firmware/README.md)**

### `3. /docs` — Research & Documentation
Contains comprehensive project reports, feasibility studies, testing logs, and payload decoder formats (ChirpStack JavaScript codecs).

---

## 🛠️ Getting Started

* 🧠 **Want to train or evaluate the models?** Navigate to the **[`ml/` directory](ml/README.md)**.
* ⚡ **Want to flash the hardware?** Navigate to the **[`firmware/` directory](firmware/README.md)**.
