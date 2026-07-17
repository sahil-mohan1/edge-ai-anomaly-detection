import numpy as np

# Read the TFLite model file
tflite_model_path = "logistic_regression_model_v2.tflite"
with open(tflite_model_path, "rb") as f:
    model_data = f.read()

# Convert model data to a C array format
hex_array = ', '.join(f'0x{byte:03x}' for byte in model_data)

# Write to model_data.h
with open("model_data.h", "w") as f:
    f.write("#ifndef MODEL_DATA_H\n#define MODEL_DATA_H\n\n")
    f.write("#include <stdint.h>\n\n")
    f.write(f"const unsigned char model_data[] = {{ {hex_array} }};\n\n")
    f.write(f"const unsigned int model_data_len = {len(model_data)};\n\n")
    f.write("#endif // MODEL_DATA_H\n")

print("Conversion completed! model_data.h has been created.")
