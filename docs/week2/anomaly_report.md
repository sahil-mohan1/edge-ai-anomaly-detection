# Peak Classification and Anomaly Report (HLK-LD2413 Sensor)

This report fulfills the deliverables for **Week 2 (Task 3: Identify the Nature of Unwanted Peaks)** of the Summer Internship - Anomaly Detection project. It provides visual graphs, classification of anomalous peaks, and root-cause observations.

---

## 📊 Visual Graph of Normal and Abnormal Readings

Below is the complete time-series plot of the merged dataset starting from `20-02-2026 14:49`. Normal readings (ErrorCode `0`) are plotted in green and teal, while anomalous conditions are highlighted with distinct marker shapes/colors according to their error status.

![HLK-LD2413 Sensor Time Series](../../plots/water_level_anomalies.png)

---

## 🔍 Peak & Anomaly Classification

The anomalies in the dataset correspond to status bytes (`errorcode`) transmitted in the UART frame of the HLK-LD2413 sensor. The table below classifies each error using your official protocol labels:

| Error Code | Official Label | Occurrences | Distance Value | Primary Behavior |
| :--- | :--- | :---: | :---: | :--- |
| **0** | **ok** | 7,520 (85.7%) | Varied (1.0m – 4.1m) | Expected fluctuations corresponding to actual water level changes. |
| **1** | **0 abort** | 449 (5.1%) | Exactly `0.0 m` | Water level drops to 0 (distance shown as 4.50m), likely target lost/aborted. |
| **2** | **sensor timeout** | 0 (0.0%) | N/A | No timeout code was recorded in this subset. |
| **3** | **spike detected** | 6 (0.1%) | Exactly `0.0 m` | Infrequent transient spikes causing target loss (water level drops to 0, distance shown as 4.50m). |
| **4** | **exceed limit** | 0 (0.0%) | N/A | No limit exceedances recorded in this subset. |
| **5** | **sensor unstable** | 804 (9.1%) | `0.0 m` (279) or drifting values | Water level drops to 0 or drifts due to target instability. |

---

## 💡 Root-Cause Observation Note

> [!NOTE]
> **Measurement Context:** The "Water Level" column in the **raw dataset** represents the **actual water level** relative to the channel bottom. 
> *   A **smaller value** (e.g., `0.5 m`) means the water level is low.
> *   A **larger value** (e.g., `3.5 m`) means the water level is high.
> However, for model training and preprocessing, this is converted to **Distance** (the distance from the sensor to the water surface), and the model's output is also **Distance**.
'
### 1. "0 abort" & "spike detected" Flatlines (Codes 1 & 3)
*   **Observation:** Whenever the status changes to `1` ("0 abort") or `3` ("spike detected"), the water level measurement flatlines at exactly `0.0 m` (which translates to a distance of `4.50 m`).
*   **Root Cause:** When a signal is aborted or a sudden target spike fails verification checks, the sensor fails to measure a valid target and outputs a water level of `0.0 m`. This zero water level is then calculated or plotted as a maximum distance limit (e.g. `4.50 m`).

### 2. "sensor unstable" (Code 5)
*   **Observation:** When status is `5` ("sensor unstable"), we see:
    *   Flatlines at `0.0 m` water level / `4.50 m` distance (279 times).
    *   Drifting water level values (e.g. 2.93m, 2.90m) that deviate from the smooth normal wave curve.
*   **Root Cause:** Caused by surface ripples, turbulence, or sensor structure vibration. The target reflection is highly unstable, returning scattered echoes. The sensor tries to lock onto a distance, yielding unstable, drifting values.
