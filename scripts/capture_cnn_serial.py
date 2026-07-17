import serial
import serial.tools.list_ports
import time
import os
import sys
import threading
import queue
import webbrowser
import json
import argparse
import pandas as pd
import numpy as np
from flask import Flask, Response, render_template_string, jsonify, request

app = Flask(__name__)

# Global variables and paths
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
csv_path = os.path.join(base_dir, 'data', 'processed', 'data-may26-june18_processed.csv')
output_path = os.path.join(base_dir, 'cnn_model_raw_output.txt')

# Global simulation/serial state
g_state = {
    "port": "COM7",
    "baud": 115200,
    "status": "Disconnected",
    "total_samples": 0,
    "anomalies_detected": 0,
    "current_raw": 0.0,
    "current_corrected": 0.0,
    "is_complete": False,
    "total_expected": 2066
}

data_points = []
raw_records = []
sse_clients = []
g_lock = threading.Lock()
ser = None
serial_thread = None
stop_event = threading.Event()
df_gt = pd.DataFrame()
client_connected_event = threading.Event()

# Load Ground Truth
try:
    print(f"Loading Ground Truth from {csv_path}...")
    if os.path.exists(csv_path):
        df_gt = pd.read_csv(csv_path)
        if 'Time' in df_gt.columns:
            df_gt['Time_datetime'] = pd.to_datetime(df_gt['Time'], errors='coerce', dayfirst=True)
        else:
            df_gt['Time_datetime'] = pd.date_range(start='2026-05-26', periods=len(df_gt), freq='15min')
        df_gt['wl_clean'] = df_gt['Water Level'].replace(-1.0, np.nan)
        g_state["total_expected"] = len(df_gt)
        print(f"Loaded {len(df_gt)} Ground Truth points.")
    else:
        print(f"Warning: {csv_path} not found. Running without Ground Truth alignment.")
except Exception as e:
    print(f"Warning: Could not load ground truth CSV: {e}")

def find_esp32_port():
    ports = list(serial.tools.list_ports.comports())
    # Try typical chip descriptions
    for p in ports:
        desc = p.description.lower()
        if "cp210" in desc or "ch340" in desc or "silicon labs" in desc or "usb-to-uart" in desc:
            return p.device
    # Fallback to first port
    if ports:
        return ports[0].device
    return "COM7"

def broadcast_event(event_type, data):
    msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    with g_lock:
        dead = []
        for q in sse_clients:
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.append(q)
        for q in dead:
            if q in sse_clients:
                sse_clients.remove(q)

