#ifndef EMBEDDED_CNN_CORRECTOR_H
#define EMBEDDED_CNN_CORRECTOR_H

#include <cmath>
#include <cstdint>

// Forward declaration of the inference function that you will implement
// using X-CUBE-AI or TFLite Micro.
// It should take a float array of size 12 and return a single float prediction.
extern float run_cnn_inference(const float* input_window);

class EmbeddedCNNCorrector {
private:
    static constexpr int WINDOW_SIZE = 12;
    static constexpr float BASE_THRESH = 0.5f;
    static constexpr float MAX_THRESH = 1.5f;
    static constexpr float THRESH_DECAY = 0.9f;
    static constexpr uint32_t MAX_GAP_MINUTES = 25; // Re-seed buffer if gap > 25 mins

    float history[WINDOW_SIZE];
    int history_count;
    
    float last_corrected_wl;
    uint32_t last_valid_time; // Using uint32_t for unix timestamp or minute counter
    float dyn_thresh;
    bool buffer_poisoned; // Tracks if a 0.0 drop poisoned the buffer

public:
    EmbeddedCNNCorrector() {
        reset(1.34f, 0);
    }

    void reset(float initial_wl, uint32_t current_time) {
        history_count = 0;
        last_corrected_wl = initial_wl;
        last_valid_time = current_time;
        dyn_thresh = BASE_THRESH;
        buffer_poisoned = false;
        
        for (int i = 0; i < WINDOW_SIZE; i++) {
            history[i] = initial_wl;
        }
    }

    void push_history(float val) {
        for (int i = 0; i < WINDOW_SIZE - 1; i++) {
            history[i] = history[i + 1];
        }
        history[WINDOW_SIZE - 1] = val;
        if (history_count < WINDOW_SIZE) {
            history_count++;
        }
    }

    // Process a single sample. 
    // current_time must be in minutes (e.g., unix timestamp / 60)
    float process_sample(uint32_t current_time, int errorcode, float wl_raw, bool& is_anomaly) {
        is_anomaly = false;

        // 1. Basic Protocol & Bounds Checks
        bool is_protocol_error = (errorcode == 1 || errorcode == 3) || 
                                 (errorcode == 5 && (wl_raw == 0.0f || wl_raw >= 4.45f));
        bool is_bounds_error = (wl_raw < 0.05f || wl_raw >= 4.45f);

        // 2. Sudden Zero Dropout Rule
        bool sudden_zero = false;
        if (wl_raw == 0.0f) {
            float drop = std::abs(wl_raw - last_corrected_wl);
            if (drop > 0.5f) {
                sudden_zero = true;
            }
        }

        if (is_protocol_error || is_bounds_error || sudden_zero) {
            is_anomaly = true;
            
            // Time-gap check for buffer re-seeding
            uint32_t gap_mins = current_time - last_valid_time;
            if (gap_mins > MAX_GAP_MINUTES) {
                buffer_poisoned = true;
            }
            
            // Zero-padding interpolation (fill gap with 0.0 in logic, but don't output 0.0)
            if (gap_mins > 15) {
                push_history(0.0f);
            }
            return last_corrected_wl;
        }

        // 3. Buffer Re-seeding on Recovery
        uint32_t gap_mins = current_time - last_valid_time;
        if (buffer_poisoned && gap_mins > MAX_GAP_MINUTES) {
            // Re-seed the entire buffer with this first valid reading to wipe momentum
            for (int i = 0; i < WINDOW_SIZE; i++) {
                history[i] = wl_raw;
            }
            history_count = WINDOW_SIZE;
            buffer_poisoned = false;
        }

        // 4. Initial Startup Bypass
        if (history_count < WINDOW_SIZE) {
            push_history(wl_raw);
            last_valid_time = current_time;
            last_corrected_wl = wl_raw;
            dyn_thresh = BASE_THRESH;
            return wl_raw;
        }

        // 5. CNN Inference
        // Note: For full INT8 TFLite/X-CUBE-AI, history buffer could be maintained as int8,
        // but keeping it float here makes it independent of the model's quantization details.
        float raw_pred = run_cnn_inference(history);
        
        // Round to 3 decimal places to match Python logic and prevent noisy residual values
        float cnn_pred = std::round(raw_pred * 1000.0f) / 1000.0f;

        // 6. Thresholding & Residual Gate
        float residual = std::abs(wl_raw - cnn_pred);
        float roc = std::abs(wl_raw - last_corrected_wl);
        
        // Expand threshold if a valid large change happened recently
        uint32_t time_since_valid = current_time - last_valid_time;
        dyn_thresh = BASE_THRESH + (dyn_thresh - BASE_THRESH) * std::pow(THRESH_DECAY, time_since_valid);
        
        if (roc <= BASE_THRESH) {
            // Normal physical rate of change, trust the sensor directly
            is_anomaly = false;
        } else if (residual > dyn_thresh) {
            is_anomaly = true;
            dyn_thresh = std::min((float)MAX_THRESH, dyn_thresh + 0.1f);
            
            if (gap_mins > 15) {
                push_history(0.0f);
            }
            return last_corrected_wl;
        }

        // Normal reading
        is_anomaly = false;
        dyn_thresh = BASE_THRESH;
        last_valid_time = current_time;
        last_corrected_wl = std::round(wl_raw * 1000.0f) / 1000.0f;
        push_history(last_corrected_wl);

        return last_corrected_wl;
    }
};

#endif // EMBEDDED_CNN_CORRECTOR_H
