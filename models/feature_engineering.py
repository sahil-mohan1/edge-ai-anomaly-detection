"""
feature_engineering.py
-----------------------
Builds the feature dictionary consumed by the ARFR model.

Features
--------
Lag features   : last N corrected water-level readings (rolling buffer)
Cyclic time    : sin/cos encoding of hour-of-day and minute-of-day
                 so the model understands the 24-hour daily cycle
Refill cycle   : sin/cos encoding of the 12-hour pump/refill cycle
                 (water is pumped into the apartment tank twice per day)
Day of week    : integer 0-6 (Mon=0)
Prev errorcode : the previous step's error code (signals recent instability)
"""

import math
from collections import deque
from datetime import datetime
from . import config


class FeatureEngineer:
    """
    Maintains a rolling buffer of past corrected values and builds a
    feature dictionary for each new time step.
    """

    def __init__(self, n_lags: int = config.N_LAGS):
        self.n_lags = n_lags
        # Initialise buffer with zeros (model will warm up over first n_lags steps)
        self._buffer: deque[float] = deque([0.0] * n_lags, maxlen=n_lags)
        self._prev_errorcode: int = 0
        self._step: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_features(self, timestamp: datetime, errorcode: int) -> dict:
        """
        Build and return a feature dict for the current time step.

        Parameters
        ----------
        timestamp   : parsed datetime of the current reading
        errorcode   : raw error code of the current reading

        Returns
        -------
        dict  – feature dictionary ready to pass to ARFR.predict_one / learn_one
        """
        features: dict = {}

        # ---- Lag features ----
        for i, val in enumerate(reversed(self._buffer), start=1):
            features[f"lag_{i}"] = val

        # ---- Cyclic time encoding ----
        hour      = timestamp.hour
        minute    = timestamp.minute
        # Minutes since midnight (0 – 1439)
        mins_day  = hour * 60 + minute
        day_frac  = mins_day / 1440.0          # 0.0 → 1.0 over one day

        features["hour_sin"]   = math.sin(2 * math.pi * day_frac)
        features["hour_cos"]   = math.cos(2 * math.pi * day_frac)

        # ---- Refill cycle encoding (12-hour pump/refill cycle) ----
        # Apartment water tanks are typically refilled twice per day
        # (e.g., morning and evening pump schedule).
        refill_frac = mins_day / 720.0
        features["refill_sin"]  = math.sin(2 * math.pi * refill_frac)
        features["refill_cos"]  = math.cos(2 * math.pi * refill_frac)

        # ---- Calendar features ----
        features["day_of_week"] = float(timestamp.weekday())   # 0=Mon … 6=Sun

        # ---- Previous error code ----
        features["prev_errorcode"] = float(self._prev_errorcode)

        return features

    def update(self, corrected_value: float, errorcode: int) -> None:
        """
        Push the corrected value into the rolling buffer so it can be used
        as a lag feature in the next step.

        Parameters
        ----------
        corrected_value : the final (possibly replaced) water level
        errorcode       : raw error code of the step just processed
        """
        self._buffer.append(corrected_value)
        self._prev_errorcode = errorcode
        self._step += 1

    @property
    def is_warmed_up(self) -> bool:
        """True once the buffer has enough real values for reliable features."""
        return self._step >= self.n_lags

    @property
    def step(self) -> int:
        return self._step
