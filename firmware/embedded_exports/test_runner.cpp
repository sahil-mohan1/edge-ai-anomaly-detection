// C++ Software-in-the-Loop Test Runner
#include <iostream>
#include <iomanip>
#include <cmath>
#include "custom_model.h"
#include "test_data.h"

int main() {
    std::cout << "============================================================" << std::endl;
    std::cout << "  C++ SOFTWARE-IN-THE-LOOP MODEL SIMULATION TEST" << std::endl;
    std::cout << "============================================================" << std::endl;

    WaterLevelAnomalyDetector detector;
    detector.reset(1.34f);

    int passes = 0;
    int failures = 0;

    std::cout << std::left 
              << std::setw(8)  << "Step"
              << std::setw(12) << "Raw WL"
              << std::setw(10) << "ErrorCode"
              << std::setw(15) << "C++ Corr"
              << std::setw(15) << "Py Corr"
              << std::setw(15) << "C++ Anom"
              << std::setw(15) << "Py Anom"
              << "Status" << std::endl;
    std::cout << std::string(95, '-') << std::endl;

    for (int i = 0; i < num_test_rows; ++i) {
        bool cpp_is_anomaly = false;
        float cpp_corr_wl = detector.process_sample(test_rows[i].wl_raw, test_rows[i].errorcode, cpp_is_anomaly);

        // Check if output matches Python expectations (within small float delta)
        bool value_match = std::abs(cpp_corr_wl - test_rows[i].expected_wl_corrected) < 0.001f;
        bool status_match = (cpp_is_anomaly == test_rows[i].expected_is_anomaly);

        bool success = value_match && status_match;

        std::cout << std::left 
                  << std::setw(8)  << i
                  << std::setw(12) << test_rows[i].wl_raw
                  << std::setw(10) << test_rows[i].errorcode
                  << std::setw(15) << cpp_corr_wl
                  << std::setw(15) << test_rows[i].expected_wl_corrected
                  << std::setw(15) << (cpp_is_anomaly ? "True" : "False")
                  << std::setw(15) << (test_rows[i].expected_is_anomaly ? "True" : "False")
                  << (success ? "PASS" : "FAIL") << std::endl;

        if (success) {
            passes++;
        } else {
            failures++;
        }
    }

    std::cout << std::string(95, '-') << std::endl;
    std::cout << "Summary: " << passes << " passed, " << failures << " failed." << std::endl;
    
    if (failures == 0) {
        std::cout << "SUCCESS: C++ implementation matches Python outputs perfectly!" << std::endl;
        return 0;
    } else {
        std::cout << "FAILURE: Discrepancy found between C++ and Python models." << std::endl;
        return 1;
    }
}
