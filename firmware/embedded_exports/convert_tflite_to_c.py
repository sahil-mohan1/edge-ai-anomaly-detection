import os

def convert_to_c_array(input_path, output_path, array_name):
    with open(input_path, 'rb') as f:
        data = f.read()

    with open(output_path, 'w') as f:
        f.write('#ifndef CNN_MODEL_DATA_H\n')
        f.write('#define CNN_MODEL_DATA_H\n\n')
        f.write(f'// Model size: {len(data)} bytes\n')
        f.write(f'alignas(8) const unsigned char {array_name}[] = {{\n')

        for i, byte in enumerate(data):
            f.write(f'0x{byte:02x}, ')
            if (i + 1) % 12 == 0:
                f.write('\n')

        f.write('\n};\n')
        f.write(f'const int {array_name}_len = {len(data)};\n\n')
        f.write('#endif // CNN_MODEL_DATA_H\n')

if __name__ == '__main__':
    convert_to_c_array('models/saved/water_level_cnn.tflite', 'scripts/cnn_model_data.h', 'g_cnn_model_data')
    print("Converted to scripts/cnn_model_data.h")
