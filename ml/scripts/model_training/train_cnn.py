import os
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Flatten, Dense
import matplotlib.pyplot as plt

# Configuration
DATA_PATH = 'data/processed/combined_data.csv'
MODEL_SAVE_PATH_KERAS = 'models/saved/water_level_cnn.keras'
MODEL_SAVE_PATH_TFLITE = 'models/saved/water_level_cnn.tflite'
WINDOW_SIZE = 12  # Number of past readings to look at (e.g., 1 hour if 5-min intervals)

def create_dataset(data, window_size):
    X, y = [], []
    for i in range(len(data) - window_size):
        X.append(data[i:(i + window_size)])
        y.append(data[i + window_size])
    return np.array(X), np.array(y)

def main():
    print("Loading data...")
    df = pd.read_csv(DATA_PATH)
    
    # We will use 'Water Level' as the primary feature
    # For a real system, you might want to filter out anomalies (errorcode != 0) before training
    # to ensure the model learns normal behavior. For simplicity, we use the raw data here.
    # A better approach: interpolate over anomalies for the training set.
    
    # Simple preprocessing: If errorcode > 0, interpolate
    df_train = df.copy()
    df_train.loc[df_train['errorcode'] > 0, 'Water Level'] = np.nan
    df_train['Water Level'] = df_train['Water Level'].interpolate(method='linear').bfill().ffill()
    
    values = df_train['Water Level'].values
    
    print("Preparing sliding window dataset...")
    X, y = create_dataset(values, WINDOW_SIZE)
    
    # Reshape X for Conv1D: (samples, time steps, features)
    X = X.reshape((X.shape[0], X.shape[1], 1))
    
    # Split into train and test
    split = int(0.8 * len(X))
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    
    print(f"Train shapes: X={X_train.shape}, y={y_train.shape}")
    print(f"Test shapes: X={X_test.shape}, y={y_test.shape}")
    
    # Build 1D-CNN Model
    print("Building model...")
    model = Sequential([
        Conv1D(filters=16, kernel_size=3, activation='relu', input_shape=(WINDOW_SIZE, 1)),
        MaxPooling1D(pool_size=2),
        Flatten(),
        Dense(8, activation='relu'),
        Dense(1) # Linear output for regression
    ])
    
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    model.summary()
    
    print("Training model...")
    history = model.fit(X_train, y_train, epochs=20, batch_size=32, validation_split=0.1, verbose=1)
    
    print("Evaluating model...")
    loss, mae = model.evaluate(X_test, y_test, verbose=0)
    print(f"Test Loss (MSE): {loss:.4f}, Test MAE: {mae:.4f}")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(MODEL_SAVE_PATH_KERAS), exist_ok=True)
    
    print(f"Saving Keras model to {MODEL_SAVE_PATH_KERAS}")
    model.save(MODEL_SAVE_PATH_KERAS)
    
    print("Converting to TFLite (with post-training quantization)...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    
    # Enable basic quantization to reduce size and improve speed on STM32
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    
    # Provide a representative dataset to allow full integer quantization
    def representative_data_gen():
        # Sample uniformly across the entire training set to get the full min/max range for INT8 scaling
        indices = np.random.choice(len(X_train), size=500, replace=False)
        for i in indices:
            yield [X_train[i:i+1].astype(np.float32)]

    converter.representative_dataset = representative_data_gen
    # Ensure ops are supported by TFLite Micro
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8
    
    try:
        tflite_model = converter.convert()
        with open(MODEL_SAVE_PATH_TFLITE, 'wb') as f:
            f.write(tflite_model)
        print(f"Saved TFLite model to {MODEL_SAVE_PATH_TFLITE}")
        print(f"TFLite model size: {len(tflite_model)} bytes")
    except Exception as e:
        print(f"Quantization failed, falling back to unquantized TFLite. Error: {e}")
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        tflite_model = converter.convert()
        with open(MODEL_SAVE_PATH_TFLITE, 'wb') as f:
            f.write(tflite_model)
        print(f"Saved unquantized TFLite model to {MODEL_SAVE_PATH_TFLITE}")
        print(f"TFLite model size: {len(tflite_model)} bytes")
    
    # Optional: Plot some predictions to verify it doesn't have "sharp jumps"
    # Select a slice of the test data
    y_pred = model.predict(X_test)
    
    plt.figure(figsize=(12, 6))
    plt.plot(y_test[:300], label='Actual', alpha=0.7)
    plt.plot(y_pred[:300], label='1D-CNN Predicted', alpha=0.7)
    plt.title('1D-CNN Forecast vs Actual')
    plt.xlabel('Time Step')
    plt.ylabel('Water Level')
    plt.legend()
    plot_path = 'plots/cnn_predictions.png'
    os.makedirs('plots', exist_ok=True)
    plt.savefig(plot_path)
    print(f"Saved prediction plot to {plot_path}")

if __name__ == "__main__":
    main()
