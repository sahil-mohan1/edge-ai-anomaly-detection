#include <iostream>
#include <iomanip>
#include <fstream>
#include <sstream>
#include <windows.h>
#include "embedded_cnn_corrector.h"

// ============================================================================
// STUB FOR X-CUBE-AI / TFLITE MICRO INFERENCE
// On STM32, replace this stub with your actual ai_network_run() call
// ============================================================================
float run_cnn_inference(const float* input_window) {
    // Basic mock: return the last value in the window as the prediction
    // This allows the C++ state machine to run on PC without compiling TFLite.
    return input_window[11]; 
}
// ============================================================================

struct DataPoint {
    std::string time;
    int errorcode;
    float wl_raw;
};

DataPoint parse_row(const std::string& line) {
    std::stringstream ss(line);
    std::string temp;
    DataPoint dp;

    std::getline(ss, dp.time, ',');
    std::getline(ss, temp, ',');
    dp.errorcode = std::atoi(temp.c_str());
    std::getline(ss, temp, ',');
    dp.wl_raw = std::atof(temp.c_str());
    return dp;
}

int main(int argc, char* argv[]) {
    std::cout << "--- C++ Embedded CNN Anomaly Detector Simulation ---\n";
    std::cout << "Make sure to implement run_cnn_inference() with X-CUBE-AI on your STM32.\n\n";

    std::string filename = "data/processed/data-may26-june18_processed.csv";
    float points_per_sec = 0.0f;

    if (argc > 1) {
        points_per_sec = std::atof(argv[1]);
    }
    if (argc > 2) {
        filename = argv[2];
    }

    if (points_per_sec > 0.0f) {
        std::cout << "Rate: " << points_per_sec << " points/sec\n";
    } else {
        std::cout << "Rate: Max speed\n";
    }
    std::cout << "Dataset: " << filename << "\n\n";

    EmbeddedCNNCorrector corrector;
    // Assume start time is minute 0
    corrector.reset(1.34f, 0);

    std::ifstream file(filename);
    if (!file) {
        std::cerr << "Could not open " << filename << "\n";
        return 1;
    }

    std::string line;
    std::getline(file, line); // header

    int min_counter = 0;
    while (std::getline(file, line)) {
        if (line.empty()) continue;
        DataPoint dp = parse_row(line);
        
        bool is_anomaly = false;
        // Simulate reading every 15 minutes
        float corrected = corrector.process_sample(min_counter, dp.errorcode, dp.wl_raw, is_anomaly);
        
        std::cout << "Min: " << std::setw(5) << min_counter 
                  << " | Raw: " << std::fixed << std::setprecision(2) << std::setw(5) << dp.wl_raw 
                  << " | Err: " << dp.errorcode 
                  << " | Corrected: " << std::setw(5) << corrected 
                  << " | " << (is_anomaly ? "[ANOMALY]" : "NORMAL") << "\n";
        
        if (points_per_sec > 0.0f) {
            int delay_ms = static_cast<int>(1000.0f / points_per_sec);
            Sleep(delay_ms);
        }

        min_counter += 15; // The datasets are typically 15 mins apart, update counter accordingly
        if (min_counter > 1500) break; // Limit to 100 rows for demo
    }
    
    return 0;
}
