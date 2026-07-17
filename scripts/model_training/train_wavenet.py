# -*- coding: utf-8 -*-
"""
train_wavenet.py
----------------
Trains the WaveNet water level predictor and exports a Float32 TFLite model.

Architecture summary
━━━━━━━━━━━━━━━━━━━━
Input A  (96, 6)   — [wl_norm, recent_diurnal_norm, day_sin, day_cos, half_day_sin, half_day_cos]
Input B  (1,)      — outage_duration_norm  (0 = normal, 1 = deep outage)

  [1] Input projection : explicit causal Conv1D(12, kernel=1)
  [2–7] Six dilated residual blocks   dilation = [1, 2, 4, 8, 16, 32]
        Each block: gated activation (tanh × sigmoid) + residual + skip collect
        Receptive field after all blocks: 127 steps ≈ 31.75 hours  ✓
  [8] Skip sum → ReLU → Conv1D(12,1,relu) → last-step slice → Dense(1) = wl_ar
  [9] Last input step → Dense(16,relu) → Dense(1)                      = wl_temporal
      (model learns to rely on time channels when wl is corrupted)
 [10] Outage gate (inside model):
        output = wl_temporal + wl_ar × (1 − outage_duration_norm)

Loss: outage-weighted Huber (δ=0.05 in [0,1] space ≈ 0.225 m physical)
       weight = 1 + 2 × odn  →  outage steps weighted up to 3×

Inputs/outputs are normalised to [0, 1]  (divide/multiply by 4.5 m).
No diurnal lookup table.  No hardcoded usage patterns.
Everything is learned from data.

Output: models/saved/water_level_wavenet.tflite  (target ≤ 40 KB)
"""

import os
import numpy as np
import tensorflow as tf
from pathlib import Path
from tensorflow.keras import layers, Model, Input

# ── Config ───────────────────────────────────────────────────────────────────
BASE_DIR     = "c:/Users/sahil/Desktop/ICFOSS/Anomaly Detection"
DATASET_PATH = f"{BASE_DIR}/data/processed/wavenet_dataset.npz"
KERAS_PATH   = f"{BASE_DIR}/models/saved/water_level_wavenet.keras"
TFLITE_PATH  = f"{BASE_DIR}/models/saved/water_level_wavenet.tflite"

WINDOW_SIZE    = 96
N_CHANNELS     = 7
N_FILTERS      = 8
KERNEL_SIZE    = 3
DILATIONS      = [1, 2, 4, 8, 16, 32]
TEMPORAL_UNITS = 16

EPOCHS      = 150
BATCH_SIZE  = 64
PATIENCE    = 25
LR          = 1e-3
HUBER_DELTA = 0.05   # [0,1] space; ≈ 0.225 m physical

# ── Custom Keras layer (avoids Lambda serialisation issues) ───────────────────

@tf.keras.utils.register_keras_serializable(package='wavenet')
class SubtractFromOne(layers.Layer):
    """Returns 1.0 - x.  Used to compute (1 - outage_duration_norm)."""
    def call(self, x):
        return 1.0 - x

    def get_config(self):
        return super().get_config()


@tf.keras.utils.register_keras_serializable(package='wavenet')
class SliceTimeFeatures(layers.Layer):
    """Drops wl_norm (index 0) and returns only the 5 features (diurnal + time) (indices 1-5).
    Used in the temporal head so it is immune to corrupted wl during long outages."""
    def call(self, x):
        return x[:, 1:]

    def get_config(self):
        return super().get_config()





# ── Model ────────────────────────────────────────────────────────────────────

def causal_conv1d(x, filters, kernel_size, dilation_rate, name_prefix):
    """
    Native causal Conv1D — Keras handles the left-side zero-padding internally.
    TFLite supports padding='causal' as a single PAD+CONV2D fused op, which is
    more compact in the flatbuffer than explicit ZeroPadding1D + VALID Conv1D.
    """
    return layers.Conv1D(
        filters, kernel_size,
        dilation_rate=dilation_rate,
        padding='causal',
        use_bias=True,
        name=f'{name_prefix}_conv'
    )(x)


@tf.keras.utils.register_keras_serializable(package='wavenet')
class SliceDiurnalAndWeekday(layers.Layer):
    """Extracts recent_diurnal_norm (index 1) and weekday features (indices 4, 5, 6)."""
    def call(self, x):
        return tf.gather(x, [1, 4, 5, 6], axis=1)

    def get_config(self):
        return super().get_config()


