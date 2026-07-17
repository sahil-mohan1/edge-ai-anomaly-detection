"""
train_large_mlp.py
------------------
Trains a larger AR-MLP (Float32) using the expanded dataset.
Now using Multi-Step Autoregressive Training (Scheduled Sampling)
to fix inference drift during outages.
"""

import os
import random

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
import tensorflow as tf

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATASET_PATH = "c:/Users/sahil/Desktop/ICFOSS/Anomaly Detection/data/processed/large_training_dataset.csv"
MODEL_SAVE_PATH = "c:/Users/sahil/Desktop/ICFOSS/Anomaly Detection/models/saved/large_ar_mlp.keras"
TFLITE_SAVE_PATH = "c:/Users/sahil/Desktop/ICFOSS/Anomaly Detection/models/saved/large_ar_mlp.tflite"

N_FEATURES = 23
HIDDEN1 = 64
HIDDEN2 = 32
HIDDEN3 = 16

EPOCHS = 100
BATCH_SIZE = 64
PATIENCE = 15
SEQ_LEN = 16  # Multi-step training horizon (4 hours at 15-min intervals)

# ---------------------------------------------------------------------------
# Data Loading & Sequence Extraction
# ---------------------------------------------------------------------------
def load_and_split_data(path: str, seq_len: int = 1, test_size: float = 0.2):
    df = pd.read_csv(path)
    # Define the 23 features in exact order
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

    split_idx = int(len(df) * (1 - test_size))
    df_train = df.iloc[:split_idx]
    df_val = df.iloc[split_idx:]

    def make_sequences(df_subset):
        X_raw = df_subset[feature_cols].values.astype(np.float32)
        y_cls_raw = df_subset["is_anomaly"].values.astype(np.float32)
        y_reg_raw = df_subset["wl_clean"].values.astype(np.float32)
        
        n_samples = len(X_raw) - seq_len + 1
        
        X_seq = np.zeros((n_samples, seq_len, N_FEATURES), dtype=np.float32)
        y_cls_seq = np.zeros((n_samples, seq_len), dtype=np.float32)
        y_reg_seq = np.zeros((n_samples, seq_len), dtype=np.float32)
        
        for i in range(n_samples):
            X_seq[i] = X_raw[i : i + seq_len]
            y_cls_seq[i] = y_cls_raw[i : i + seq_len]
            y_reg_seq[i] = y_reg_raw[i : i + seq_len]
            
        reg_mask_seq = (~np.isnan(y_reg_seq)).astype(np.float32)
        return X_seq, y_cls_seq, y_reg_seq, reg_mask_seq

    X_train, y_cls_train, y_reg_train, reg_mask_train = make_sequences(df_train)
    X_val, y_cls_val, y_reg_val, reg_mask_val = make_sequences(df_val)

    return X_train, X_val, y_cls_train, y_cls_val, y_reg_train, y_reg_val, reg_mask_train, reg_mask_val

# ---------------------------------------------------------------------------
# Model Architecture
# ---------------------------------------------------------------------------
def build_model(input_dim: int):
    inputs = tf.keras.Input(shape=(input_dim,), name="features")

    # Classification branch (uses all features)
    x_cls = tf.keras.layers.Dense(HIDDEN1, activation="relu", name="hidden1_cls")(inputs)
    x_cls = tf.keras.layers.Dense(HIDDEN2, activation="relu", name="hidden2_cls")(x_cls)
    anomaly_out = tf.keras.layers.Dense(1, activation="sigmoid", name="anomaly")(x_cls)

    # Regression branch (uses only lags and time features, indices 2:)
    reg_inputs = inputs[:, 2:]
    x_reg = tf.keras.layers.Dense(HIDDEN1, activation="relu", name="hidden1_reg")(reg_inputs)
    x_reg = tf.keras.layers.Dense(HIDDEN2, activation="relu", name="hidden2_reg")(x_reg)
    x_reg = tf.keras.layers.Dense(HIDDEN3, activation="relu", name="hidden3_reg")(x_reg)
    wl_out = tf.keras.layers.Dense(1, activation="linear", name="wl")(x_reg)

    output = tf.keras.layers.Concatenate(name="output")([anomaly_out, wl_out])
    model = tf.keras.Model(inputs=inputs, outputs=output, name="Large_AR_MLP")
    return model

