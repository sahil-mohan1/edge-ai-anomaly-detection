"""
hybrid_corrector.py
-------------------
Core anomaly-detection and correction pipeline.

Combines SNARIMAX (structured tidal prediction) and ARFR (non-linear
feature-based prediction) into a single weighted ensemble, then applies
error-code-aware rules to decide whether to trust each reading or replace
it with the ensemble prediction.

Error-code policy
-----------------
  0  (ok)             → trust the reading; update both models
  1  (abort)          → always replace; do NOT update models
  2  (sensor timeout) → always replace; do NOT update models
  3  (spike detected) → always replace; do NOT update models
  4  (exceed limit)   → check physical bounds:
                          within bounds  → trust (real flood/dry event); update
                          out of bounds  → replace; do NOT update
  5  (sensor unstable)→ residual gate:
                          |pred − reading| ≤ threshold AND reading ≠ 0.0
                            → partially valid; trust; update
                          otherwise → replace; do NOT update

Output per step
---------------
  corrected_value : float      final best-estimate water level
  is_anomaly      : bool       True if the original reading was replaced
  correction_src  : str        'raw' | 'snarimax' | 'arfr' | 'ensemble'
                               | 'physical_bounds' | 'residual_gate'
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from . import config
from .arfr_model import ARFRModel
from .feature_engineering import FeatureEngineer
from .snarimax_model import SNARIMAXModel


# ---------------------------------------------------------------------------
# Result dataclass returned for every processed reading
# ---------------------------------------------------------------------------

@dataclass
class CorrectionResult:
    timestamp:       datetime
    errorcode:       int
    original_value:  float
    corrected_value: float
    snarimax_pred:   float
    arfr_pred:       float
    ensemble_pred:   float
    is_anomaly:      bool
    correction_src:  str          # explains WHY a correction was (or was not) applied
    residual:        float        # |ensemble_pred − original_value|


# ---------------------------------------------------------------------------
# Main corrector class
# ---------------------------------------------------------------------------

class HybridCorrector:
    """
    Online, one-sample-at-a-time anomaly correction pipeline.

    Usage
    -----
    >>> corrector = HybridCorrector()
    >>> result = corrector.process(timestamp, errorcode, water_level)
    >>> print(result.corrected_value, result.is_anomaly)
    """

    def __init__(
        self,
        snarimax_weight: float = config.SNARIMAX_WEIGHT,
        arfr_weight:     float = config.ARFR_WEIGHT,
        residual_thresh: float = config.RESIDUAL_THRESHOLD_M,
        limit_thresh:    float = config.LIMIT_RESIDUAL_THRESHOLD_M,
        physical_min:    float = config.PHYSICAL_MIN_M,
        physical_max:    float = config.PHYSICAL_MAX_M,
    ):
        self._snarimax_w  = snarimax_weight
        self._arfr_w      = arfr_weight
        self._res_thresh  = residual_thresh
        self._lim_thresh  = limit_thresh
        self._phys_min    = physical_min
        self._phys_max    = physical_max

        # Sub-models
        self.snarimax  = SNARIMAXModel()
        self.arfr      = ARFRModel()
        self.feat_eng  = FeatureEngineer()

        # Last known clean water level (used as hold value during long outages)
        self._last_valid_value: float = 0.0
        self._last_valid_ts: Optional[datetime] = None

        # Running statistics (for reporting)
        self._stats: dict[str, int] = {
            "total":            0,
            "corrected":        0,
            "ec_abort":         0,   # errorcode 1
            "ec_timeout":       0,   # errorcode 2
            "ec_spike":         0,   # errorcode 3
            "ec_limit_fault":   0,   # errorcode 4 – out of physical range
            "ec_limit_real":    0,   # errorcode 4 – trusted as real event
            "ec_unstable_bad":  0,   # errorcode 5 – replaced
            "ec_unstable_ok":   0,   # errorcode 5 – kept
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        timestamp:   datetime,
        errorcode:   int,
        water_level: float,
    ) -> CorrectionResult:
        """
        Process one sensor reading and return a CorrectionResult.

        Parameters
        ----------
        timestamp   : datetime of the reading
        errorcode   : raw sensor error code (0–5)
        water_level : raw water level value (metres)

        Returns
        -------
        CorrectionResult  – contains corrected value, anomaly flag, diagnostics
        """
        self._stats["total"] += 1

        # ---- Step 1: Build features & get predictions ----
        features      = self.feat_eng.build_features(timestamp, errorcode)
        snarimax_pred = self.snarimax.predict()
        arfr_pred     = self.arfr.predict(features)
        ensemble_pred = self._blend(snarimax_pred, arfr_pred)

        residual = abs(ensemble_pred - water_level)

        # ---- Step 2: Apply error-code policy ----
        corrected, is_anomaly, src = self._apply_policy(
            errorcode, water_level, ensemble_pred, residual,
            self._last_valid_value, self._last_valid_ts, timestamp
        )

        # ---- Step 3: Update models and last-valid tracker on clean readings ----
        if not is_anomaly:
            self._last_valid_value = corrected   # keep track of last good value
            self._last_valid_ts = timestamp
            self.snarimax.learn(corrected)
            self.arfr.learn(features, corrected)

        # ---- Step 4: Advance feature buffer with corrected value ----
        self.feat_eng.update(corrected, errorcode)

        if is_anomaly:
            self._stats["corrected"] += 1

        return CorrectionResult(
            timestamp       = timestamp,
            errorcode       = errorcode,
            original_value  = water_level,
            corrected_value = corrected,
            snarimax_pred   = snarimax_pred,
            arfr_pred       = arfr_pred,
            ensemble_pred   = ensemble_pred,
            is_anomaly      = is_anomaly,
            correction_src  = src,
            residual        = residual,
        )

    @property
    def stats(self) -> dict:
        """Running correction statistics dictionary."""
        return dict(self._stats)

    def summary(self) -> str:
        """Return a formatted summary string."""
        s = self._stats
        pct = (s["corrected"] / s["total"] * 100) if s["total"] else 0
        lines = [
            "=" * 55,
            "  Hybrid Corrector - Processing Summary",
            "=" * 55,
            f"  Total readings processed : {s['total']:,}",
            f"  Anomalies corrected      : {s['corrected']:,}  ({pct:.1f}%)",
            "-" * 55,
            f"  +-- EC=1 Abort (hold)     : {s['ec_abort']:,}",
            f"  +-- EC=2 Timeout (hold)   : {s['ec_timeout']:,}",
            f"  +-- EC=3 Spike (clamped)  : {s['ec_spike']:,}",
            f"  +-- EC=4 Limit - fault    : {s['ec_limit_fault']:,}",
            f"  +-- EC=4 Limit - real evt : {s['ec_limit_real']:,}  (kept)",
            f"  +-- EC=5 Unstable - bad   : {s['ec_unstable_bad']:,}",
            f"  +-- EC=5 Unstable - ok    : {s['ec_unstable_ok']:,}  (kept)",
            "=" * 55,
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _blend(self, snarimax_pred: float, arfr_pred: float) -> float:
        """
        Weighted ensemble of SNARIMAX and ARFR predictions.
        Falls back to SNARIMAX alone during ARFR warm-up.
        """
        if not self.arfr.is_warmed_up:
            return snarimax_pred
        if not self.snarimax.is_trained:
            return arfr_pred
        return self._snarimax_w * snarimax_pred + self._arfr_w * arfr_pred

    def _apply_policy(
        self,
        errorcode:        int,
        water_level:      float,
        ensemble_pred:    float,
        residual:         float,
        last_valid_value: float = 0.0,
        last_valid_ts:    Optional[datetime] = None,
        current_ts:       Optional[datetime] = None,
    ) -> tuple[float, bool, str]:
        """
        Apply the error-code-aware correction policy.

        Returns
        -------
        (corrected_value, is_anomaly, correction_source_label)
        """

        # ---- errorcode 0: OK -- trust the reading ----
        if errorcode == 0:
            return water_level, False, "raw"

        # ---- errorcodes 1, 2: abort / timeout -- hold last valid value ----
        # The sensor is completely offline. We cannot predict what the water
        # level did during the outage. Holding the last known good reading
        # is honest and prevents the lag buffer from being corrupted with
        # clamped extreme predictions.
        if errorcode in (1, 2):
            stat_key = {1: "ec_abort", 2: "ec_timeout"}[errorcode]
            self._stats[stat_key] += 1
            hold_val = last_valid_value if last_valid_value > 0 else ensemble_pred
            return hold_val, True, "hold_last_valid"

        # ---- errorcode 3: spike detected (sensor clamped to 0.0) ----
        # Sensor caught its own spike. Replace with ensemble prediction.
        if errorcode == 3:
            self._stats["ec_spike"] += 1
            return ensemble_pred, True, "ensemble"

        # ---- errorcode 4: exceed limit -- physical bounds check ----
        if errorcode in config.LIMIT_CODES:
            within_bounds = self._phys_min <= water_level <= self._phys_max
            if within_bounds and residual <= self._lim_thresh:
                self._stats["ec_limit_real"] += 1
                return water_level, False, "raw"
            else:
                self._stats["ec_limit_fault"] += 1
                return ensemble_pred, True, "physical_bounds"

        # ---- errorcode 5: sensor unstable -- residual gate ----
        if errorcode in config.PARTIAL_CODES:
            reading_is_zero = (water_level == 0.0)
            
            # Temporal consistency check
            is_temporally_consistent = False
            if last_valid_ts is not None and current_ts is not None:
                time_gap = current_ts - last_valid_ts
                if time_gap.total_seconds() <= config.MAX_CONSISTENCY_GAP_MIN * 60:
                    if abs(water_level - last_valid_value) <= config.MAX_CONSISTENCY_STEP_M:
                        is_temporally_consistent = True
                        
            reading_is_bad  = reading_is_zero or (residual > self._res_thresh and not is_temporally_consistent)
            if reading_is_bad:
                self._stats["ec_unstable_bad"] += 1
                return ensemble_pred, True, "residual_gate"
            else:
                self._stats["ec_unstable_ok"] += 1
                return water_level, False, "raw"

        # ---- Unknown error code: conservative fallback ----
        return ensemble_pred, True, "ensemble"
