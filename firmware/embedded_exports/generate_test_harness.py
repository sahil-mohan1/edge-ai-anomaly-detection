# -*- coding: utf-8 -*-
"""
generate_test_harness.py
------------------------
Generates scripts/test_data.h and scripts/test_runner.cpp for local C++ compiler testing.
"""
import os
import sys
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression, LinearRegression

# Reuse the loading logic from test_anomaly_detection
from test_anomaly_detection import load_and_align_data, run_logistic_regression_detector

def main():
    df = load_and_align_data()
    
    # Train Linear Regression model for AR correction
    gt_wl = df['Water_Level_GT'].values
    gt_anom = df['Is_Anomaly_GT'].values
    raw_wl = df['Water_Level_Raw'].values
    errorcodes = df['errorcode'].values
    
    X_train_lr = []
    y_train_lr = []
    for i in range(2, len(df)):
        if gt_anom[i] == 0 and gt_anom[i-1] == 0 and gt_anom[i-2] == 0:
            X_train_lr.append([gt_wl[i-1], gt_wl[i-2]])
            y_train_lr.append(gt_wl[i])
    lr_model = LinearRegression()
    lr_model.fit(X_train_lr, y_train_lr)
    
    # Train Logistic Regression model again
    X_train = []
    y_train = []
    last_valid_gt = 1.34
    for i in range(len(df)):
        if i > 0 and not np.isnan(gt_wl[i-1]):
            last_valid_gt = gt_wl[i-1]
        abs_diff = abs(raw_wl[i] - last_valid_gt)
        X_train.append([raw_wl[i], errorcodes[i], abs_diff])
        y_train.append(gt_anom[i])
        
    logr = LogisticRegression()
    logr.fit(X_train, y_train)
    
    # Run predictions
    pred_anom, corr_wl = run_logistic_regression_detector(df, logr, lr_model)
    
    # Save the full aligned timeline data for C++ dashboard simulator parsing
    aligned_csv_path = "data/processed/aligned_test_data.csv"
    os.makedirs(os.path.dirname(aligned_csv_path), exist_ok=True)
    export_df = pd.DataFrame({
        'Time': df['Time'].dt.strftime('%Y-%m-%d %H:%M:%S'),
        'errorcode': errorcodes,
        'Water_Level_Raw': raw_wl,
        'Water_Level_GT': df['Water_Level_GT'].fillna(-1.0),
        'Is_Anomaly_GT': gt_anom
    })
    export_df.to_csv(aligned_csv_path, index=False)
    print(f"Exported aligned timeline to {aligned_csv_path}")
    
    # Find a window that contains several anomalies to make the test interesting
    anom_indices = np.where(pred_anom == 1)[0]
    if len(anom_indices) > 0:
        start_idx = max(0, anom_indices[0] - 10)
        end_idx = min(len(df), start_idx + 100)
    else:
        start_idx = 0
        end_idx = min(len(df), 100)
        
    # Generate test_data.h
    test_data_path = "scripts/test_data.h"
    with open(test_data_path, "w") as f:
        f.write("// Auto-generated test cases from Python evaluation script\n")
        f.write("#ifndef TEST_DATA_H\n#define TEST_DATA_H\n\n")
        f.write("struct TestRow {\n")
        f.write("    float wl_raw;\n")
        f.write("    int errorcode;\n")
        f.write("    float expected_wl_corrected;\n")
        f.write("    bool expected_is_anomaly;\n")
        f.write("};\n\n")
        f.write(f"const int num_test_rows = {end_idx - start_idx};\n\n")
        f.write("const TestRow test_rows[] = {\n")
        for i in range(start_idx, end_idx):
            f.write(f"    {{ {raw_wl[i]:.4f}f, {int(errorcodes[i])}, {corr_wl[i]:.4f}f, {str(pred_anom[i] == 1).lower()} }},\n")
        f.write("};\n\n")
        f.write("#endif // TEST_DATA_H\n")
        
    print(f"Generated C++ test vectors in {test_data_path}")
    
    # Generate test_runner.cpp
    runner_path = "scripts/test_runner.cpp"
    with open(runner_path, "w") as f:
        f.write(r"""// C++ Software-in-the-Loop Test Runner
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
""")
    print(f"Generated C++ runner in {runner_path}")

if __name__ == "__main__":
    main()