def build_model() -> Model:
    # ── Inputs ────────────────────────────────────────────────────────────────
    seq_in = Input(shape=(WINDOW_SIZE, N_CHANNELS), name='sequence')  # (96, 7)

    # ── Input projection (no dilation, no padding needed for kernel=1) ────────
    x = layers.Conv1D(N_FILTERS, 1, padding='valid',
                      activation='relu', name='input_proj')(seq_in)  # (96, 12)

    # ── Six dilated residual blocks ───────────────────────────────────────────
    skip_outputs = []
    for i, d in enumerate(DILATIONS):
        # Gated activation: tanh × sigmoid
        x_t = causal_conv1d(x, N_FILTERS, KERNEL_SIZE, d, f'gate_t_{i}')
        x_t = layers.Activation('tanh',    name=f'tanh_{i}')(x_t)

        x_s = causal_conv1d(x, N_FILTERS, KERNEL_SIZE, d, f'gate_s_{i}')
        x_s = layers.Activation('sigmoid', name=f'sigmoid_{i}')(x_s)

        gated = layers.Multiply(name=f'gated_{i}')([x_t, x_s])  # (96, 12)
        # Residual: add gated back to input
        x = layers.Add(name=f'residual_{i}')([x, gated])          # (96, 8)

        # Skip connection for final aggregation
        skip = layers.Conv1D(N_FILTERS, 1, name=f'skip_proj_{i}')(gated)
        skip_outputs.append(skip)
    # ── Skip aggregation → Output ────────────────────────────────────────────
    skip_sum = layers.Add(name='skip_sum')(skip_outputs)                    # (96, 8)
    skip_sum = layers.Activation('relu',    name='skip_relu')(skip_sum)
    skip_sum = layers.Conv1D(N_FILTERS, 1, activation='relu',
                             name='skip_agg')(skip_sum)                     # (96, 8)

    # Slice only the last time step for temporal profile extraction
    last_input = layers.Cropping1D(cropping=(WINDOW_SIZE - 1, 0),
                                   name='last_input_crop')(seq_in)          # (1, 7)
    last_input_flat = layers.Reshape((N_CHANNELS,),
                                     name='last_input_flat')(last_input)    # (7,)
    
    # Extract the rolling diurnal profile (1) and weekday features (4,5,6)
    temporal_profile = SliceDiurnalAndWeekday(name='diurnal_and_week')(last_input_flat)  # (4,)

    # ── AR Context ───────────────────────────────────────────────────────────
    # The last time step of the causal skip_sum contains the full receptive field.
    last_step = layers.Cropping1D(cropping=(WINDOW_SIZE - 1, 0),
                                  name='last_step_crop')(skip_sum)          # (1, 8)
    ar_context = layers.Flatten(name='ar_context_flat')(last_step)          # (8,)
    ar_context = layers.Dropout(0.5, name='ar_dropout')(ar_context)

    # ── Fusion ───────────────────────────────────────────────────────────────
    fused = layers.Concatenate(name='fusion')([ar_context, temporal_profile]) # (12,)
    
    output = layers.Dense(1, name='output')(fused)                          # (1,)

    return Model(inputs=seq_in, outputs=output, name='WaterLevelWaveNet')


# ── Loss ─────────────────────────────────────────────────────────────────────

@tf.function
def huber_loss(y_true, y_pred, delta=HUBER_DELTA):
    err = y_true - y_pred
    abs_err = tf.abs(err)
    return tf.where(abs_err <= delta,
                    0.5 * tf.square(err),
                    delta * (abs_err - 0.5 * delta))


# ── Training loop ─────────────────────────────────────────────────────────────

