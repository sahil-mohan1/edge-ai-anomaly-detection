# 🧠 Machine Learning & Data Pipeline

Welcome to the data engineering and neural network training environment for the Edge AI water-level anomaly detection project. This directory encapsulates the entire Python workflow—from raw sensor CSV parsing to exporting optimized C headers for the STM32 microcontroller.

## 🚀 Core Capabilities

- **Time-Series Feature Engineering**: Enriches raw HLK-LD2413 sensor distance logs with complex temporal data. This includes 8-step historical lags and cyclic Fourier features (day, half-day, weekly cycles) to help the model learn natural tidal rhythms.
- **Data Augmentation**: Intelligently injects synthetic "drop-to-zero" spikes and simulated hardware faults into clean datasets to ensure the classification model is robust against rare physical anomalies.
- **Model Training**: Home to the **Autoregressive Multi-Layer Perceptron (AR-MLP)** and baseline models (1D-CNN, WaveNet, SNARIMAX). The AR-MLP is trained using multi-step scheduled sampling over a 16-step horizon to prevent drift during prolonged outages.
- **Embedded Export Toolchain**: Automates the conversion of Keras (`.keras`) and TensorFlow Lite (`.tflite`) models into heavily quantized C-compatible byte arrays (`.h`), ensuring seamless integration with the X-CUBE-AI firmware layer.

## 📂 Directory Breakdown

```text
ml/
├── data/
│   ├── raw/             # Raw sensor exports directly from the serial logger.
│   └── processed/       # Cleaned datasets, time-aligned with synthetic outages added.
├── models/
│   ├── saved/           # Pickled baselines and trained `.keras` / `.tflite` model files.
│   ├── archive/         # Legacy statistical models (SNARIMAX, ARFR).
│   └── feature_engineering.py # Data transformation and scaling logic.
├── scripts/
│   ├── dataset_building/   # Scripts that generate the synthetic and training datasets.
│   ├── model_training/     # Core training loops (MLP, WaveNet, CNN architectures).
│   ├── embedded_exports/   # TFLite -> C header conversion (`convert_tflite_to_c.py`).
│   ├── filters/            # Legacy statistical filters (Hampel, Kalman, EMA).
│   └── *.py / *.exe        # Compiled executables for real-time visualization and testing.
├── notebooks/           # Jupyter notebooks for Exploratory Data Analysis (EDA).
├── plots/               # Automatically generated performance visualizations.
├── pi_deployment/       # Scripts and requirements for running edge inference on a Raspberry Pi.
└── run_pipeline.py      # The primary end-to-end Python pipeline entry point.
```

## 🛠️ Getting Started

### 1. Environment Setup
It is highly recommended to use a virtual environment. Install the required dependencies:
```bash
pip install -r pi_deployment/requirements.txt
```

### 2. Running the Training Pipeline
To retrain the AR-MLP models on the latest dataset or to run the baseline comparisons:
```bash
python run_pipeline.py
```

### 3. Generating Embedded C Headers
Once you are satisfied with a trained model, you can export it for the STM32 MCU. This script converts the `.tflite` graph into a flat C array and generates a test harness:
```bash
python scripts/embedded_exports/convert_tflite_to_c.py
python scripts/embedded_exports/generate_test_harness.py
```
The resulting files will automatically be placed in the `../firmware/embedded_exports/` directory, ready to be compiled by STM32CubeIDE.
