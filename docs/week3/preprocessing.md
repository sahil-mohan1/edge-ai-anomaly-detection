# Pre-Processing Documentation (Simulated Sensor Data)

This document fulfills the deliverables for **Week 3 (Task 4: Implement Basic Pre-Processing)** of the Summer Internship - Anomaly Detection project. 

Because the actual hardware sensor is currently unavailable, we are simulating sensor output by reading from test dataset CSV files. As a result, hardware-specific pre-processing steps (such as rejecting invalid UART frames and verifying CRC checksums) are omitted from this phase. 

Instead, this document details how the raw CSV data is programmatically pre-processed and converted into clean datasets ready for filtering and anomaly detection.

---

## 1. Data Parsing and Cleaning

The pre-processing pipeline (primarily executed via `preprocess_and_check.py`) takes raw CSV outputs and standardizes them:

### A. Timestamp Standardization
- **Process:** The raw time strings are parsed into Python `datetime` objects.
- **Output:** Timestamps are standardized into a uniform string format: `DD-MM-YYYY HH:MM`. This ensures consistency when merging datasets recorded at different times or dates.

### B. Water Level Extraction and Unit Conversion
- **Process:** The raw water level is often recorded as a string with mixed units (e.g., "1.23 m" or "1230 mm").
- **Output:** Regular expressions are used to extract the numerical float value. If the string contains the "mm" indicator, the value is automatically divided by 1000 to convert it to meters.

---

## 2. Invalid Data Rejection and Calculation

### A. Distance Calculation (Range Limits)
- **Process:** The water level measured is the actual water level in the channel. The sensor has a maximum installation height/range limit of **4.50 meters** from the bottom. We calculate the distance (from sensor to water surface) for the model.
- **Output:** The distance is calculated using the formula:
  ```python
  Distance = 4.50 - Water Level
  ```
- **Rejection Logic:** By enforcing this formula and bounding it, any water level reading below 0m (resulting in a distance > 4.50m limit) is inherently treated as an empty channel (Distance = 4.50m) or flagged, matching our known maximum range.

### B. Error Code Initialization
- **Process:** The initial training dataset inherently contained error codes. For all other datasets, a new column named `errorcode` is initialized and added programmatically based on the known error codes corresponding to different conditions observed in the training data.
- **Output:** The output is the dataset with the `errorcode` column included, initialized to `0` by default, and then corrected based on different conditions. This column can be later modified when injecting outages or spikes for testing.

---

## 3. Dataset Verification

### A. Output Formatting
- The final processed dataset is pruned to only include the relevant columns: `Time`, `errorcode`, and `Distance` (rounded to 2 decimal places).
- The output is saved to the `data/processed/` directory.

### B. Overlap Checking
- **Process:** To maintain data integrity across multiple recording sessions, the pre-processing script includes a safety check.
- **Output:** It compares the minimum and maximum timestamps of the newly processed data against all other existing files in the `data/processed/` directory. It alerts the user if any time overlap is found, preventing duplicated time-series entries.
