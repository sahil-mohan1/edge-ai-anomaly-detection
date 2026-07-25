# Edge AI Anomaly Detection

This repository contains the complete end-to-end project for a **smart water-level anomaly detection node**. The system is built for the **STM32WLE5 (LoRa-E5)** platform and leverages a custom **Autoregressive Multi-Layer Perceptron (AR-MLP)** to detect, classify, and reconstruct anomalous sensor readings in real-time on the edge before transmitting over LoRaWAN.

## Repository Structure

This is a monorepo that contains both the machine learning experimentation environment and the embedded firmware implementation:

### 1. `ml/` (Python ML Pipeline)
Contains the Python-based data processing, model training, and evaluation scripts.
* Includes scripts to build datasets from raw sensor logs.
* Trains the dual-branch AR-MLP and CNN models.
* Generates C-compatible headers (weights and test harnesses) for deployment.
* See [ml/README.md](ml/README.md) for full details.

### 2. `firmware/` (Embedded C Firmware)
Contains the embedded edge AI firmware for the LoRa-E5 module.
* Deploys the trained models using **STMicroelectronics X-CUBE-AI**.
* Reads distance data from the HLK radar level sensor.
* Runs the AR-MLP model dynamically to filter out physical glitches and simulated outages.
* Encodes the cleaned data and transmits it securely via the LoRaWAN MAC stack.
* See [firmware/README.md](firmware/README.md) for full details.

### 3. `docs/` (Project Documentation)
Contains project reports, feasibility studies, testing logs, and payload formats spanning the development cycles.

## Quick Start

* If you are looking to retrain the neural network or generate new test data, head to the **[ml/ directory](ml/README.md)**.
* If you are looking to build the C firmware and flash the STM32 microcontroller, head to the **[firmware/ directory](firmware/README.md)**.