def read_serial_loop():
    global ser, raw_records, data_points
    
    # Try requested port first. If it fails and is COM7, try autodetecting
    port_to_try = g_state["port"]
    print(f"Connecting to serial port {port_to_try} at {g_state['baud']}...")
    g_state["status"] = "Connecting"
    broadcast_event("status_change", {"status": "Connecting", "port": port_to_try})
    
    try:
        ser = serial.Serial(port_to_try, g_state["baud"], timeout=2)
    except serial.SerialException as e:
        print(f"Failed to open port {port_to_try}: {e}")
        detected_port = find_esp32_port()
        if detected_port != port_to_try:
            print(f"Attempting autodetected ESP32 port: {detected_port}...")
            port_to_try = detected_port
            g_state["port"] = detected_port
            broadcast_event("status_change", {"status": "Connecting", "port": port_to_try})
            try:
                ser = serial.Serial(port_to_try, g_state["baud"], timeout=2)
            except serial.SerialException as ex:
                g_state["status"] = "Connection Failed"
                broadcast_event("status_change", {"status": "Connection Failed", "error": str(ex), "port": port_to_try})
                print(f"Failed to open autodetected port {port_to_try}: {ex}")
                return
        else:
            g_state["status"] = "Connection Failed"
            broadcast_event("status_change", {"status": "Connection Failed", "error": str(e), "port": port_to_try})
            return

    g_state["status"] = "Connected"
    broadcast_event("status_change", {"status": "Connected", "port": port_to_try})

    print("Waiting for browser to connect to stream before resetting ESP32...")
    client_connected_event.wait()

    # Trigger ESP32 reset
    print("Resetting ESP32 via DTR/RTS...")
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.25)
    ser.setDTR(True)
    ser.setRTS(False)
    time.sleep(0.5)
    ser.reset_input_buffer()

    started = False
    data_index = 0
    
    with g_lock:
        raw_records.clear()
        data_points.clear()
        g_state["total_samples"] = 0
        g_state["anomalies_detected"] = 0
        g_state["is_complete"] = False

    broadcast_event("reset", {"total": g_state["total_expected"]})

    last_data_time = time.time()

    while not stop_event.is_set():
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if not line:
                # Heartbeat check/warning if serial is silent for too long
                if started and not g_state["is_complete"] and time.time() - last_data_time > 8:
                    print("Warning: No serial data received for 8 seconds. ESP32 may be halted.")
                    last_data_time = time.time()
                continue

            last_data_time = time.time()
            
            if "Starting ESP32" in line or "Setup complete" in line:
                started = True
                g_state["status"] = "Streaming"
                broadcast_event("status_change", {"status": "Streaming", "port": port_to_try})
                print("Setup detected. ESP32 is transmitting...")
                continue
                
            if "DATASET_COMPLETE" in line:
                g_state["is_complete"] = True
                g_state["status"] = "Completed"
                broadcast_event("status_change", {"status": "Completed", "port": port_to_try})
                print("DATASET_COMPLETE detected!")
                
                # Save captured data in same UTF-16 format as before
                with g_lock:
                    if len(raw_records) > 0:
                        print(f"Saving {len(raw_records)} records to {output_path}...")
                        with open(output_path, 'w', encoding='utf-16') as f:
                            f.writelines(raw_records)
                        print("File saved successfully.")
                break
                
            is_valid_data = False
            rw, cw, ec = 0.0, 0.0, 0.0

            if line.startswith("Raw_WaterLevel:"):
                parts = line.split(',')
                if len(parts) >= 3:
                    try:
                        rw = float(parts[0].split(':')[1])
                        cw = float(parts[1].split(':')[1])
                        ec = float(parts[2].split(':')[1])
                        is_valid_data = True
                    except Exception as parse_ex:
                        print(f"Parsing error: {parse_ex} for line: {line}")
            elif line.startswith("R:"):
                parts = line.split(',')
                if len(parts) >= 3:
                    try:
                        rw = float(parts[0].split(':')[1])
                        cw = float(parts[1].split(':')[1])
                        ec = float(parts[2].split(':')[1])
                        # Expand back to original long format for file logging compatibility
                        line = f"Raw_WaterLevel:{rw},Corrected_WaterLevel:{cw},Anomaly_Trigger:{ec:.2f}"
                        is_valid_data = True
                    except Exception as parse_ex:
                        print(f"Parsing error: {parse_ex} for line: {line}")

            if is_valid_data:
                try:
                    with g_lock:
                        raw_records.append(line + "\n")
                    
                    # Match with Ground Truth row
                    timestamp = str(data_index)
                    gt_val = None
                    if not df_gt.empty and data_index < len(df_gt):
                        row = df_gt.iloc[data_index]
                        timestamp = row['Time_datetime'].isoformat() if hasattr(row['Time_datetime'], 'isoformat') else str(row['Time_datetime'])
                        if not pd.isna(row['wl_clean']):
                            gt_val = float(row['wl_clean'])
                    
                    is_anom = (ec >= 1.0) # Anomaly Trigger is 3.0f, normal is 0.0f
                    
                    with g_lock:
                        g_state["total_samples"] += 1
                        if is_anom:
                            g_state["anomalies_detected"] += 1
                        g_state["current_raw"] = rw
                        g_state["current_corrected"] = cw
                        
                        point = {
                            "index": data_index,
                            "timestamp": timestamp,
                            "raw": rw,
                            "corrected": cw,
                            "anomaly": is_anom,
                            "gt": gt_val
                        }
                        data_points.append(point)
                        
                    broadcast_event("data", point)
                    data_index += 1
                except Exception as ex:
                    print(f"Processing error: {ex}")
                        
        except Exception as e:
            print(f"Error in serial read thread: {e}")
            g_state["status"] = "Error"
            broadcast_event("status_change", {"status": "Error", "error": str(e), "port": port_to_try})
            break

    try:
        ser.close()
        print("Closed serial port.")
    except:
        pass

