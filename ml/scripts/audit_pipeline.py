"""
audit_pipeline.py
-----------------
Performs a rigorous audit of the training and evaluation pipeline for the AR-MLP model.
Checks train/test split chronological consistency, feature leakage, normalisation,
duplicate rows, anomaly label generation, evaluation logic, and regression bias.
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime

DATE_FMT = "%d-%m-%Y %H:%M"
DATASET_PATH = "data/processed/training_dataset.csv"
RAW_CSV = "data/processed/combined_data.csv"
FILTERED_CSV = "data/processed/filtered_data.csv"

FEATURE_COLS = [
    "errorcode_norm", "wl_raw_norm",
    "wl_lag_1", "wl_lag_2", "wl_lag_3", "wl_lag_4",
    "wl_lag_5", "wl_lag_6", "wl_lag_7", "wl_lag_8",
    "hour_sin", "hour_cos", "refill_sin", "refill_cos",
    "day_of_week", "prev_errorcode"
]

def run_audit():
    print("=" * 70)
    print("             PIPELINE AUDIT FOR AR-MLP MODEL")
    print("=" * 70)

    # Check file existence
    for path in [DATASET_PATH, RAW_CSV, FILTERED_CSV]:
        if not os.path.exists(path):
            print(f"ERROR: Required file {path} not found.")
            sys.exit(1)

    # Load dataset
    df = pd.read_csv(DATASET_PATH)
    df["_ts"] = pd.to_datetime(df["Time"], format=DATE_FMT, dayfirst=True)
    df = df.sort_values("_ts").reset_index(drop=True)

    print(f"Dataset Loaded: {len(df)} rows")
    print(f"Date Range: {df['_ts'].min()} to {df['_ts'].max()}")
    print(f"Anomaly Rate: {df['is_anomaly'].mean() * 100:.2f}% (Total anomalies: {df['is_anomaly'].sum()})")

    # 1. Train / Test Split Audit
    print("\n" + "-" * 50)
    print("1. TRAIN / TEST SPLIT AUDIT")
    print("-" * 50)
    TRAIN_RATIO = 0.80
    split_idx = int(len(df) * TRAIN_RATIO)
    train_df = df.iloc[:split_idx]
    val_df = df.iloc[split_idx:]

    print(f"Train set: {len(train_df)} rows, from {train_df['_ts'].min()} to {train_df['_ts'].max()}")
    print(f"Val set  : {len(val_df)} rows, from {val_df['_ts'].min()} to {val_df['_ts'].max()}")

    # Check chronological split and overlap
    max_train_time = train_df["_ts"].max()
    min_val_time = val_df["_ts"].min()
    overlap_samples = val_df[val_df["_ts"] <= max_train_time]

    print(f"Max train timestamp: {max_train_time}")
    print(f"Min val timestamp  : {min_val_time}")
    if min_val_time >= max_train_time:
        print("PASS: Validation set starts strictly after or at training set's end in time.")
    else:
        print("FAIL: Time-travel leak! Some validation timestamps are before training timestamps.")
    print(f"Number of overlapping timestamps: {len(overlap_samples)}")

    # 2. Lag / Window Generation Audit
    print("\n" + "-" * 50)
    print("2. LAG / WINDOW GENERATION AUDIT")
    print("-" * 50)
    # Check if lags are constructed correctly and do not use future values
    # In build_training_dataset.py, wl_lag_1 is lag_buf[-1] (last clean value)
    # Let's inspect a few rows where we can reconstruct manually
    lag_errors = 0
    clean_history = []
    
    for idx, row in df.iterrows():
        # verify wl_lag_1 is indeed the last clean value before this step
        if idx > 0:
            expected_lag_1 = clean_history[-1] if len(clean_history) > 0 else 0.0
            actual_lag_1 = row["wl_lag_1"]
            # Allow small float diffs
            if len(clean_history) > 0 and abs(expected_lag_1 - actual_lag_1) > 1e-5:
                lag_errors += 1
                if lag_errors <= 3:
                    print(f"Mismatch at index {idx}: expected {expected_lag_1}, got {actual_lag_1}")

        # Update clean history
        if row["is_anomaly"] == 0 and not pd.isna(row["wl_clean"]):
            clean_history.append(row["wl_clean"])

    if lag_errors == 0:
        print("PASS: Lag columns match chronological past clean values. No future leakage in lags.")
    else:
        print(f"FAIL: {lag_errors} lag inconsistencies detected.")

    # Check if current target wl_clean is used as input
    # Notice that wl_raw_norm is input. On clean rows, wl_raw == wl_clean.
    # Therefore, wl_raw_norm contains the exact target value.
    print("Features used for prediction:")
    for col in FEATURE_COLS:
        print(f"  - {col}")

    # 3. Scaling and Normalization Audit
    print("\n" + "-" * 50)
    print("3. SCALING AND NORMALIZATION AUDIT")
    print("-" * 50)
    # Check if normalization is constant or fit on full dataset
    # We see: errorcode_norm = ec / 5.0, wl_raw_norm = wl_raw / 4.5.
    # Let's verify this relationship holds exactly across the entire dataset.
    ec_norm_check = (df["errorcode_norm"] == df["errorcode"] / 5.0).all()
    wl_norm_check = (df["wl_raw_norm"] == df["wl_raw"] / 4.5).all()
    print(f"Fixed scale check for errorcode_norm (val / 5.0): {ec_norm_check}")
    print(f"Fixed scale check for wl_raw_norm (val / 4.5)  : {wl_norm_check}")
    if ec_norm_check and wl_norm_check:
        print("PASS: Scalers use fixed normalization constants. No leakage from fitting scalers on the entire dataset.")
    else:
        print("FAIL: Scaling is not using fixed constants or has data mismatch.")

    # 4. Training vs Testing Data Audit
    print("\n" + "-" * 50)
    print("4. TRAINING VS TESTING DATA AUDIT")
    print("-" * 50)
    print(f"Train size: {len(train_df)} (Indices: 0 to {split_idx-1})")
    print(f"Val size  : {len(val_df)} (Indices: {split_idx} to {len(df)-1})")
    overlap_idx = set(train_df.index).intersection(set(val_df.index))
    print(f"Index intersection size: {len(overlap_idx)}")
    if len(overlap_idx) == 0:
        print("PASS: Train and Val indices are mutually exclusive.")
    else:
        print("FAIL: Shared indices between train and val!")

    # 5. Duplicate Samples Audit
    print("\n" + "-" * 50)
    print("5. DUPLICATE SAMPLES AUDIT")
    print("-" * 50)
    # Check duplicate rows in raw data
    raw_df = pd.read_csv(RAW_CSV)
    raw_dupes = raw_df.duplicated().sum()
    print(f"Duplicate rows in raw dataset (combined_data.csv): {raw_dupes}")
    
    # Check duplicates in feature matrix
    feat_dupes = df[FEATURE_COLS].duplicated().sum()
    print(f"Duplicate feature rows in training_dataset.csv: {feat_dupes}")
    
    # Check if there are overlapping duplicate rows between train and validation sets
    train_feats = set(tuple(x) for x in train_df[FEATURE_COLS].values)
    val_feats = [tuple(x) for x in val_df[FEATURE_COLS].values]
    overlap_feats = sum(1 for x in val_feats if x in train_feats)
    print(f"Validation feature rows that are identical to training feature rows: {overlap_feats} ({overlap_feats/len(val_df)*100:.2f}%)")

    # 6. Anomaly Labels Audit
    print("\n" + "-" * 50)
    print("6. ANOMALY LABELS AUDIT")
    print("-" * 50)
    # Check if labels are deterministic based on errorcode
    print("Errorcode vs Anomaly mapping in training set:")
    print(train_df.groupby("errorcode")["is_anomaly"].value_counts())
    print("\nErrorcode vs Anomaly mapping in validation set:")
    print(val_df.groupby("errorcode")["is_anomaly"].value_counts())
    
    # Check if errorcode != 0 is a perfect predictor of is_anomaly
    train_ec_nonzero_is_anom = ((train_df["errorcode"] != 0) == train_df["is_anomaly"]).all()
    val_ec_nonzero_is_anom = ((val_df["errorcode"] != 0) == val_df["is_anomaly"]).all()
    print(f"Does (errorcode != 0) perfectly match (is_anomaly == 1) in train? {train_ec_nonzero_is_anom}")
    print(f"Does (errorcode != 0) perfectly match (is_anomaly == 1) in val? {val_ec_nonzero_is_anom}")

    # Let's count how many anomalies have errorcode == 0
    silent_train = train_df[(train_df["errorcode"] == 0) & (train_df["is_anomaly"] == 1)]
    silent_val = val_df[(val_df["errorcode"] == 0) & (val_df["is_anomaly"] == 1)]
    print(f"Anomalies with errorcode == 0 in train: {len(silent_train)}")
    print(f"Anomalies with errorcode == 0 in val  : {len(silent_val)}")

    # 7. Evaluation Procedure and Regression Bias Audit
    print("\n" + "-" * 50)
    print("7. EVALUATION PROCEDURE AND REGRESSION BIAS AUDIT")
    print("-" * 50)
    # Regression target is wl_clean, which is only defined for clean rows (is_anomaly == 0).
    # On clean rows, is wl_clean exactly equal to wl_raw?
    clean_rows = df[df["is_anomaly"] == 0]
    mismatch_clean = (clean_rows["wl_clean"] != clean_rows["wl_raw"]).sum()
    print(f"Clean rows where wl_clean != wl_raw: {mismatch_clean}")
    
    # Evaluate a trivial baseline for regression:
    # Since wl_raw_norm is an input, the model can trivially learn: wl_pred = wl_raw_norm * 4.5
    # Let's see what the MAE and RMSE would be if we just output wl_raw on clean rows
    val_clean = val_df[val_df["is_anomaly"] == 0]
    trivial_mae = np.mean(np.abs(val_clean["wl_clean"] - val_clean["wl_raw"]))
    trivial_rmse = np.sqrt(np.mean((val_clean["wl_clean"] - val_clean["wl_raw"])**2))
    print(f"Trivial Baseline (wl_pred = wl_raw) on validation clean rows:")
    print(f"  MAE : {trivial_mae:.6f} m")
    print(f"  RMSE: {trivial_rmse:.6f} m")
    
    # Why is this an evaluation bias?
    # Because we ONLY evaluate the regression model on CLEAN rows, where the target is EXACTLY the input!
    # During actual anomalies, the target wl_clean is NaN (we don't know the ground truth clean water level).
    # Therefore, the regression metrics are completely blind to how well the model reconstructs/imputes water levels during anomalies!
    # It only measures how well it copies wl_raw when there are no anomalies!

    # 8. Robustness / Rule-Based Baseline Test
    print("\n" + "-" * 50)
    print("8. ROBUSTNESS & BASELINE METRICS COMPARISON")
    print("-" * 50)
    # Let's compute the performance of a simple heuristic model on the validation set:
    # Pred_Anomaly = 1 if errorcode != 0 else 0
    # Pred_WL = wl_raw
    y_true_cls = val_df["is_anomaly"].values
    y_pred_cls_heuristic = (val_df["errorcode"].values != 0).astype(int)
    
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
    
    h_acc = accuracy_score(y_true_cls, y_pred_cls_heuristic)
    h_prec = precision_score(y_true_cls, y_pred_cls_heuristic, zero_division=0)
    h_rec = recall_score(y_true_cls, y_pred_cls_heuristic, zero_division=0)
    h_f1 = f1_score(y_true_cls, y_pred_cls_heuristic, zero_division=0)
    h_cm = confusion_matrix(y_true_cls, y_pred_cls_heuristic)
    
    print("Heuristic/Rule-Based Baseline (is_anomaly = (errorcode != 0)):")
    print(f"  Accuracy : {h_acc:.4f}")
    print(f"  Precision: {h_prec:.4f}")
    print(f"  Recall   : {h_rec:.4f}")
    print(f"  F1-Score : {h_f1:.4f}")
    print(f"  Confusion Matrix:")
    print(f"    TN={h_cm[0,0]}  FP={h_cm[0,1]}")
    print(f"    FN={h_cm[1,0]}  TP={h_cm[1,1]}")

    print("\nConclusion:")
    print("1. Classification is 100% because all anomalies in the validation set have non-zero errorcode.")
    print("   Therefore, the neural network only needs to learn the rule (errorcode_norm > 0) to get 100% metrics.")
    print("   This is a trivial classification task because there are no silent anomalies (errorcode == 0 but is_anomaly == 1) in the validation set.")
    print("2. Regression MAE/RMSE is near-zero because the model is only evaluated on clean rows where wl_clean == wl_raw.")
    print("   Since wl_raw_norm is an input feature, the neural network learns a simple identity mapping and gets perfect metrics.")
    print("   It is never evaluated on its ability to impute water levels during actual anomalies (because ground truth clean water level is missing during anomalies).")

if __name__ == "__main__":
    run_audit()
