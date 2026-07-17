#include <iostream>
#include <iomanip>
#include <fstream>
#include <sstream>
#include <vector>
#include <cmath>
#include <deque>
#include <ctime>

// Include the extracted weights
#include "mlp_weights.h"

using namespace std;

// Activation functions
float relu(float x) { return x > 0.0f ? x : 0.0f; }
float sigmoid(float x) { return 1.0f / (1.0f + std::exp(-x)); }

// Matrix Vector multiplication
void dense_layer(const float* input, int in_dim, int out_dim, const float* w, const float* b, float* output, bool use_relu) {
    for (int i = 0; i < out_dim; i++) {
        float sum = b[i];
        for (int j = 0; j < in_dim; j++) {
            sum += input[j] * w[j * out_dim + i];
        }
        output[i] = use_relu ? relu(sum) : sum;
    }
}

struct MLPOutput {
    float anomaly_prob;
    float predicted_wl;
};

MLPOutput run_mlp_inference(const float* input_features) {
    // CLASSIFICATION BRANCH (uses all 23 features)
    float h1_cls[64];
    dense_layer(input_features, 23, 64, (const float*)hidden1_cls_w, hidden1_cls_b, h1_cls, true);
    
    float h2_cls[32];
    dense_layer(h1_cls, 64, 32, (const float*)hidden2_cls_w, hidden2_cls_b, h2_cls, true);
    
    float anomaly_out;
    dense_layer(h2_cls, 32, 1, (const float*)anomaly_w, anomaly_b, &anomaly_out, false);
    anomaly_out = sigmoid(anomaly_out);

    // REGRESSION BRANCH (uses 21 features, skipping index 0 and 1)
    const float* reg_inputs = &input_features[2];
    
    float h1_reg[64];
    dense_layer(reg_inputs, 21, 64, (const float*)hidden1_reg_w, hidden1_reg_b, h1_reg, true);
    
    float h2_reg[32];
    dense_layer(h1_reg, 64, 32, (const float*)hidden2_reg_w, hidden2_reg_b, h2_reg, true);
    
    float h3_reg[16];
    dense_layer(h2_reg, 32, 16, (const float*)hidden3_reg_w, hidden3_reg_b, h3_reg, true);
    
    float wl_out;
    dense_layer(h3_reg, 16, 1, (const float*)wl_w, wl_b, &wl_out, false);

    MLPOutput out;
    out.anomaly_prob = anomaly_out;
    out.predicted_wl = wl_out;
    return out;
}

// Data Parsing
struct DataPoint {
    std::string time_str;
    int errorcode;
    float wl_raw;
    std::time_t ts;
};

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

DataPoint parse_row(const std::string& line) {
    std::stringstream ss(line);
    std::string temp;
    DataPoint dp;
    std::getline(ss, dp.time_str, ',');
    std::getline(ss, temp, ',');
    dp.errorcode = std::atoi(temp.c_str());
    std::getline(ss, temp, ',');
    dp.wl_raw = std::atof(temp.c_str());
    dp.ts = parse_time(dp.time_str);
    return dp;
}

void build_time_features(std::time_t t, float* features) {
    std::tm* tm_info = std::localtime(&t);
    int mins_day = tm_info->tm_hour * 60 + tm_info->tm_min;
    float day_frac = (mins_day % 1440) / 1440.0f;
    float half_day_frac = (mins_day % 720) / 720.0f;
    float quarter_day_frac = (mins_day % 360) / 360.0f;
    float eighth_day_frac = (mins_day % 180) / 180.0f;
    
    int wday = (tm_info->tm_wday + 6) % 7; // Monday = 0
    int mins_week = wday * 1440 + mins_day;
    float week_frac = mins_week / 10080.0f;
    
    float PI = 3.141592653589793f;
    
    features[0] = std::sin(2 * PI * week_frac);
    features[1] = std::cos(2 * PI * week_frac);
    features[2] = std::sin(2 * PI * day_frac);
    features[3] = std::cos(2 * PI * day_frac);
    features[4] = std::sin(2 * PI * half_day_frac);
    features[5] = std::cos(2 * PI * half_day_frac);
    features[6] = std::sin(2 * PI * quarter_day_frac);
    features[7] = std::cos(2 * PI * quarter_day_frac);
    features[8] = std::sin(2 * PI * eighth_day_frac);
    features[9] = std::cos(2 * PI * eighth_day_frac);
    features[10] = week_frac;
    features[11] = (float)wday / 6.0f;
}

