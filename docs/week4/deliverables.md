# Task 5 Deliverables

Here are the deliverables for the Filter Testing and Anomaly Detection task.

## 1. Filter Comparison Table

The following table summarizes the performance of all 5 tested filters evaluated against the manual ground truth (`filtered_data.csv`).

| Filter | RMSE (m) | MAE (m) | Max Error (m) | N |
| :--- | :--- | :--- | :--- | :--- |
| **Moving Average** | 0.7106 | 0.4131 | 2.7332 | 1285 |
| **Median Filter** | 0.6843 | 0.3396 | 3.4300 | 1285 |
| **EMA** | 0.7153 | 0.4434 | 2.7380 | 1285 |
| **Hampel Filter** | 0.6654 | 0.3265 | 3.4550 | 1285 |
| **Rate-of-Change Limiter** | 0.6749 | 0.3469 | 2.9700 | 1285 |
| **2D Kalman** | 0.7405 | 0.4302 | 3.0767 | 1285 |

> [!TIP]
> The **Hampel Filter** outperformed all other filters with the lowest RMSE (0.6654 m) and MAE (0.3265 m).

> [!WARNING]
> **Important Context:** The observed RMSE metrics (e.g., ~0.66m for the Hampel filter) reflect performance on isolated spikes. This is because prolonged sensor outages (`Error Code 1`) were explicitly masked via hard-rejection and handled with linear interpolation prior to filtering. If the raw 0.0 readings from these outages had been passed directly to the statistical filters, the overall error metrics would be significantly higher. While linear interpolation enables the filters to process the dataset seamlessly, it cannot reconstruct the complex, non-linear water level dynamics occurring during prolonged outages. This limitation establishes the baseline requirement for predictive Machine Learning models (Week 5) to accurately reconstruct extended periods of missing data.

---

## 2. Selected Filtering Logic

Based on the evaluation, the **Hampel Filter** is selected as the primary filter for handling isolated spikes. The complete data cleaning and filtering pipeline is:

1. **Hard Rejection**: Long outages flagged by the sensor's native status byte are replaced with `NaN`.
   - `Error Code 1` (0 abort / long outage) -> `NaN`
   - *(Note: `Error Code 5`, which indicates isolated spikes, is intentionally NOT hard-rejected so the filter can handle them).*
2. **Time-Grid Resampling**: Data is resampled and aligned to a uniform 15-minute grid using a nearest asof merge (with a 7-minute tolerance) to standardize intervals.
3. **Linear Interpolation**: Any resulting `NaN` gaps (like the `Error Code 1` outages) are filled using bidirectional linear interpolation.
4. **Hampel Filtering (Final Filter)**: The script walks through the interpolated series with a rolling window. If a reading deviates by more than 3 standard deviations (MAD) from the local median, it is identified as an outlier, replaced with `NaN`, and then interpolated.

---

## 3. Cleaned Output Graphs

Below is the graph of the selected filtering output (Hampel Filter), demonstrating how the algorithm handles the dataset, smoothing over sensor glitches and transient spikes.

![Cleaned Output Graph - Hampel Filter](../../plots/task5/task5_04_hampel.png)

For a comparative visualization of all the filter models evaluated:

![All Filters Comparison](../../plots/task5/task5_00_summary_all_filters.png)

---

## 4. Initial Anomaly Detection Logic

Drawing from the `anomaly_report.md` root cause analysis and the filter testing process, the initial rule-based anomaly detection logic uses two primary components:

### A. Protocol-level Status Anomaly Check (UART Context)
We intercept and flag raw readings based on errorcodes:
- **Rule**: If `errorcode` == 1 -> Identify as an Outage.
- **Reason**: The sensor returned Error Code 1 (0 abort).
- **Rule**: If `errorcode` == 3 -> Identify as an Anomaly.
- **Reason**: The sensor returned Error Code 3 (spike detected).
- **Rule**: If `errorcode` == 5 and WL == 0.0 -> Identify as an Anomaly.
- **Reason**: The sensor returned Error Code 5 (sensor unstable).

### B. Statistical Constraints Anomaly Check
Even if the sensor reports `ok` (0) or drifting data, we apply statistical domain constraints.
- **Rule**: If a reading deviates by > `3 * MAD` from the local rolling median -> Identify as a Statistical Outlier.
- **Reason**: The water reflection may be unstable (causing temporary drift), creating physical impossibilities over a short window.

These two initial layers will correctly classify both technical sensor errors and impossible physical events for alerting purposes.