# ---------------------------------------------------------------------------
# Training Loop
# ---------------------------------------------------------------------------
def train(model, X_train, y_cls_train, y_reg_train, reg_mask_train,
          X_val, y_cls_val, y_reg_val, reg_mask_val,
          epochs: int, batch_size: int, pos_weight: float = 1.0):
    optimizer = tf.keras.optimizers.Adam(learning_rate=1e-3)

    def weighted_bce(y_true, y_pred, pos_w):
        eps = 1e-7
        loss = -(pos_w * y_true * tf.math.log(y_pred + eps)
                 + (1.0 - y_true) * tf.math.log(1.0 - y_pred + eps))
        return tf.reduce_mean(loss)

    @tf.function
    def train_step(xb_seq, ycb_seq, yrb_seq, rmb_seq):
        T = SEQ_LEN
        current_lags = xb_seq[:, 0, 2:10] # Initial lags
        
        loss = 0.0
        with tf.GradientTape() as tape:
            for t in range(T):
                feat_t = xb_seq[:, t, :]
                
                # Overwrite true lags with autoregressive predictions
                feat_t_new = tf.concat([
                    feat_t[:, :2],       # errorcode, wl_raw
                    current_lags,        # 8 predicted lags
                    feat_t[:, 10:]       # time features
                ], axis=1)
                
                pred = model(feat_t_new, training=True)
                ap, wp = pred[:, :1], pred[:, 1:]
                
                yc = ycb_seq[:, t:t+1]
                yr = yrb_seq[:, t:t+1]
                rm = rmb_seq[:, t:t+1]
                
                cls_loss = weighted_bce(yc, ap, pos_weight)
                yr_safe  = tf.where(tf.math.is_nan(yr), tf.zeros_like(yr), yr)
                sq_err   = tf.square(yr_safe - wp) * rm
                reg_loss = tf.reduce_sum(sq_err) / (tf.reduce_sum(rm) + 1e-8)
                
                loss += (0.5 * cls_loss + 0.5 * reg_loss)
                
                # Shift lags for next step
                current_lags = tf.concat([wp, current_lags[:, :-1]], axis=1)
                
            loss = loss / tf.cast(T, tf.float32)
            
        grads = tape.gradient(loss, model.trainable_variables)
        optimizer.apply_gradients(zip(grads, model.trainable_variables))
        return loss

    @tf.function
    def val_step(xb_seq, ycb_seq, yrb_seq, rmb_seq):
        T = SEQ_LEN
        current_lags = xb_seq[:, 0, 2:10]
        loss = 0.0
        for t in range(T):
            feat_t = xb_seq[:, t, :]
            feat_t_new = tf.concat([
                feat_t[:, :2],
                current_lags,
                feat_t[:, 10:]
            ], axis=1)
            
            pred = model(feat_t_new, training=False)
            ap, wp = pred[:, :1], pred[:, 1:]
            
            yc = ycb_seq[:, t:t+1]
            yr = yrb_seq[:, t:t+1]
            rm = rmb_seq[:, t:t+1]
            
            cls_loss = weighted_bce(yc, ap, pos_weight)
            yr_safe  = tf.where(tf.math.is_nan(yr), tf.zeros_like(yr), yr)
            sq_err   = tf.square(yr_safe - wp) * rm
            reg_loss = tf.reduce_sum(sq_err) / (tf.reduce_sum(rm) + 1e-8)
            
            loss += (0.5 * cls_loss + 0.5 * reg_loss)
            current_lags = tf.concat([wp, current_lags[:, :-1]], axis=1)
            
        loss = loss / tf.cast(T, tf.float32)
        return loss

    yr_tr_safe = np.nan_to_num(y_reg_train, nan=0.0)
    yr_v_safe  = np.nan_to_num(y_reg_val,   nan=0.0)

    X_tr  = tf.constant(X_train)
    yc_tr = tf.constant(y_cls_train)
    yr_tr = tf.constant(yr_tr_safe)
    rm_tr = tf.constant(reg_mask_train, dtype=tf.float32)

    X_v   = tf.constant(X_val)
    yc_v  = tf.constant(y_cls_val)
    yr_v  = tf.constant(yr_v_safe)
    rm_v  = tf.constant(reg_mask_val, dtype=tf.float32)

    n_batches = max(1, len(X_train) // batch_size)
    best_val_loss = float("inf")
    patience_cnt = 0

    print("Epoch | Train Loss | Val Loss  | EarlyStop")
    print("-" * 45)

    for epoch in range(epochs):
        idx = tf.random.shuffle(tf.range(len(X_train)))
        X_tr_s = tf.gather(X_tr, idx)
        yc_tr_s = tf.gather(yc_tr, idx)
        yr_tr_s = tf.gather(yr_tr, idx)
        rm_tr_s = tf.gather(rm_tr, idx)

        total_loss = 0.0
        for i in range(n_batches):
            start = i * batch_size
            end   = start + batch_size
            xb = X_tr_s[start:end]
            ycb = yc_tr_s[start:end]
            yrb = yr_tr_s[start:end]
            rmb = rm_tr_s[start:end]
            total_loss += train_step(xb, ycb, yrb, rmb)

        train_loss = total_loss / n_batches

        # Validation pass
        # Since validation set might be large, we'll batch the validation too to prevent OOM
        v_batches = max(1, len(X_val) // batch_size)
        v_total_loss = 0.0
        for i in range(v_batches):
            start = i * batch_size
            end   = start + batch_size
            xb = X_v[start:end]
            ycb = yc_v[start:end]
            yrb = yr_v[start:end]
            rmb = rm_v[start:end]
            v_total_loss += val_step(xb, ycb, yrb, rmb)
        
        val_loss = v_total_loss / v_batches

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_cnt = 0
            model.save(MODEL_SAVE_PATH)
        else:
            patience_cnt += 1

        if (epoch + 1) % 5 == 0 or epoch == 0 or patience_cnt >= PATIENCE:
            print(f"{epoch+1:>5} | {train_loss:>10.4f} | {val_loss:>9.4f} | {patience_cnt}/{PATIENCE}")

        if patience_cnt >= PATIENCE:
            print("Early stopping triggered.")
            break

    # Load best model
    if os.path.exists(MODEL_SAVE_PATH):
        model.load_weights(MODEL_SAVE_PATH)

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def export_tflite_float32(model, tflite_path: str):
    print("\nConverting to Float32 TFLite (No quantization)...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()
    with open(tflite_path, "wb") as f:
        f.write(tflite_model)
    print(f"Saved Float32 TFLite model -> {tflite_path} ({len(tflite_model)} bytes)")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("  Training Large AR-MLP with Multi-Step Training")
    print("=" * 60)

    X_train, X_val, y_cls_train, y_cls_val, y_reg_train, y_reg_val, reg_mask_train, reg_mask_val = load_and_split_data(
        DATASET_PATH, seq_len=SEQ_LEN, test_size=0.2
    )

    # Compute pos_weight based on the first step of the sequences
    pos_w = (len(y_cls_train) - np.sum(y_cls_train[:, 0])) / (np.sum(y_cls_train[:, 0]) + 1e-5)
    
    model = build_model(N_FEATURES)
    model.summary()
    
    os.makedirs(os.path.dirname(MODEL_SAVE_PATH), exist_ok=True)
    
    train(model, X_train, y_cls_train, y_reg_train, reg_mask_train,
          X_val, y_cls_val, y_reg_val, reg_mask_val,
          epochs=EPOCHS, batch_size=BATCH_SIZE, pos_weight=pos_w)
          
    export_tflite_float32(model, TFLITE_SAVE_PATH)
    print("Done!")

if __name__ == "__main__":
    main()
