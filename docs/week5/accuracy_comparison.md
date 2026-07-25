# Detection Accuracy Comparison

This document provides an overview of the anomaly detection accuracy for the deployed **Large AR-MLP** model, compared against baseline rule-based methods and earlier CNN iterations.

## Evaluation Metrics

The models were evaluated using the following classification metrics on the validation dataset:
- **Precision:** The proportion of flagged anomalies that were true anomalies.
- **Recall:** The proportion of true anomalies that were successfully detected by the system.
- **F1-Score:** The harmonic mean of precision and recall.

## Accuracy Results

| Model / Approach | Precision | Recall | F1-Score | Inference Latency (Edge) | Memory Footprint |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Pure Rule-Based (Bounds & ROC)** | 98.5% | 75.2% | 85.3% | < 1 ms | ~5 KB |
| *TinyML 1D-CNN (Previous Baseline)* | *94.2%* | *96.8%* | *95.5%* | *~2-5 ms* | *~7 KB* |
| **Large AR-MLP (Selected)** | **95.1%** | **97.3%** | **96.2%** | **~3-6 ms** | **~35 KB** |

## Analysis

### Large AR-MLP Performance
The AR-MLP demonstrates the highest **Recall (97.3%)** and **F1-Score (96.2%)** across all tested models. While rule-based systems (75.2% recall) fail to detect subtle contextual anomalies (such as gradual sensor drift within normal operating bounds), the AR-MLP successfully captures these temporal dependencies by evaluating a sliding window of historical lags and encoded time features.

> [!WARNING]
> **Context on Classification Accuracy:** The extremely high classification performance is largely a result of the dataset's nature and feature selection. The model is provided the sensor's hardware `errorcode` as a direct input feature. Because the anomalies in the training dataset are almost entirely hardware-triggered events, the classification branch easily learns this deterministic relationship. Therefore, the true value of the AR-MLP lies not in anomaly *classification* (which simple rule-based checks can handle via error codes), but rather in its robust *regression and imputation* capabilities during those outages.


### Key Advantages
- **Classification vs. Imputation:** Unlike the 1D-CNN, which was built purely for classification, the AR-MLP simultaneously performs classification and regression (imputation). This allows the system to not only detect the anomaly but also predict the missing water level, seamlessly bridging data gaps.
- **Resource Constraints:** Despite having a significantly larger parameter count than the initial CNN, the Float32 TFLite export of the AR-MLP requires only ~35 KB of memory. This falls well within the flash and RAM constraints of the STM32 microcontroller, enabling offline, real-time inference without cloud dependency.

---

## Data Reconstruction Metrics (Imputation)

Because anomaly classification is often firmly governed by physical boundary rules, it is equally important to evaluate the regression capabilities of each model to reconstruct missing sensor data during a hardware outage (autoregressive mode). 

| Metric | Linear Regression | 1D CNN | WaveNet | AR MLP |
| :--- | :---: | :---: | :---: | :---: |
| **RMSE** | 0.9232 | 1.3886 | 1.0458 | **0.8821** | 
| **MAE** | 0.4946 | 0.8860 | 0.6933 | **0.4818** | 

The Large AR-MLP achieves the lowest errors (RMSE and MAE) during prolonged simulated outages compared to the other architectures.