@app.route('/')
def index():
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESP32 CNN Anomaly Detector Live Stream</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-color: #0b0f19;
            --card-bg: rgba(22, 30, 49, 0.7);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --color-raw: #f97316;
            --color-corrected: #3b82f6;
            --color-gt: #10b981;
            --color-anomaly: #ef4444;
        }

        body {
            margin: 0;
            padding: 0;
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        header {
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-color);
            padding: 1.25rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 10;
        }

        .header-title h1 {
            font-size: 1.3rem;
            margin: 0;
            font-weight: 700;
            background: linear-gradient(135deg, var(--color-corrected), #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.025em;
        }

        .header-title p {
            margin: 0.25rem 0 0 0;
            font-size: 0.85rem;
            color: var(--text-muted);
        }

        .header-controls {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .status-badge {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(255, 255, 255, 0.04);
            padding: 0.5rem 1rem;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 500;
            border: 1px solid var(--border-color);
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #9ca3af;
            transition: background-color 0.3s ease;
        }

        .status-dot.pulsing {
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.5); }
            70% { transform: scale(1.1); box-shadow: 0 0 0 8px rgba(59, 130, 246, 0); }
            100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
        }

        .main-container {
            max-width: 1400px;
            width: 100%;
            margin: 0 auto;
            padding: 2rem;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            flex-grow: 1;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.25rem;
        }

        .stat-card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            position: relative;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        }

        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: transparent;
        }

        .stat-card.raw::before { background: var(--color-raw); }
        .stat-card.corrected::before { background: var(--color-corrected); }
        .stat-card.anomalies::before { background: var(--color-anomaly); }
        .stat-card.progress-stat::before { background: #8b5cf6; }

        .stat-label {
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            color: var(--text-muted);
            letter-spacing: 0.05em;
        }

        .stat-value {
            font-size: 1.8rem;
            font-weight: 700;
            margin-top: 0.5rem;
            font-family: 'JetBrains Mono', monospace;
        }

        .stat-value.raw { color: var(--color-raw); }
        .stat-value.corrected { color: var(--color-corrected); }
        .stat-value.anomalies { color: var(--color-anomaly); }
        .stat-value.progress-val { color: #c084fc; }

        .stat-meta {
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 0.25rem;
        }

        .chart-card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
            flex-grow: 1;
            min-height: 520px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
        }

        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .chart-title {
            font-size: 1.05rem;
            font-weight: 600;
            letter-spacing: -0.01em;
        }

        .chart-controls {
            display: flex;
            gap: 0.75rem;
        }

        .btn {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 0.5rem 1.1rem;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .btn:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(255, 255, 255, 0.2);
            transform: translateY(-1px);
        }

        .btn:active {
            transform: translateY(0);
        }

        .btn.primary {
            background: var(--color-corrected);
            border-color: var(--color-corrected);
        }

        .btn.primary:hover {
            background: #2563eb;
            border-color: #2563eb;
            box-shadow: 0 0 14px rgba(59, 130, 246, 0.45);
        }

        .chart-wrapper {
            position: relative;
            flex-grow: 1;
            width: 100%;
            height: 420px;
        }

        .progress-bar-container {
            width: 100%;
            height: 6px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 3px;
            overflow: hidden;
            margin-top: 0.5rem;
        }

        .progress-bar {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, var(--color-corrected), #8b5cf6);
            transition: width 0.1s ease;
        }

        .toast {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: rgba(16, 185, 129, 0.95);
            color: #ffffff;
            padding: 0.85rem 1.5rem;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 500;
            box-shadow: 0 10px 25px rgba(0,0,0,0.3);
            display: flex;
            align-items: center;
            gap: 0.75rem;
            transform: translateY(150%);
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            z-index: 100;
        }

        .toast.show {
            transform: translateY(0);
        }
    </style>
</head>
<body>
    <header>
        <div class="header-title">
            <h1>ESP32 Pure CNN Anomaly Detector</h1>
            <p>Live Serial Capture & Calibration Output</p>
        </div>
        <div class="header-controls">
            <button class="btn" id="btnRestart">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                Reset ESP32
            </button>
            <div class="status-badge">
                <div class="status-dot" id="statusDot"></div>
                <span id="statusText">Disconnected</span>
            </div>
        </div>
    </header>

    <div class="main-container">
        <div class="stats-grid">
            <div class="stat-card raw">
                <span class="stat-label">Raw Water Level</span>
                <span class="stat-value raw" id="valRaw">-</span>
                <span class="stat-meta">Meter reading from ESP32</span>
            </div>
            <div class="stat-card corrected">
                <span class="stat-label">Corrected Water Level</span>
                <span class="stat-value corrected" id="valCorrected">-</span>
                <span class="stat-meta">1D CNN output + Diurnal fallback</span>
            </div>
            <div class="stat-card anomalies">
                <span class="stat-label">Anomalies Detected</span>
                <span class="stat-value anomalies" id="valAnomalies">0</span>
                <span class="stat-meta" id="valAnomRate">Rate: 0.0%</span>
            </div>
            <div class="stat-card progress-stat">
                <span class="stat-label">Inference Progress</span>
                <span class="stat-value progress-val" id="valProgress">0 / 2066</span>
                <div class="progress-bar-container">
                    <div class="progress-bar" id="progressBar"></div>
                </div>
            </div>
        </div>

        <div class="chart-card">
            <div class="chart-header">
                <span class="chart-title">Real-time Inference Series</span>
                <div class="chart-controls">
                    <button class="btn btn-toggle" data-dataset="0">Toggle Corrected</button>
                    <button class="btn btn-toggle" data-dataset="1">Toggle Raw</button>
                    <button class="btn btn-toggle" data-dataset="2">Toggle GT</button>
                </div>
            </div>
            <div class="chart-wrapper">
                <canvas id="liveChart"></canvas>
            </div>
        </div>
    </div>

    <div class="toast" id="toast">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
        <span id="toastText">File saved successfully!</span>
    </div>

    <script>
        const ctx = document.getElementById('liveChart').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Corrected Water Level',
                        data: [],
                        borderColor: '#3b82f6',
                        borderWidth: 2.2,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: 'Raw Water Level',
                        data: [],
                        borderColor: 'rgba(249, 115, 22, 0.55)',
                        borderWidth: 1.2,
                        borderDash: [3, 3],
                        pointRadius: 0,
                        pointHoverRadius: 3,
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: 'Ground Truth',
                        data: [],
                        borderColor: '#10b981',
                        borderWidth: 1.5,
                        pointRadius: 0,
                        pointHoverRadius: 3,
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: 'Detected Anomaly',
                        data: [],
                        borderColor: '#ef4444',
                        backgroundColor: '#ef4444',
                        pointStyle: 'rectRot',
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        showLine: false,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'category',
                        grid: { color: 'rgba(255, 255, 255, 0.04)' },
                        ticks: { color: '#94a3b8', font: { size: 9 }, maxTicksLimit: 20 }
                    },
                    y: {
                        min: -0.1,
                        max: 4.6,
                        grid: { color: 'rgba(255, 255, 255, 0.04)' },
                        ticks: { color: '#94a3b8', font: { size: 10 } }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        labels: { color: '#f1f5f9', font: { family: 'Inter', size: 11 } }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: '#1e293b',
                        titleColor: '#f1f5f9',
                        bodyColor: '#cbd5e1',
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderWidth: 1
                    }
                }
            }
        });

        // Toggle datasets via custom buttons
        document.querySelectorAll('.btn-toggle').forEach(btn => {
            btn.addEventListener('click', function() {
                const dsIndex = parseInt(this.getAttribute('data-dataset'));
                const meta = chart.getDatasetMeta(dsIndex);
                meta.hidden = meta.hidden === null ? !chart.data.datasets[dsIndex].hidden : null;
                this.style.opacity = (meta.hidden) ? '0.5' : '1';
                chart.update('none');
            });
        });

        // Toast Helper
        function showToast(message) {
            const toast = document.getElementById('toast');
            document.getElementById('toastText').textContent = message;
            toast.classList.add('show');
            setTimeout(() => {
                toast.classList.remove('show');
            }, 4000);
        }

        // Live stream SSE Client
        let eventSource = null;
        let expectedTotal = 2066;

        function connectSSE() {
            if (eventSource) {
                eventSource.close();
            }

            eventSource = new EventSource('/stream');

            eventSource.addEventListener('reset', (e) => {
                const data = JSON.parse(e.data);
                expectedTotal = data.total;
                
                chart.data.labels = [];
                chart.data.datasets.forEach(ds => ds.data = []);
                chart.update('none');

                document.getElementById('valRaw').textContent = '-';
                document.getElementById('valCorrected').textContent = '-';
                document.getElementById('valAnomalies').textContent = '0';
                document.getElementById('valAnomRate').textContent = 'Rate: 0.0%';
                document.getElementById('valProgress').textContent = `0 / ${expectedTotal}`;
                document.getElementById('progressBar').style.width = '0%';
            });

            eventSource.addEventListener('status_change', (e) => {
                const data = JSON.parse(e.data);
                const dot = document.getElementById('statusDot');
                const text = document.getElementById('statusText');
                
                text.textContent = data.status + (data.port ? ` (${data.port})` : '');
                
                dot.className = "status-dot";
                if (data.status === "Connecting" || data.status === "Streaming") {
                    dot.className = "status-dot pulsing";
                    dot.style.backgroundColor = (data.status === "Connecting") ? "#eab308" : "#10b981";
                } else if (data.status === "Connected") {
                    dot.className = "status-dot";
                    dot.style.backgroundColor = "#10b981";
                } else if (data.status === "Completed") {
                    dot.className = "status-dot";
                    dot.style.backgroundColor = "#10b981";
                    showToast("Capture complete! Output saved to cnn_model_raw_output.txt");
                } else if (data.status === "Connection Failed" || data.status === "Error") {
                    dot.style.backgroundColor = "#ef4444";
                    showToast("Serial error: " + (data.error || "Connection failed. Check USB device."));
                } else {
                    dot.style.backgroundColor = "#9ca3af";
                }
            });

            eventSource.addEventListener('data', (e) => {
                const point = JSON.parse(e.data);
                
                // Update digital readouts
                document.getElementById('valRaw').textContent = point.raw.toFixed(2) + ' m';
                document.getElementById('valCorrected').textContent = point.corrected.toFixed(2) + ' m';
                
                // Add to chart labels
                chart.data.labels.push(point.timestamp);
                
                // Push data to datasets
                chart.data.datasets[0].data.push(point.corrected);
                chart.data.datasets[1].data.push(point.raw);
                chart.data.datasets[2].data.push(point.gt);
                
                // If anomaly triggered, plot in detected anomaly dataset, else null
                chart.data.datasets[3].data.push(point.anomaly ? point.raw : null);
                
                // Update stats and progress bar
                const currentCount = point.index + 1;
                document.getElementById('valProgress').textContent = `${currentCount} / ${expectedTotal}`;
                
                const percent = Math.min(100, (currentCount / expectedTotal) * 100);
                document.getElementById('progressBar').style.width = `${percent}%`;

                // Calculate anomalies stats
                let totalAnom = 0;
                chart.data.datasets[3].data.forEach(val => {
                    if (val !== null) totalAnom++;
                });
                
                document.getElementById('valAnomalies').textContent = totalAnom;
                const rate = ((totalAnom / currentCount) * 100).toFixed(1);
                document.getElementById('valAnomRate').textContent = `Rate: ${rate}%`;

                chart.update('none');
            });

            eventSource.onerror = (e) => {
                console.error("SSE stream error, reconnecting...", e);
            };
        }

        document.getElementById('btnRestart').addEventListener('click', function() {
            this.disabled = true;
            fetch('/restart', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    console.log(data.message);
                    setTimeout(() => { this.disabled = false; }, 1000);
                })
                .catch(err => {
                    console.error("Error resetting ESP32:", err);
                    this.disabled = false;
                });
        });

        // Initialize connection
        connectSSE();
    </script>
