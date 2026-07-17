# Selected Anomaly Detection Method

The primary anomaly detection method selected for this project is an **Autoregressive Multi-Layer Perceptron (AR-MLP)**. This model was chosen to provide robust, dual-purpose functionality: accurate classification of sensor anomalies and real-time regression (imputation) of missing water level data directly on the edge.

## Rationale for Selection
While simpler rule-based systems are effective for obvious hardware failures (e.g., sensor flatlines or error codes), they fail to impute missing data during prolonged outages. Pure convolutional approaches (like 1D-CNNs) struggled to bridge long data gaps gracefully without complex zero-padding logic. 

The AR-MLP solves this by:
- **Autoregressive Imputation:** During normal operation, the model continuously predicts the current water level based on past lags. When an anomaly or outage occurs, it feeds its own predictions back into its sliding window, allowing it to seamlessly bridge missing gaps over several hours.
- **Dual-Branch Architecture:** It simultaneously performs classification (is it an anomaly?) and regression (what should the water level be?), optimizing computational efficiency by sharing the same input tensor.
- **STM32 Edge Deployment:** Despite being larger compared to our initial TinyML models, this AR-MLP (Float32 TFLite) is fully supported by the **STM32Cube.AI** toolchain. It can execute directly on the STM32 microcontroller (in the `hardware_projects/waterlevel1` environment), ensuring zero-latency, offline anomaly detection without cloud dependence.

## Model Architecture
- **Input (23 Features):** The input tensor combines current readings (`errorcode_norm`, `wl_raw_norm`), 8 autoregressive lags of clean water levels, 12 cyclic time-encoding features (sine/cosine representations for time of day and week), and the previous error code.
- **Classification Branch:** Uses all 23 features, passing through Dense layers (64 -> 32) to a final **Sigmoid** output node yielding an anomaly probability (0.0 to 1.0).
- **Regression Branch:** Uses only the lags and time features (21 features, intentionally ignoring the corrupt current readings), passing through Dense layers (64 -> 32 -> 16) to a final **Linear** output node yielding the predicted clean water level.
- **Multi-Step Training:** The model is trained using Scheduled Sampling over a 16-step sequence (4 hours) to prevent autoregressive drift during inference.

By shifting the computational intelligence directly to the STM32 sensor node via this AR-MLP, the system guarantees reliable data collection and immediate anomaly response.
