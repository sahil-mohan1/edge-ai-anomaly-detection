import json

with open('c:\\Users\\sahil\\Desktop\\ICFOSS\\Anomaly Detection\\scripts\\filters\\task5_filter_testing.ipynb', 'r', encoding='utf-8') as f:
    data = json.load(f)

new_metrics = [
    'def metrics(pred_series, df_raw, gt):\n',
    '    """RMSE, MAE, MaxErr vs ground truth aligned on common timestamps, EVALUATED ONLY ON ANOMALIES."""\n',
    '    df_p   = pd.DataFrame({\'Time\': df_raw[\'Time\'], \'pred\': pred_series.values, \'raw\': df_raw[\'WL_raw\']})\n',
    '    merged = pd.merge(df_p,\n',
    '                      gt[[\'Time\', \'Water Level\']].rename(columns={\'Water Level\': \'truth\'}),\n',
    '                      on=\'Time\', how=\'inner\').dropna(subset=[\'pred\', \'truth\'])\n',
    '    \n',
    '    # Isolate anomalies: where raw data differs from ground truth (or is NaN)\n',
    '    anomaly_mask = merged[\'raw\'].isna() | ((merged[\'raw\'] - merged[\'truth\']).abs() > 0.001)\n',
    '    merged = merged[anomaly_mask]\n',
    '    \n',
    '    if merged.empty:\n',
    '        return dict(RMSE=float(\'nan\'), MAE=float(\'nan\'), MaxErr=float(\'nan\'), N=0)\n',
    '    err = merged[\'pred\'] - merged[\'truth\']\n',
    '    return dict(RMSE=float((err**2).mean()**0.5),\n',
    '                MAE=float(err.abs().mean()),\n',
    '                MaxErr=float(err.abs().max()),\n',
    '                N=len(merged))\n'
]

for cell in data['cells']:
    if cell['cell_type'] == 'code':
        source = cell['source']
        if any('def metrics(' in line for line in source):
            start_idx = -1
            end_idx = -1
            for i, line in enumerate(source):
                if line.startswith('def metrics('):
                    start_idx = i
                elif start_idx != -1 and line.startswith('def plot_filter('):
                    end_idx = i
                    break
            
            if start_idx != -1 and end_idx != -1:
                new_source = source[:start_idx] + new_metrics + ['\n', '\n'] + source[end_idx:]
                cell['source'] = new_source

with open('c:\\Users\\sahil\\Desktop\\ICFOSS\\Anomaly Detection\\scripts\\filters\\task5_filter_testing.ipynb', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=1)
