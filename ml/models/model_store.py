"""
model_store.py
--------------
Handles saving and loading the trained HybridCorrector state to/from disk.

River models (SNARIMAX, ARFRegressor) are fully picklable, so we use
Python's standard `pickle` module to serialise the entire corrector object.

Saved files (in models/saved/)
--------------------------------
  hybrid_corrector.pkl   - the full HybridCorrector instance
                           (includes SNARIMAX, ARFR, FeatureEngineer buffers,
                            and running statistics)
  metadata.json          - human-readable training metadata (timestamp,
                           last processed row timestamp, rows seen, etc.)

Usage
-----
  from models.model_store import save_model, load_model, get_last_timestamp

  # After training:
  save_model(corrector, last_timestamp=df['_ts'].iloc[-1])

  # On next run (resume from checkpoint):
  corrector      = load_model()          # returns None if no saved model found
  last_ts        = get_last_timestamp()  # returns None if no saved model found
  new_df         = df[df['_ts'] > last_ts]   # only process NEW rows
"""

import json
import os
import pickle
from datetime import datetime, timezone
from pathlib import Path

# Default directory to store saved model files (inside models/saved/)
_DEFAULT_SAVE_DIR = Path(__file__).parent / "saved"
_MODEL_FILENAME   = "hybrid_corrector.pkl"
_META_FILENAME    = "metadata.json"


def save_model(corrector, save_dir=None, last_timestamp=None) -> str:
    """
    Serialise and save a trained HybridCorrector to disk.

    Parameters
    ----------
    corrector      : HybridCorrector - the trained corrector instance.
    save_dir       : directory to save into. Defaults to models/saved/.
    last_timestamp : the timestamp of the last row processed (datetime or str).
                     Stored in metadata so the pipeline knows where to resume.

    Returns
    -------
    str - absolute path of the saved .pkl file.
    """
    save_dir = Path(save_dir) if save_dir else _DEFAULT_SAVE_DIR
    save_dir.mkdir(parents=True, exist_ok=True)

    model_path = save_dir / _MODEL_FILENAME
    meta_path  = save_dir / _META_FILENAME

    # ---- Save model via pickle ----
    with open(model_path, "wb") as f:
        pickle.dump(corrector, f, protocol=pickle.HIGHEST_PROTOCOL)

    # ---- Serialise last_timestamp ----
    if last_timestamp is not None and hasattr(last_timestamp, "isoformat"):
        last_ts_str = last_timestamp.isoformat()
    elif last_timestamp is not None:
        last_ts_str = str(last_timestamp)
    else:
        last_ts_str = None

    # ---- Save human-readable metadata ----
    stats = corrector.stats
    meta = {
        "saved_at":            datetime.now(timezone.utc).isoformat(),
        "last_timestamp":      last_ts_str,
        "rows_processed":      stats["total"],
        "anomalies_corrected": stats["corrected"],
        "correction_rate_pct": round(
            stats["corrected"] / stats["total"] * 100 if stats["total"] else 0, 2
        ),
        "breakdown": {
            "ec1_abort":        stats["ec_abort"],
            "ec2_timeout":      stats["ec_timeout"],
            "ec3_spike":        stats["ec_spike"],
            "ec4_limit_fault":  stats["ec_limit_fault"],
            "ec4_limit_real":   stats["ec_limit_real"],
            "ec5_unstable_bad": stats["ec_unstable_bad"],
            "ec5_unstable_ok":  stats["ec_unstable_ok"],
        },
        "snarimax_trained":  corrector.snarimax.is_trained,
        "arfr_samples_seen": corrector.arfr.n_trained,
        "model_file":        str(model_path),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"  Model saved -> '{model_path}'")
    print(f"  Metadata    -> '{meta_path}'")
    return str(model_path)


def load_model(save_dir=None):
    """
    Load a previously saved HybridCorrector from disk.

    Returns
    -------
    HybridCorrector - the restored corrector (ready to continue learning),
                      or None if no saved model is found.
    """
    save_dir   = Path(save_dir) if save_dir else _DEFAULT_SAVE_DIR
    model_path = save_dir / _MODEL_FILENAME
    meta_path  = save_dir / _META_FILENAME

    if not model_path.exists():
        return None

    with open(model_path, "rb") as f:
        corrector = pickle.load(f)

    if meta_path.exists():
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        print(f"  Loaded model saved at : {meta.get('saved_at', 'unknown')}")
        print(f"  Last data timestamp   : {meta.get('last_timestamp', 'unknown')}")
        print(f"  Rows previously seen  : {meta.get('rows_processed', '?'):,}")
        print(f"  ARFR samples trained  : {meta.get('arfr_samples_seen', '?'):,}")
    else:
        print(f"  Loaded model from '{model_path}'")

    return corrector


def get_last_timestamp(save_dir=None):
    """
    Return the last processed timestamp from metadata, as a pandas Timestamp.
    Returns None if no saved metadata exists or last_timestamp is not set.
    """
    import pandas as pd
    save_dir  = Path(save_dir) if save_dir else _DEFAULT_SAVE_DIR
    meta_path = save_dir / _META_FILENAME

    if not meta_path.exists():
        return None

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    ts_str = meta.get("last_timestamp")
    if ts_str is None:
        return None

    return pd.Timestamp(ts_str)


def model_exists(save_dir=None) -> bool:
    """Return True if a saved model file exists."""
    save_dir = Path(save_dir) if save_dir else _DEFAULT_SAVE_DIR
    return (save_dir / _MODEL_FILENAME).exists()


def delete_model(save_dir=None) -> None:
    """Delete saved model and metadata files (force full retrain)."""
    save_dir   = Path(save_dir) if save_dir else _DEFAULT_SAVE_DIR
    model_path = save_dir / _MODEL_FILENAME
    meta_path  = save_dir / _META_FILENAME
    for p in [model_path, meta_path]:
        if p.exists():
            os.remove(p)
            print(f"  Deleted '{p}'")
