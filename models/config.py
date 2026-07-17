"""
config.py
---------
Central configuration for the anomaly detection/correction pipeline.

All tunable constants live here so that only this file needs to be changed
when adapting the pipeline to a different sensor or deployment site.
"""

# ---------------------------------------------------------------------------
# Error Code Definitions
# ---------------------------------------------------------------------------
ERROR_CODE_LABELS = {
    0: "ok",
    1: "abort",
    2: "sensor timeout",
    3: "spike detected",
    4: "exceed limit",
    5: "sensor unstable",
}

# Codes where the Water Level is ALWAYS invalid – replace 100% with prediction
ALWAYS_CORRUPT_CODES = frozenset({1, 2, 3})

# Codes where the Water Level is SOMETIMES valid – apply residual gate
PARTIAL_CODES = frozenset({5})

# Codes where value may be a real extreme event OR a fault
LIMIT_CODES = frozenset({4})

# ---------------------------------------------------------------------------
# Physical Sensor Bounds  (adjust to match actual sensor spec)
# ---------------------------------------------------------------------------
PHYSICAL_MIN_M = 0.05   # Minimum plausible water level (metres)
                         # Values at exactly 0.0 are almost always fault readings
PHYSICAL_MAX_M = 4.5    # Maximum plausible water level (metres) — tank capacity

# ---------------------------------------------------------------------------
# Anomaly Correction Thresholds
# ---------------------------------------------------------------------------
# For errorcode=5: if |prediction − reading| > this, treat reading as corrupt
RESIDUAL_THRESHOLD_M = 0.80   # metres

# Temporal consistency thresholds
MAX_CONSISTENCY_GAP_MIN = 35  # minutes
MAX_CONSISTENCY_STEP_M = 0.35 # metres

# For errorcode=4: additional guard – if reading is outside physical bounds,
# replace regardless of residual
LIMIT_RESIDUAL_THRESHOLD_M = 0.80  # metres (higher tolerance for real floods)

# ---------------------------------------------------------------------------
# Feature Engineering (ARFR lag window)
# ---------------------------------------------------------------------------
N_LAGS = 8          # Number of past corrected values used as features
                    # 8 × 15 min = 2-hour look-back window

# ---------------------------------------------------------------------------
# SNARIMAX Hyper-parameters
# (River time_series.SNARIMAX)
# ---------------------------------------------------------------------------
# Apartment water tanks follow a ~12-hour pump/refill cycle (filled twice daily).
# At 15-minute resolution, one full refill cycle = 48 steps.
SNARIMAX_PARAMS = dict(
    p  = 8,    # Non-seasonal AR order (8 x 15 min = 2 h look-back)
    d  = 0,    # NO differencing -- water level is bounded (0-4.5 m), not a random walk
    q  = 2,    # Non-seasonal MA order
    m  = 24,   # Seasonal period (6-hour pump half-cycle at 15-min steps)
    sp = 1,    # Seasonal AR order
    sd = 0,    # Seasonal differencing
    sq = 1,    # Seasonal MA order
)

# ---------------------------------------------------------------------------
# Adaptive Random Forest Regressor Hyper-parameters
# (River ensemble.AdaptiveRandomForestRegressor)
# ---------------------------------------------------------------------------
ARFR_PARAMS = dict(
    n_models = 10,
    seed     = 42,
)

# Warm-up period before ARFR predictions are trusted
# (need enough lags in the buffer first)
ARFR_WARMUP_STEPS = N_LAGS + 2

# ---------------------------------------------------------------------------
# Ensemble Weighting
# ---------------------------------------------------------------------------
# ARFR is weighted higher: it uses lag features (knows recent history),
# handles non-linearity, and doesn't blow up during outages.
# SNARIMAX provides seasonal structure but is less stable during long gaps.
SNARIMAX_WEIGHT = 0.35
ARFR_WEIGHT     = 0.65

# ---------------------------------------------------------------------------
# Output Paths (relative to project root)
# ---------------------------------------------------------------------------
INPUT_CSV  = "data/processed/combined_data.csv"
OUTPUT_CSV = "data/processed/corrected_data.csv"
