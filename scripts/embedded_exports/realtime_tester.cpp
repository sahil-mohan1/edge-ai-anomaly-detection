#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <cmath>
#include <windows.h> // For Sleep() on Windows
#include <iomanip>
#include "custom_model.h"

// Struct to store CSV rows
struct DataPoint {
    std::string time;
    int errorcode;
    float wl_raw;
    float wl_gt;
    int is_anomaly_gt;
};

// Parse a single CSV row
DataPoint parse_row(const std::string& line) {
    std::stringstream ss(line);
    std::string temp;
    DataPoint dp;

    std::getline(ss, dp.time, ',');
    
    std::getline(ss, temp, ',');
    dp.errorcode = std::atoi(temp.c_str());

    std::getline(ss, temp, ',');
    dp.wl_raw = std::atof(temp.c_str());

    std::getline(ss, temp, ',');
    dp.wl_gt = std::atof(temp.c_str());

    std::getline(ss, temp, ',');
    dp.is_anomaly_gt = std::atoi(temp.c_str());

    return dp;
}

void print_header() {
    std::cout << "\n" << std::string(100, '=') << std::endl;
    std::cout << "  C++ REAL-TIME LOGISTIC REGRESSION ANOMALY DETECTION TESTER" << std::endl;
    std::cout << std::string(100, '=') << std::endl;
}

void run_interactive_mode() {
    WaterLevelAnomalyDetector detector;
    detector.reset(1.34f);

    std::cout << "\n>>> Starting Interactive Manual Mode." << std::endl;
    std::cout << "Enter sensor measurements manually to see the C++ model prediction in micro-seconds." << std::endl;
    std::cout << "Type 'exit' as the water level to return to menu." << std::endl;
    std::cout << std::string(100, '-') << std::endl;

    while (true) {
        std::string input;
        std::cout << "\nEnter Raw Water Level (meters): ";
        std::cin >> input;
        if (input == "exit" || input == "quit" || input == "e") {
            break;
        }

        float wl_raw;
        try {
            wl_raw = std::stof(input);
        } catch (...) {
            std::cout << "Invalid water level input. Please enter a number." << std::endl;
            continue;
        }

        int errorcode;
        std::cout << "Enter Error Code (e.g. 0=Normal, 1/3=Abort, 5=Unstable): ";
        if (!(std::cin >> errorcode)) {
            std::cin.clear();
            std::cin.ignore(10000, '\n');
            std::cout << "Invalid error code input. Must be an integer." << std::endl;
            continue;
        }

        bool is_anomaly = false;
        float corrected_wl = detector.process_sample(wl_raw, errorcode, is_anomaly);

        std::cout << "\n--- C++ Model Prediction ---" << std::endl;
        std::cout << "  - Input Raw WL:    " << wl_raw << " m" << std::endl;
        std::cout << "  - Input Errorcode: " << errorcode << std::endl;
        std::cout << "  - Corrected WL:    " << corrected_wl << " m" << std::endl;
        std::cout << "  - Classification:  " 
                  << (is_anomaly ? "\033[1;31mANOMALY DETECTED\033[0m" : "\033[1;32mNORMAL (No Anomaly)\033[0m") 
                  << std::endl;
    }
}

void run_stream_simulation_mode() {
    std::string filename = "data/processed/aligned_test_data.csv";
    std::ifstream file(filename);
    if (!file) {
        std::cerr << "Error: " << filename << " not found!" << std::endl;
        std::cerr << "Make sure you run scripts/generate_test_harness.py first." << std::endl;
        return;
    }

    std::string line;
    // Discard header
    std::getline(file, line);

    int delay_ms = 100;
    std::cout << "\nEnter streaming delay between samples in milliseconds (default: 100ms): ";
    std::string delay_input;
    std::cin.ignore(); // Clear any leftover newline
    std::getline(std::cin, delay_input);
    if (!delay_input.empty()) {
        try {
            delay_ms = std::stoi(delay_input);
        } catch (...) {
            std::cout << "Invalid delay. Using default 100ms." << std::endl;
        }
    }

    std::cout << "\n>>> Streaming data at 1 sample every " << delay_ms << "ms (simulation speedup: " 
              << (15.0 * 60.0 * 1000.0 / delay_ms) << "x)" << std::endl;
    std::cout << "Press Ctrl+C to stop streaming." << std::endl;
    std::cout << std::string(100, '-') << std::endl;

    std::cout << std::left
              << std::setw(22) << "Timestamp"
              << std::setw(12) << "Raw WL"
              << std::setw(10) << "ErrorCode"
              << std::setw(15) << "Corrected WL"
              << std::setw(18) << "C++ Prediction"
              << std::setw(15) << "GT Anomaly"
              << "Status" << std::endl;
    std::cout << std::string(100, '-') << std::endl;

    WaterLevelAnomalyDetector detector;
    detector.reset(1.34f);

    while (std::getline(file, line)) {
        if (line.empty()) continue;
        DataPoint dp = parse_row(line);

        bool is_anomaly = false;
        float corrected_wl = detector.process_sample(dp.wl_raw, dp.errorcode, is_anomaly);

        std::string cpp_pred_str = is_anomaly ? "\033[1;31mANOMALY\033[0m" : "\033[1;32mNORMAL\033[0m";
        std::string gt_str = (dp.is_anomaly_gt == 1) ? "ANOMALY" : "NORMAL";
        
        bool match = (is_anomaly == (dp.is_anomaly_gt == 1));
        std::string match_str = match ? "\033[1;32mPASS\033[0m" : "\033[1;31mFAIL (Discrepancy)\033[0m";

        std::cout << std::left
                  << std::setw(22) << dp.time
                  << std::setw(12) << dp.wl_raw
                  << std::setw(10) << dp.errorcode
                  << std::setw(15) << corrected_wl
                  << std::setw(27) << cpp_pred_str // 27 width to account for ANSI escape color codes
                  << std::setw(15) << gt_str
                  << match_str << std::endl;

        Sleep(delay_ms);
    }
    file.close();
    std::cout << "\nStream completed!" << std::endl;
}

int main() {
    while (true) {
        print_header();
        std::cout << "Select mode:\n";
        std::cout << "  1. Simulated Live Stream (Stream CSV data points at speed)\n";
        std::cout << "  2. Interactive Manual Input (Enter data manually to get instantaneous prediction)\n";
        std::cout << "  3. Exit\n";
        std::cout << "Choice: ";
        
        int choice;
        if (!(std::cin >> choice)) {
            std::cin.clear();
            std::cin.ignore(10000, '\n');
            std::cout << "Invalid choice. Please select 1, 2, or 3." << std::endl;
            continue;
        }

        if (choice == 1) {
            run_stream_simulation_mode();
        } else if (choice == 2) {
            run_interactive_mode();
        } else if (choice == 3) {
            std::cout << "Exiting. Goodbye!" << std::endl;
            break;
        } else {
            std::cout << "Invalid option." << std::endl;
        }
    }
    return 0;
}
