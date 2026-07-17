import pandas as pd
import numpy as np

# This is the processed dataset that has all the required 23 features
DATASET_PATH = r"C:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\data\processed\large_training_dataset.csv"
OUTPUT_PATH = r"C:\Users\sahil\Desktop\ICFOSS\Anomaly Detection\data\processed\stm32_validation_data.csv"

# The exact 23 features the MLP was trained on
feature_cols = [
    "errorcode_norm", "wl_raw_norm",
    "wl_lag_1", "wl_lag_2", "wl_lag_3", "wl_lag_4",
    "wl_lag_5", "wl_lag_6", "wl_lag_7", "wl_lag_8",
    "week_sin", "week_cos",
    "day_sin", "day_cos",
    "half_day_sin", "half_day_cos",
    "quarter_day_sin", "quarter_day_cos",
    "eighth_day_sin", "eighth_day_cos",
    "weekly_bin_norm", "day_of_week",
    "prev_errorcode"
]

print(f"Loading {DATASET_PATH}...")
df = pd.read_csv(DATASET_PATH)

# Extract only the 23 features
X = df[feature_cols].copy()

# Drop any rows that happen to have NaNs or Infs
X = X.replace([np.inf, -np.inf], np.nan)
X = X.dropna()

# Let's take the first 1000 samples for validation to keep it fast
X = X.head(1000)

print(f"Saving validation data with shape {X.shape} to {OUTPUT_PATH}")
# Save without index and without header for STM32Cube.AI
X.to_csv(OUTPUT_PATH, index=False, header=False)
print("Done! Use stm32_validation_data.csv in STM32 Cube AI Studio.")
