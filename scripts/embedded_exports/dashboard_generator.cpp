// C++ Software-in-the-Loop Interactive Dashboard Generator
#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include "custom_model.h"

struct Row {
    std::string time;
    int errorcode;
    float wl_raw;
    float wl_gt;
    int is_anomaly_gt;
};

// Simple helper to parse a CSV line
Row parse_csv_line(const std::string &line) {
    std::stringstream ss(line);
    std::string temp;
    Row r;
    
    // Time
    std::getline(ss, r.time, ',');
    
    // Errorcode
    std::getline(ss, temp, ',');
    r.errorcode = std::atoi(temp.c_str());
    
    // Raw WL
    std::getline(ss, temp, ',');
    r.wl_raw = std::atof(temp.c_str());
    
    // GT WL
    std::getline(ss, temp, ',');
    r.wl_gt = std::atof(temp.c_str());
    
    // GT Anomaly
    std::getline(ss, temp, ',');
    r.is_anomaly_gt = std::atoi(temp.c_str());
    
    return r;
}

int get_weekly_bin_from_time(const std::string& time_str) {
    size_t space_pos = time_str.find(' ');
    if (space_pos == std::string::npos || time_str.length() < space_pos + 6) return 0;
    
    // Parse Year, Month, Day to calculate Day of Week
    int year = std::atoi(time_str.substr(0, 4).c_str());
    int month = std::atoi(time_str.substr(5, 2).c_str());
    int day = std::atoi(time_str.substr(8, 2).c_str());
    
    // Sakamoto's algorithm to calculate day of week (0 = Sunday, 1 = Monday, ..., 6 = Saturday)
    static int t[] = { 0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4 };
    int temp_year = year;
    if (month < 3) temp_year -= 1;
    int day_of_week = (temp_year + temp_year/4 - temp_year/100 + temp_year/400 + t[month-1] + day) % 7;
    
    int hour = std::atoi(time_str.substr(space_pos + 1, 2).c_str());
    int minute = std::atoi(time_str.substr(space_pos + 4, 2).c_str());
    
    return day_of_week * 96 + hour * 4 + minute / 15;
}

