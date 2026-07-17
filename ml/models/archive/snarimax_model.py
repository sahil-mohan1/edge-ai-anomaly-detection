"""
snarimax_model.py
-----------------
Thin wrapper around River's SNARIMAX time-series model.

SNARIMAX = Seasonal Non-linear AutoRegressive Integrated Moving Average
           with eXogenous inputs.

Why SNARIMAX for water level?
- Captures the ~12-hour semi-diurnal tidal periodicity (m=48 at 15-min steps)
- Online: updates one observation at a time – no retraining required
- Differencing (d=1) removes slow sensor drift
- Prediction fills gaps caused by errorcode 1/2/3 faults

Key API contract
----------------
  predict() -> float          returns the next-step forecast
  learn(y: float) -> None     updates the model with a clean observation
  reset() -> None             re-initialises the model (use sparingly)
"""

from river import time_series
from . import config


class SNARIMAXModel:
    """
    Online SNARIMAX wrapper for water-level time-series prediction.

    The model ONLY learns from clean / corrected readings.  During
    anomalous periods the caller should call predict() but NOT learn().
    """

    def __init__(self, params: dict | None = None):
        """
        Parameters
        ----------
        params : dict of SNARIMAX hyper-parameters (see config.SNARIMAX_PARAMS).
                 Defaults to config values if not provided.
        """
        self._params  = params or config.SNARIMAX_PARAMS
        self._model   = time_series.SNARIMAX(**self._params)
        self._trained = False          # becomes True after first learn() call
        self._last_pred: float = 0.0  # cached forecast

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(self) -> float:
        """
        Forecast the next step.

        Before any training has occurred returns 0.0 (safe default).
        After training, returns the one-step-ahead forecast clamped to a
        physically plausible range to prevent SNARIMAX differencing blow-ups
        during the warm-up phase.
        """
        if not self._trained:
            return self._last_pred

        try:
            forecast = self._model.forecast(horizon=1)
            val = float(forecast[0])
            # Clamp to physical range – prevents d=1 differencing blow-up
            from . import config
            val = max(config.PHYSICAL_MIN_M, min(val, config.PHYSICAL_MAX_M))
            self._last_pred = val
        except Exception:
            pass   # model hasn't seen enough history yet – keep last prediction

        return self._last_pred

    def learn(self, y: float) -> None:
        """
        Update the SNARIMAX model with one clean water-level observation.

        Parameters
        ----------
        y : corrected water level (metres)
        """
        self._model.learn_one(y)
        self._trained = True

    def reset(self) -> None:
        """Re-initialise the model from scratch."""
        self._model   = time_series.SNARIMAX(**self._params)
        self._trained = False
        self._last_pred = 0.0

    @property
    def is_trained(self) -> bool:
        return self._trained
