#include <iostream>
#include <iomanip>
#include <fstream>
#include <sstream>
#include <windows.h>
#include <ctime>
#include "esp32_anomaly_detector/embedded_cnn_corrector.h"

#include "cnn_weights.h"

// ============================================================================
// PURE C IMPLEMENTATION OF 1D CNN
// ============================================================================
float run_cnn_inference(const float* input_window) {
    // 1. Conv1D (kernel=3, filters=16) + ReLU
    // Input: 12 elements. Output: 10 elements x 16 filters
    float conv_out[10][16] = {0};
    for (int i = 0; i < 10; i++) {
        for (int f = 0; f < 16; f++) {
            float sum = conv_b[f];
            for (int k = 0; k < 3; k++) {
                sum += input_window[i + k] * conv_w[k][f];
            }
            conv_out[i][f] = sum > 0 ? sum : 0; // ReLU
        }
    }
    
    // 2. MaxPool1D (pool_size=2, strides=2)
    // Output: 5 elements x 16 filters
    float pool_out[5][16] = {0};
    for (int i = 0; i < 5; i++) {
        for (int f = 0; f < 16; f++) {
            float val1 = conv_out[i*2][f];
            float val2 = conv_out[i*2 + 1][f];
            pool_out[i][f] = val1 > val2 ? val1 : val2;
        }
    }
    
    // 3. Flatten
    float flat_out[80];
    int idx = 0;
    for (int i = 0; i < 5; i++) {
        for (int f = 0; f < 16; f++) {
            flat_out[idx++] = pool_out[i][f];
        }
    }
    
    // 4. Dense 1 (8 units) + ReLU
    float dense1_out[8] = {0};
    for (int d = 0; d < 8; d++) {
        float sum = dense1_b[d];
        for (int i = 0; i < 80; i++) {
            sum += flat_out[i] * dense1_w[i][d];
        }
        dense1_out[d] = sum > 0 ? sum : 0; // ReLU
    }
    
    // 5. Dense 2 (1 unit)
    float out = dense2_b;
    for (int i = 0; i < 8; i++) {
        out += dense1_out[i] * dense2_w[i];
    }
    
    return out;
}

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

std::time_t parse_time(const std::string& time_str) {
    int dd, mm, yyyy, hh, mn;
    if (sscanf(time_str.c_str(), "%d-%d-%d %d:%d", &dd, &mm, &yyyy, &hh, &mn) != 5) {
        return 0;
    }
    std::tm time_in = {0};
    time_in.tm_year = yyyy - 1900;
    time_in.tm_mon  = mm - 1;
    time_in.tm_mday = dd;
    time_in.tm_hour = hh;
    time_in.tm_min  = mn;
    time_in.tm_isdst = -1;
    return std::mktime(&time_in);
}

int main(int argc, char* argv[]) {
    std::cout << "--- C++ Embedded CNN Anomaly Detector Outage Tester ---\n";

    std::string filename = "data/processed/data-may26-june18_processed.csv";
    
    // Default outage: 800 * 15 mins is roughly June 4, let's just use empty strings for default
    std::string outage_start_str = "03-06-2026 00:00";
    std::string outage_end_str = "06-06-2026 00:00";

    if (argc >= 3) {
        outage_start_str = argv[1];
        outage_end_str = argv[2];
    }
    
    std::time_t outage_start = parse_time(outage_start_str);
    std::time_t outage_end = parse_time(outage_end_str);

    if (outage_start == 0 || outage_end == 0) {
        std::cerr << "Invalid date format. Use 'dd-mm-yyyy HH:MM'\n";
        std::cerr << "Example: scripts\\cnn_outage_tester.exe \"03-06-2026 00:00\" \"06-06-2026 00:00\"\n";
        return 1;
    }
    
    std::cout << "Simulating Outage from " << outage_start_str << " to " << outage_end_str << "\n";

    EmbeddedCNNCorrector corrector;

    std::ifstream file(filename);
    if (!file) {
        std::cerr << "Could not open " << filename << "\n";
        return 1;
    }

    std::string line;
    std::getline(file, line); // header

    int row_idx = 0;
    
    std::time_t first_time_t = 0;
    int first_min_counter = 0;
    bool is_first = true;

    while (std::getline(file, line)) {
        if (line.empty()) continue;
        DataPoint dp = parse_row(line);
        
        std::time_t t = parse_time(dp.time);
        if (is_first) {
            first_time_t = t;
            std::tm* time_in = std::localtime(&t);
            int first_wday = (time_in->tm_wday + 6) % 7; // Monday = 0
            first_min_counter = first_wday * 1440 + time_in->tm_hour * 60 + time_in->tm_min;
            corrector.reset(1.34f, first_min_counter);
            is_first = false;
        }

        uint32_t total_mins_since_start = (t - first_time_t) / 60;
        uint32_t min_counter = first_min_counter + total_mins_since_start;
        
        // Inject outage based on timestamp
        if (t >= outage_start && t < outage_end) {
            dp.wl_raw = 0.0f;
            dp.errorcode = 5;
        }

        bool is_anomaly = false;
        float corrected = corrector.process_sample(min_counter, dp.errorcode, dp.wl_raw, is_anomaly);
        
        int printed_ec = is_anomaly ? 3 : dp.errorcode; // 3 marks anomaly in Python parser

        std::cout << "Raw_WaterLevel:" << dp.wl_raw 
                  << ",Corr_WaterLevel:" << corrected 
                  << ",ErrorCode:" << printed_ec 
                  << ",Offset:" << corrector.get_anomaly_offset()
                  << ",Seq:" << corrector.get_anomaly_seq_len()
                  << "\n";
        
        row_idx++;
    }
    
    return 0;
}