int main() {
    std::cout << "============================================================" << std::endl;
    std::cout << "  C++ INTERACTIVE DASHBOARD SIMULATION GENERATOR" << std::endl;
    std::cout << "============================================================" << std::endl;

    std::ifstream csv("data/processed/aligned_test_data.csv");
    if (!csv) {
        std::cerr << "Error: data/processed/aligned_test_data.csv not found! Run generate_test_harness.py first." << std::endl;
        return 1;
    }

    std::string line;
    // Discard header
    std::getline(csv, line);

    std::vector<std::string> times;
    std::vector<float> raw_wls;
    std::vector<int> errorcodes;
    std::vector<float> corr_wls_ar;
    std::vector<float> corr_wls_diurnal;
    std::vector<float> corr_wls_harmonic;
    std::vector<bool> cpp_anoms;
    std::vector<int> gt_anoms;

    WaterLevelAnomalyDetector detector_ar(MODE_AR);
    WaterLevelAnomalyDetector detector_diurnal(MODE_DIURNAL);
    WaterLevelAnomalyDetector detector_harmonic(MODE_HARMONIC);
    
    detector_ar.reset(1.34f);
    detector_diurnal.reset(1.34f);
    detector_harmonic.reset(1.34f);

    std::cout << "Loading dataset and simulating C++ Logistic Regression model (AR, Weekly Diurnal, Weekly Harmonic correctors)..." << std::endl;
    
    int tp = 0, fp = 0, tn = 0, fn = 0;

    while (std::getline(csv, line)) {
        if (line.empty()) continue;
        Row r = parse_csv_line(line);

        int weekly_bin = get_weekly_bin_from_time(r.time);

        bool is_anomaly_ar = false;
        float corr_wl_ar = detector_ar.process_sample(r.wl_raw, r.errorcode, is_anomaly_ar, weekly_bin);

        bool is_anomaly_diurnal = false;
        float corr_wl_diurnal = detector_diurnal.process_sample(r.wl_raw, r.errorcode, is_anomaly_diurnal, weekly_bin);

        bool is_anomaly_harmonic = false;
        float corr_wl_harmonic = detector_harmonic.process_sample(r.wl_raw, r.errorcode, is_anomaly_harmonic, weekly_bin);

        times.push_back(r.time);
        raw_wls.push_back(r.wl_raw);
        errorcodes.push_back(r.errorcode);
        corr_wls_ar.push_back(corr_wl_ar);
        corr_wls_diurnal.push_back(corr_wl_diurnal);
        corr_wls_harmonic.push_back(corr_wl_harmonic);
        cpp_anoms.push_back(is_anomaly_ar);
        gt_anoms.push_back(r.is_anomaly_gt);

        // Compute baseline (AR) classification metrics
        if (r.is_anomaly_gt == 1 && is_anomaly_ar) tp++;
        else if (r.is_anomaly_gt == 0 && is_anomaly_ar) fp++;
        else if (r.is_anomaly_gt == 0 && !is_anomaly_ar) tn++;
        else if (r.is_anomaly_gt == 1 && !is_anomaly_ar) fn++;
    }

    csv.close();

    float accuracy = (float)(tp + tn) / (times.size());
    float precision = (tp + fp > 0) ? (float)tp / (tp + fp) : 0.0f;
    float recall = (tp + fn > 0) ? (float)tp / (tp + fn) : 0.0f;
    float f1 = (precision + recall > 0) ? 2.0f * (precision * recall) / (precision + recall) : 0.0f;
    float fpr = (fp + tn > 0) ? (float)fp / (fp + tn) : 0.0f;

    std::cout << "Baseline C++ Model (AR) Simulation Metrics Summary:" << std::endl;
    std::cout << "  - Accuracy:  " << accuracy * 100.0f << "%" << std::endl;
    std::cout << "  - F1-Score:  " << f1 * 100.0f << "%" << std::endl;
    std::cout << "  - Precision: " << precision * 100.0f << "%" << std::endl;
    std::cout << "  - Recall:    " << recall * 100.0f << "%" << std::endl;
    std::cout << "  - FPR:       " << fpr * 100.0f << "% (FP: " << fp << ")" << std::endl;

    std::cout << "Writing plots/task6/cpp_interactive_dashboard.html..." << std::endl;

    std::ofstream out("plots/task6/cpp_interactive_dashboard.html");
    if (!out) {
        std::cerr << "Error: Failed to create output dashboard file!" << std::endl;
        return 1;
    }

    out << R"html(<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>C++ Edge Logistic Regression - Interactive Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #0f172a;
            color: #f1f5f9;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
        }
        header {
            background-color: #1e293b;
            padding: 15px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #334155;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        h1 {
            margin: 0;
            font-size: 20px;
            font-weight: 600;
            color: #38bdf8;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .badge {
            background-color: #0284c7;
            color: #e0f2fe;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
        }
        .meta-info {
            display: flex;
            gap: 20px;
            font-size: 13px;
            color: #94a3b8;
        }
        .meta-item strong {
            color: #f1f5f9;
        }
        .control-panel {
            display: flex;
            align-items: center;
            gap: 24px;
            padding: 12px 30px;
            background-color: #1e293b;
            border-bottom: 1px solid #334155;
            flex-wrap: wrap;
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.15);
        }
        .control-title {
            font-size: 11px;
            font-weight: 700;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-right: 8px;
        }
        .control-item {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 13px;
            font-weight: 500;
            color: #94a3b8;
            cursor: pointer;
            user-select: none;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            padding: 4px 8px;
            border-radius: 6px;
        }
        .control-item:hover {
            color: #f1f5f9;
            background-color: rgba(255, 255, 255, 0.03);
        }
        .control-item input[type="checkbox"] {
            display: none;
        }
        .custom-checkbox {
            width: 15px;
            height: 15px;
            border: 2px solid var(--color);
            border-radius: 4px;
            display: inline-block;
            position: relative;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            background-color: transparent;
        }
        .control-item input[type="checkbox"]:checked + .custom-checkbox {
            background-color: var(--color);
            box-shadow: 0 0 8px var(--color);
        }
        .control-item input[type="checkbox"]:checked + .custom-checkbox::after {
            content: '';
            position: absolute;
            left: 4px;
            top: 1px;
            width: 3px;
            height: 7px;
            border: solid #0f172a;
            border-width: 0 2px 2px 0;
            transform: rotate(45deg);
        }
        #chart-container {
            flex-grow: 1;
            padding: 20px;
            background-color: #0f172a;
            position: relative;
        }
        #chart {
            width: 100%;
            height: 100%;
            border-radius: 8px;
            overflow: hidden;
        }
    </style>
