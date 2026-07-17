# Anomaly Detection & Correction Pipeline

This project implements a hybrid anomaly detection and correction pipeline using SNARIMAX and Adaptive Random Forest Regressor (ARFR) models to clean water level sensor data.

## Project Structure

The project directory has been organized cleanly into the following structure:

- **`data/`**
  - **`raw/`**: Raw CSV files directly from the sensor (e.g., `-data-12_09_43 - Copy.csv`).
  - **`processed/`**: Generated and processed datasets, including:
    - `combined_data.csv`: Merged sensor and error code records.
    - `normal_data.csv` / `abnormal_data.csv`: Data split by error code status.
    - `filtered_data.csv`: Data filtered using basic rejection rules (ground truth).
    - `corrected_data.csv`: Cleaned output from the SNARIMAX+ARFR pipeline.
- **`docs/`**: PDFs and Markdown reports detailing sensor behavior, analysis, and deliverables.
- **`models/`**: Source code for models, features, config parameters, and saving/loading utilities.
  - `saved/`: Model pickle files and metadata checkpoints.
- **`plots/`**: Output plots from the pipeline and filters.
  - `task5/`: Comparative filter test results (EMA, Hampel, Kalman, etc.).
- **`scripts/`**: Preprocessing, gap analysis, filtering, and plotting helper scripts.
- **`run_pipeline.py`**: The main execution script (pipeline entry point).

## Getting Started

### 1. Combine Raw Datasets
Merge the raw sensor readings and error logs into a combined file:
```bash
python scripts/combine_data.py
```

### 2. Run Gap Analysis
Assess the time gaps and missing records in the merged data:
```bash
python scripts/analyze_gaps.py
```

### 3. Generate Anomaly Plots
Visualize raw readings vs. sensor error codes:
```bash
python scripts/plot_filtered_anomalies.py
```

### 4. Test Different Statistical Filters
Evaluate different filters (Moving Average, Median, EMA, Hampel, Kalman) against the ground truth:
```bash
python scripts/filters/task5_filter_testing.py
```

### 5. Run the Hybrid Pipeline
Execute the full correction pipeline:
```bash
python run_pipeline.py
```
Use `--no-plot` to run headlessly, or `--retrain` to discard saved models and retrain from scratch.
