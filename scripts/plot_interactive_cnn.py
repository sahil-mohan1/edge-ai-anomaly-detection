import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.cnn_corrector import CNNCorrector

def main():
    processed_dir = 'data/processed'
    csv_files = [f for f in os.listdir(processed_dir) if f.endswith('.csv')]
    
    if not csv_files:
        print("No CSV files found in data/processed/")
        return
        
    print("Available datasets:")
    for i, f in enumerate(csv_files):
        print(f"[{i+1}] {f}")
        
    while True:
        try:
            choice = input(f"Select a dataset (1-{len(csv_files)}): ")
            idx = int(choice) - 1
            if 0 <= idx < len(csv_files):
                selected_file = csv_files[idx]
                break
            else:
                print("Invalid selection. Try again.")
        except ValueError:
            print("Please enter a number.")
            
    data_path = os.path.join(processed_dir, selected_file)
    print(f"\nLoading data and model for {selected_file}...")
    df = pd.read_csv(data_path)
    # Parse timestamps to handle time gaps properly
    df['Parsed_Time'] = pd.to_datetime(df['Time'], format='mixed', dayfirst=True)
    
    corrector = CNNCorrector(model_path='models/saved/water_level_cnn.tflite')
    
    print(f"Simulating CNN correction with Zero-Padding Latent Interpolation on {len(df)} samples...")
    
    results = []
    
    # We will process all rows
    for i, row in df.iterrows():
        raw_val = row['Water Level']
        ec = row['errorcode']
        current_time = row['Parsed_Time']
        
        step_results = corrector.process(current_time, ec, raw_val)
        results.extend(step_results)
        
    print("Building dataframe from results...")
    # Build dataframe for plotting
    plot_data = []
    for r in results:
        plot_data.append({
            'Time': r.timestamp,
            'Water Level': r.original_value,
            'CNN_Pred': r.cnn_pred,
            'Corrected': r.corrected_value,
            'Is_Anomaly': r.is_anomaly,
            'Is_Interpolated': r.correction_src == 'zero_padding_interpolation'
        })
        
    df_plot = pd.DataFrame(plot_data)
    
    print("Building interactive plot...")
    fig = go.Figure()
    
    # Raw values (shows spikes/drops)
    fig.add_trace(go.Scatter(
        x=df_plot['Time'], 
        y=df_plot['Water Level'], 
        mode='lines', 
        name='Raw Sensor Data',
        line=dict(color='rgba(255, 255, 255, 0.4)')
        # Removed hoverinfo='skip' so it shows up in tooltip
    ))
    
    # CNN Predictions
    fig.add_trace(go.Scatter(
        x=df_plot['Time'], 
        y=df_plot['CNN_Pred'], 
        mode='lines', 
        name='1D-CNN Prediction',
        line=dict(color='rgba(0, 114, 178, 0.9)', width=2)
    ))
    
    # Final Corrected output
    fig.add_trace(go.Scatter(
        x=df_plot['Time'], 
        y=df_plot['Corrected'], 
        mode='lines', 
        name='Final Corrected Output',
        line=dict(color='rgba(0, 158, 115, 0.9)', width=1, dash='dot')
    ))
    
    # Markers for true anomalies
    anomalies = df_plot[(df_plot['Is_Anomaly'] == True) & (df_plot['Is_Interpolated'] == False)]
    fig.add_trace(go.Scatter(
        x=anomalies['Time'], 
        y=anomalies['Water Level'], 
        mode='markers', 
        name='Detected Anomalies (Static 0.5m Limit)',
        marker=dict(color='red', size=8, symbol='x')
    ))
    
    # Markers for interpolated gaps
    interpolated = df_plot[df_plot['Is_Interpolated'] == True]
    if len(interpolated) > 0:
        fig.add_trace(go.Scatter(
            x=interpolated['Time'], 
            y=interpolated['Corrected'], 
            mode='markers', 
            name='Zero-Padded Interpolations',
            marker=dict(color='orange', size=6, symbol='circle')
        ))
    
    fig.update_layout(
        title='CNN with Zero-Padding Latent Interpolation & Static Limit',
        xaxis_title='Timestamp',
        yaxis_title='Water Level (m)',
        hovermode='x unified',
        template='plotly_dark'
    )
    
    base_name = os.path.splitext(selected_file)[0]
    out_path = f'plots/interactive_cnn_zero_padding_{base_name}.html'
    os.makedirs('plots', exist_ok=True)
    fig.write_html(out_path)
    print(f"Saved interactive HTML plot to {out_path}")
    print("Stats:", corrector.stats)

if __name__ == "__main__":
    main()
