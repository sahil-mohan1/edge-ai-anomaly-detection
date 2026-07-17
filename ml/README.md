# ml

Python / ML pipeline for water-level anomaly detection.

## Structure

```
ml/
├── data/
│   ├── raw/             # Raw sensor CSV exports
│   └── processed/       # Cleaned, feature-engineered datasets
├── models/
│   ├── saved/           # Trained .keras / .tflite model files
│   ├── archive/         # Older model experiments
│   ├── cnn_corrector.py
│   ├── feature_engineering.py
│   └── model_store.py
├── scripts/
│   ├── dataset_analysis/   # EDA scripts
│   ├── dataset_building/   # Preprocessing & dataset generation
│   ├── model_training/     # Training scripts (MLP, WaveNet, CNN)
│   ├── embedded_exports/   # Export trained weights → C headers
│   ├── filters/            # Task 5 filter experiments
│   └── *.py / *.exe        # Evaluation & real-time test runners
├── notebooks/           # Jupyter notebooks
├── plots/               # Generated plots & HTML reports
├── pi_deployment/       # Raspberry Pi deployment scripts
└── run_pipeline.py      # Main end-to-end pipeline entry point
```

## Quick Start

```bash
pip install -r ml/pi_deployment/requirements.txt
python ml/run_pipeline.py
```

## Generating embedded exports

After training, run the export scripts to regenerate C headers for the firmware:

```bash
python ml/scripts/embedded_exports/convert_tflite_to_c.py
python ml/scripts/embedded_exports/generate_test_harness.py
```

Outputs land in `firmware/embedded_exports/`.