int main(int argc, char* argv[]) {
    std::cout << "--- C++ AR-MLP Autoregressive Simulator ---\n";
    
    // Read the CLEAN dataset so we can inject our own outage anywhere
    std::string in_file = "C:\\Users\\sahil\\Desktop\\ICFOSS\\Anomaly Detection\\data\\processed\\data-june6-july1_processed.csv";
    std::string out_file = "C:\\Users\\sahil\\Desktop\\ICFOSS\\Anomaly Detection\\data\\processed\\mlp_c_simulation.csv";
    
    std::time_t outage_start = 0;
    std::time_t outage_end = 0;
    
    if (argc >= 3) {
        outage_start = parse_time(argv[1]);
        outage_end = parse_time(argv[2]);
        std::cout << "Injecting Outage from " << argv[1] << " to " << argv[2] << "\n";
    }
    
    std::ifstream file(in_file);
    if (!file) {
        std::cerr << "Could not open " << in_file << "\n";
        return 1;
    }
    
    std::ofstream out(out_file);
    out << "Time,errorcode,wl_raw,predicted_wl,anomaly_prob,is_anomaly\n";

    std::string line;
    std::getline(file, line); // header

    // Initialize lag buffer (empty, will accumulate during warmup)
    std::deque<float> lag_buffer;
    
    int prev_errorcode = 0;
    int consecutive_anomalies = 0;
    const float BASE_THRESH = 0.5f;
    const float MAX_THRESH = 1.5f;
    float dyn_thresh = BASE_THRESH;
    float last_corrected = 1.18f;
    int row_idx = 0;

    while (std::getline(file, line)) {
        if (line.empty()) continue;
        DataPoint dp = parse_row(line);
        
        // Fix 2: Clean Warmup Phase
        // Do not run inference for the first 8 rows. Just seed the lag buffer with real data
        // and skip writing to the output CSV (matching Python's history drop behavior).
        if (row_idx < 8) {
            lag_buffer.push_back(dp.wl_raw);
            prev_errorcode = dp.errorcode;
            row_idx++;
            continue;
        }
        
        // Inject outage if within window
        if (outage_start != 0 && dp.ts >= outage_start && dp.ts <= outage_end) {
            dp.wl_raw = 0.0f;
            dp.errorcode = 1;
        }
        
        float input_features[23];
        input_features[0] = (float)dp.errorcode / 5.0f;
        input_features[1] = dp.wl_raw / 4.5f;
        
        // Load lags 
        for(int i=0; i<8; i++) {
            input_features[2 + i] = lag_buffer[7 - i]; // Reverse order as per Python implementation
        }
        
        // Time features
        build_time_features(dp.ts, &input_features[10]);
        
        input_features[22] = (float)prev_errorcode / 5.0f; // Force clean state to prevent dampened regression hallucination
        
        // Run model
        MLPOutput result = run_mlp_inference(input_features);
        
        // Fix 1: Unified Anomaly Logic & Threshold tracking
        bool is_anomaly = false;
        float residual = std::abs(dp.wl_raw - result.predicted_wl);
        
        if (dp.errorcode == 5 || dp.wl_raw < 0.05f || dp.wl_raw >= 4.45f || residual > dyn_thresh) {
            is_anomaly = true;
            dyn_thresh = std::min(MAX_THRESH, dyn_thresh + 0.1f);
        } else {
            dyn_thresh = BASE_THRESH;
        }
        
        float corrected_wl = is_anomaly ? result.predicted_wl : dp.wl_raw;
        corrected_wl = std::max(0.0f, std::min(corrected_wl, 4.5f));
        
        out << dp.time_str << "," 
            << dp.errorcode << "," 
            << dp.wl_raw << "," 
            << result.predicted_wl << "," 
            << result.anomaly_prob << "," 
            << (is_anomaly ? 1 : 0) << "\n";
            
        // Autoregressive lag update
        lag_buffer.push_back(corrected_wl);
        lag_buffer.pop_front();
        
        last_corrected = corrected_wl;
        prev_errorcode = dp.errorcode;
        
        row_idx++; // MUST increment for non-warmup rows too!
    }
    
    std::cout << "Simulation complete. Output saved to " << out_file << "\n";
    return 0;
}