def train(model, tr_tensors, va_tensors, optimizer):
    Xs_tr, y_tr, m_tr = tr_tensors
    Xs_va, y_va, m_va = va_tensors

    @tf.function
    def train_step(xs, y, m):
        with tf.GradientTape() as tape:
            pred = model(xs, training=True)
            raw_huber  = huber_loss(y, pred)
            
            # Extract diurnal profile (last timestep, channel index 1)
            diurnal = xs[:, -1, 1:2]
            
            # Pattern loss: penalize under-predicting the diurnal pattern
            pattern_loss = tf.square(tf.maximum(0.0, diurnal - pred))
            
            # Combine losses to prioritize the diurnal pattern
            raw = raw_huber + 1.0 * pattern_loss
            
            loss = tf.reduce_sum(raw * m) / (tf.reduce_sum(m) + 1e-8)
        grads = tape.gradient(loss, model.trainable_variables)
        optimizer.apply_gradients(zip(grads, model.trainable_variables))
        return loss

    @tf.function
    def val_step(xs, y, m):
        pred = model(xs, training=False)
        raw  = huber_loss(y, pred)
        return tf.reduce_sum(raw * m) / (tf.reduce_sum(m) + 1e-8)

    n_tr      = int(Xs_tr.shape[0])
    n_batches = max(1, n_tr // BATCH_SIZE)
    best_val  = float('inf')
    patience  = 0
    best_epoch = 0

    print(f"\n{'Epoch':>5}  {'Train Loss':>10}  {'Val Loss':>9}  {'Patience':>8}")
    print("-" * 45)

    for epoch in range(EPOCHS):
        idx  = tf.random.shuffle(tf.range(n_tr))
        Xs_s = tf.gather(Xs_tr, idx)
        y_s  = tf.gather(y_tr,  idx)
        m_s  = tf.gather(m_tr,  idx)

        total = 0.0
        for b in range(n_batches):
            s = b * BATCH_SIZE
            e = s + BATCH_SIZE
            total += float(train_step(Xs_s[s:e], y_s[s:e], m_s[s:e]))
        tr_loss = total / n_batches

        vl_loss = float(val_step(Xs_va, y_va, m_va))

        if vl_loss < best_val:
            best_val   = vl_loss
            patience   = 0
            best_epoch = epoch + 1
            model.save(KERAS_PATH)
        else:
            patience += 1

        if (epoch + 1) % 10 == 0 or epoch == 0 or patience >= PATIENCE:
            print(f"{epoch+1:>5}  {tr_loss:>10.5f}  {vl_loss:>9.5f}  {patience}/{PATIENCE}")

        if patience >= PATIENCE:
            print("Early stopping triggered.")
            break

    print(f"\nBest val loss: {best_val:.5f}  (epoch {best_epoch})")
    return best_val


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  WaveNet Water Level Predictor -- Training")
    print("=" * 60)

    # ── Load dataset ─────────────────────────────────────────────────────────
    print(f"\nLoading dataset: {DATASET_PATH}")
    if not Path(DATASET_PATH).exists():
        raise FileNotFoundError(
            f"Dataset not found. Run build_wavenet_dataset.py first.\n  {DATASET_PATH}")

    data   = np.load(DATASET_PATH)
    X_seq  = data['X_seq'].astype(np.float32)
    y      = data['y'].astype(np.float32)[:, None]
    y_mask = data['y_mask'].astype(np.float32)[:, None]

    N = len(X_seq)
    idx   = np.random.permutation(N)
    split = int(0.8 * N)
    tr_idx, va_idx = idx[:split], idx[split:]

    y_tr      = y[tr_idx]
    mask_tr   = y_mask[tr_idx]

    tr_tensors = (tf.constant(X_seq[tr_idx]),
                  tf.constant(y_tr, dtype=tf.float32),
                  tf.constant(mask_tr, dtype=tf.float32))

    va_tensors = (tf.constant(X_seq[va_idx]),
                  tf.constant(y[va_idx], dtype=tf.float32),
                  tf.constant(y_mask[va_idx], dtype=tf.float32))



    # ── Build model ──────────────────────────────────────────────────────────
    model = build_model()
    model.summary()

    n_params = model.count_params()
    print(f"\nTotal parameters   : {n_params:,}")
    print(f"Est. float32 size  : {n_params * 4 / 1024:.1f} KB")

    optimizer = tf.keras.optimizers.Adam(learning_rate=LR)

    # ── Train ────────────────────────────────────────────────────────────────
    Path(KERAS_PATH).parent.mkdir(parents=True, exist_ok=True)
    train(model, tr_tensors, va_tensors, optimizer)

    # ── Load best & export TFLite ─────────────────────────────────────────────
    print("\nLoading best weights...")
    model = tf.keras.models.load_model(
        KERAS_PATH,
        custom_objects={'SubtractFromOne': SubtractFromOne,
                        'SliceTimeFeatures': SliceTimeFeatures,
                        'SliceDiurnalAndWeekday': SliceDiurnalAndWeekday},
        safe_mode=False)   # safe_mode=False needed for any Lambda in older saves

    print("Exporting Float32 TFLite (no quantisation)...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_bytes = converter.convert()

    Path(TFLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(TFLITE_PATH, 'wb') as f:
        f.write(tflite_bytes)

    size_kb = len(tflite_bytes) / 1024
    print(f"\n  Saved    -> {TFLITE_PATH}")
    print(f"  TFLite size : {len(tflite_bytes):,} bytes  ({size_kb:.1f} KB)")
    if len(tflite_bytes) > 40_000:
        print("  !  WARNING: Exceeds 40 KB target - consider reducing N_FILTERS.")
    else:
        print("  OK  Within 40 KB budget.")

    # ── Quick sanity check ────────────────────────────────────────────────────
    print("\nRunning TFLite sanity check...")
    interp = tf.lite.Interpreter(model_path=TFLITE_PATH)
    interp.allocate_tensors()
    inp_details = interp.get_input_details()
    out_details = interp.get_output_details()

    print("  Input tensors:")
    for d in inp_details:
        print(f"    [{d['index']}] {d['name']}  shape={d['shape']}  dtype={d['dtype']}")
    print("  Output tensor:")
    for d in out_details:
        print(f"    [{d['index']}] {d['name']}  shape={d['shape']}  dtype={d['dtype']}")

    # Feed a random sample
    sample_seq = X_seq[0:1].astype(np.float32)
    for d in inp_details:
        if list(d['shape']) == [1, WINDOW_SIZE, N_CHANNELS]:
            interp.set_tensor(d['index'], sample_seq)

    interp.invoke()
    pred_norm = float(interp.get_tensor(out_details[0]['index'])[0, 0])
    print(f"  Sample prediction (normalised) : {pred_norm:.4f}  "
          f"({pred_norm * 4.5:.3f} m)")

    print("\nDone!")


if __name__ == '__main__':
    main()