</head>
<body>
    <header>
        <div>
            <h1>C++ SIL Simulation Dashboard <span class="badge">Logistic Regression</span></h1>
            <div style="font-size: 12px; color: #64748b; margin-top: 4px;">Inference generated entirely by compiled C++ code on Windows host</div>
        </div>
        <div class="meta-info">
            <div class="meta-item">Total Samples: <strong id="total-samples">0</strong></div>
            <div class="meta-item">Anomalies Detected: <strong id="anomalies-count" style="color: #ef4444;">0</strong></div>
            <div class="meta-item">FPR: <strong id="fpr-val">0.00%</strong></div>
        </div>
    </header>
    <div class="control-panel">
        <span class="control-title">Toggle Traces:</span>
        <label class="control-item" style="--color: rgba(239, 68, 68, 0.85);">
            <input type="checkbox" id="toggle-raw" checked onchange="updateVisibility(0, this.checked)">
            <span class="custom-checkbox"></span>
            Raw Sensor Data
        </label>
        <label class="control-item" style="--color: #10b981;">
            <input type="checkbox" id="toggle-ar" checked onchange="updateVisibility(1, this.checked)">
            <span class="custom-checkbox"></span>
            AR Predictor
        </label>
        <label class="control-item" style="--color: #f59e0b;">
            <input type="checkbox" id="toggle-diurnal" checked onchange="updateVisibility(2, this.checked)">
            <span class="custom-checkbox"></span>
            Weekly Profile
        </label>
        <label class="control-item" style="--color: #8b5cf6;">
            <input type="checkbox" id="toggle-harmonic" checked onchange="updateVisibility(3, this.checked)">
            <span class="custom-checkbox"></span>
            Weekly Harmonic Fit
        </label>
        <label class="control-item" style="--color: #ef4444;">
            <input type="checkbox" id="toggle-anom" checked onchange="updateVisibility(4, this.checked)">
            <span class="custom-checkbox"></span>
            Flagged Anomalies
        </label>
    </div>
    <div id="chart-container">
        <div id="chart"></div>
    </div>

    <script>
)html";

    out << "        const times = [";
    for (size_t i = 0; i < times.size(); ++i) {
        out << "\"" << times[i] << "\"" << (i == times.size()-1 ? "" : ",");
    }
    out << "];\n";

    out << "        const raw_wl = [";
    out << std::fixed << std::setprecision(3);
    for (size_t i = 0; i < raw_wls.size(); ++i) {
        out << raw_wls[i] << (i == raw_wls.size()-1 ? "" : ",");
    }
    out << "];\n";

    out << "        const corr_wl_ar = [";
    for (size_t i = 0; i < corr_wls_ar.size(); ++i) {
        out << corr_wls_ar[i] << (i == corr_wls_ar.size()-1 ? "" : ",");
    }
    out << "];\n";

    out << "        const corr_wl_diurnal = [";
    for (size_t i = 0; i < corr_wls_diurnal.size(); ++i) {
        out << corr_wls_diurnal[i] << (i == corr_wls_diurnal.size()-1 ? "" : ",");
    }
    out << "];\n";

    out << "        const corr_wl_harmonic = [";
    for (size_t i = 0; i < corr_wls_harmonic.size(); ++i) {
        out << corr_wls_harmonic[i] << (i == corr_wls_harmonic.size()-1 ? "" : ",");
    }
    out << "];\n";

    out << "        const cpp_anom = [";
    for (size_t i = 0; i < cpp_anoms.size(); ++i) {
        out << (cpp_anoms[i] ? "true" : "false") << (i == cpp_anoms.size()-1 ? "" : ",");
    }
    out << "];\n";

    out << R"html(
        document.getElementById('total-samples').innerText = times.length;
        
        let anomCount = 0;
        const anomTimes = [];
        const anomValues = [];

        for(let i = 0; i < times.length; i++) {
            if(cpp_anom[i]) {
                anomCount++;
                anomTimes.push(times[i]);
                anomValues.push(raw_wl[i]);
            }
        }
        document.getElementById('anomalies-count').innerText = anomCount;
)html";

    out << "        document.getElementById('fpr-val').innerText = \"" << fpr * 100.0f << "%\";\n";

    out << R"html(
        // Trace 1: Raw Data
        const traceRaw = {
            x: times,
            y: raw_wl,
            type: 'scatter',
            mode: 'lines',
            name: 'Raw Sensor Data',
            line: { color: 'rgba(239, 68, 68, 0.45)', width: 1 },
            opacity: 0.8
        };

        // Trace 2a: Corrected Data (AR)
        const traceCorrAr = {
            x: times,
            y: corr_wl_ar,
            type: 'scatter',
            mode: 'lines',
            name: 'C++ Corrected (AR Predictor)',
            line: { color: '#10b981', width: 1.5 }
        };

        // Trace 2b: Corrected Data (Weekly Profile)
        const traceCorrDiurnal = {
            x: times,
            y: corr_wl_diurnal,
            type: 'scatter',
            mode: 'lines',
            name: 'C++ Corrected (Weekly Profile)',
            line: { color: '#f59e0b', width: 1.5 }
        };

        // Trace 2c: Corrected Data (Weekly Harmonic Fit)
        const traceCorrHarmonic = {
            x: times,
            y: corr_wl_harmonic,
            type: 'scatter',
            mode: 'lines',
            name: 'C++ Corrected (Weekly Harmonic Fit)',
            line: { color: '#8b5cf6', width: 1.5 }
        };

        // Trace 3: Anomalies Scatter
        const traceAnom = {
            x: anomTimes,
            y: anomValues,
            type: 'scatter',
            mode: 'markers',
            name: 'C++ Flagged Anomalies',
            marker: { color: '#ef4444', size: 6, symbol: 'x' }
        };

        const data = [traceRaw, traceCorrAr, traceCorrDiurnal, traceCorrHarmonic, traceAnom];

        const layout = {
            plot_bgcolor: '#0f172a',
            paper_bgcolor: '#0f172a',
            xaxis: {
                title: { text: 'Timestamp', font: { color: '#94a3b8', size: 12 } },
                gridcolor: '#1e293b',
                tickcolor: '#1e293b',
                tickfont: { color: '#64748b' }
            },
            yaxis: {
                title: { text: 'Water Level / Distance (m)', font: { color: '#94a3b8', size: 12 } },
                gridcolor: '#1e293b',
                tickcolor: '#1e293b',
                tickfont: { color: '#64748b' }
            },
            legend: {
                font: { color: '#94a3b8', size: 11 },
                orientation: 'h',
                y: 1.1,
                x: 0.5,
                xanchor: 'center'
            },
            margin: { l: 60, r: 40, t: 40, b: 60 },
            hovermode: 'closest'
        };

        const config = { responsive: true, scrollZoom: true };
        Plotly.newPlot('chart', data, layout, config);

        // Visibility toggle helper
        function updateVisibility(index, visible) {
            Plotly.restyle('chart', { visible: visible ? true : 'legendonly' }, [index]);
        }

        // Keep HTML checkboxes in sync with Plotly legend clicks
        const chartDiv = document.getElementById('chart');
        chartDiv.on('plotly_restyle', function(data) {
            if (data && data[0] && 'visible' in data[0] && data[1]) {
                const visibleVals = data[0].visible;
                const indices = data[1];
                for (let i = 0; i < indices.length; i++) {
                    const idx = indices[i];
                    const vis = Array.isArray(visibleVals) ? visibleVals[i] : visibleVals;
                    const checkboxId = getCheckboxIdForIndex(idx);
                    if (checkboxId) {
                        const cb = document.getElementById(checkboxId);
                        if (cb) {
                            cb.checked = (vis === true || vis === 'true');
                        }
                    }
                }
            }
        });

        function getCheckboxIdForIndex(index) {
            switch(index) {
                case 0: return 'toggle-raw';
                case 1: return 'toggle-ar';
                case 2: return 'toggle-diurnal';
                case 3: return 'toggle-harmonic';
                case 4: return 'toggle-anom';
                default: return null;
            }
        }
    </script>
</body>
</html>
)html";

    out.close();
    std::cout << "Dashboard generated successfully! Opening dashboard in browser..." << std::endl;
    
    // Launch browser on Windows
    std::system("start plots\\task6\\cpp_interactive_dashboard.html");
    
    return 0;
}