</body>
</html>
    """)

@app.route('/stream')
def stream_data():
    def event_stream():
        q = queue.Queue(maxsize=100)
        with g_lock:
            sse_clients.append(q)
            client_connected_event.set()
            
        # Send initial reset/sizing
        yield f"event: reset\ndata: {json.dumps({'total': g_state['total_expected']})}\n\n"
        # Send current status
        yield f"event: status_change\ndata: {json.dumps({'status': g_state['status'], 'port': g_state['port']})}\n\n"
        
        with g_lock:
            for p in data_points:
                yield f"event: data\ndata: {json.dumps(p)}\n\n"
                
        while True:
            try:
                msg = q.get(timeout=15) # Heartbeat timeout
                yield msg
            except queue.Empty:
                yield ": heartbeat\n\n"
            except GeneratorExit:
                with g_lock:
                    if q in sse_clients:
                        sse_clients.remove(q)
                break
                
    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/restart', methods=['POST'])
def restart_simulation():
    global serial_thread, stop_event
    
    print("User requested ESP32 reset via web dashboard.")
    stop_event.set()
    if serial_thread and serial_thread.is_alive():
        serial_thread.join(timeout=3)
        
    stop_event.clear()
    serial_thread = threading.Thread(target=read_serial_loop, daemon=True)
    serial_thread.start()
    
    return jsonify({"status": "success", "message": "Simulation restarted"})

def main():
    global serial_thread, stop_event
    
    parser = argparse.ArgumentParser(description="Live ESP32 CNN Serial Plotter")
    parser.add_argument("--port", default="COM7", help="Serial port (default: COM7)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--webport", type=int, default=5055, help="Web dashboard port (default: 5055)")
    args = parser.parse_args()
    
    g_state["port"] = args.port
    g_state["baud"] = args.baud
    
    # Start serial reading thread
    stop_event.clear()
    serial_thread = threading.Thread(target=read_serial_loop, daemon=True)
    serial_thread.start()
    
    # Open browser window
    webport = args.webport
    url = f"http://127.0.0.1:{webport}"
    print(f"Opening browser at {url}...")
    
    # Tiny delay before browser open to let Flask warm up
    def open_browser():
        time.sleep(1.0)
        webbrowser.open_new_tab(url)
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run Flask server (disable logging to keep stdout clean for serial logs)
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    try:
        app.run(host="127.0.0.1", port=webport, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("Shutting down live plotter...")
    finally:
        stop_event.set()
        if serial_thread and serial_thread.is_alive():
            serial_thread.join(timeout=1)

if __name__ == '__main__':
    main()
