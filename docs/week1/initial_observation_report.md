# Initial Observation Report

## 1. Introduction
This report summarizes the initial observations of the HLK-LD2413 sensor data, specifically comparing normal operational data against periods containing known anomalies. The observations are based entirely on the contents of the `normal_data.csv` and `abnormal_data.csv` datasets, which were obtained from `combined_data.csv` by separating normal readings and anomalies.

## 2. Normal Operation Characteristics
Based on the `normal_data.csv` dataset, the sensor behaves predictably under standard conditions:
*   **Error Codes:** During normal operation, the sensor consistently reports an error code of `0`.
*   **Data Stability:** The measured water level fluctuates gradually (e.g., moving between `3.16m` and `1.45m`, which corresponds to actual distances of `1.34m` and `3.05m` respectively, based on a 4.5m max tank height). 
*   **Reporting Frequency:** Data points are logged at a regular 15-minute interval. There are no sudden, jagged leaps in water level measurements when operating normally.

## 3. Anomaly Characteristics
Based on the `abnormal_data.csv` dataset, several distinct anomalous behaviors have been identified:

### 3.1 Sharp Drops to Zero
The most prominent anomaly is a sudden and sustained drop in the reported water level from the sensor to `0.0` (which would falsely imply an empty tank or a distance of 4.5m). 
*   This is highly unnatural and clearly indicates a sensor fault, communication drop, or temporary outage.
*   These zero-distance readings are strongly correlated with an error code of `1`.

### 3.2 Transitional Error States
Prior to the sustained zero readings, the sensor occasionally outputs anomalous error codes:
*   **Error Code `5`:** Observed while still reporting a plausible water level (e.g., `2.63m`).
*   **Error Code `3`:** Observed exactly as the water level drops to `0.0`.
*   This suggests the sensor may experience a degradation in confidence or signal before fully failing to a zero-state.

## 4. Conclusion
The primary challenge for the anomaly detection logic will be differentiating between genuine, slow-moving water level changes and the sharp, sudden drops to `0.0` caused by sensor faults. The presence of non-zero error codes (`1`, `3`, `5`) serves as a highly reliable secondary indicator that the corresponding measurement is invalid and should be rejected or filtered during preprocessing.
