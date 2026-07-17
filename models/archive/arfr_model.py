"""
arfr_model.py
-------------
Thin wrapper around River's AdaptiveRandomForestRegressor (ARFR).

Why ARFR for water level?
- Non-linear: captures tidal curves, rain events, abrupt transitions
- Concept-drift aware: uses ADWIN detector internally to adapt when the
  sensor baseline shifts (e.g., seasonal low-water vs. monsoon period)
- Online: per-sample update, zero retraining overhead
- Works alongside engineered features (lags, cyclic time)

Key API contract
----------------
  predict(features: dict) -> float   returns next-step regression estimate
  learn(features: dict, y: float)    updates model with clean observation
  reset() -> None                    re-initialises the model
"""

from river import forest
from . import config


class ARFRModel:
    """
    Online Adaptive Random Forest Regressor for water-level prediction.

    Receives a feature dictionary (built by FeatureEngineer) for each
    time step.  Like SNARIMAXModel, it only learns from clean readings.
    """

    def __init__(self, params: dict | None = None,
                 warmup_steps: int = config.ARFR_WARMUP_STEPS):
        """
        Parameters
        ----------
        params        : dict of ARFR hyper-parameters (see config.ARFR_PARAMS).
        warmup_steps  : number of steps before predictions are considered
                        reliable (the lag buffer must fill first).
        """
        self._params       = params or config.ARFR_PARAMS
        self._model        = forest.ARFRegressor(**self._params)
        self._warmup_steps = warmup_steps
        self._n_trained    = 0         # count of learn() calls
        self._last_pred: float = 0.0  # cached last prediction

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(self, features: dict) -> float:
        """
        Predict the next water level given a feature dictionary.

        Returns 0.0 (or the last known prediction) during warm-up so that
        the caller can weight SNARIMAX more heavily early on.

        Parameters
        ----------
        features : dict produced by FeatureEngineer.build_features()
        """
        if not self.is_warmed_up:
            return self._last_pred

        try:
            pred = self._model.predict_one(features)
            if pred is not None:
                self._last_pred = float(pred)
        except Exception:
            pass   # sparse features / untrained trees – return cached value

        return self._last_pred

    def learn(self, features: dict, y: float) -> None:
        """
        Update the ARFR model with one clean sample.

        Parameters
        ----------
        features : dict produced by FeatureEngineer.build_features()
        y        : corrected water level (metres)
        """
        self._model.learn_one(features, y)
        self._n_trained += 1

    def reset(self) -> None:
        """Re-initialise the model from scratch."""
        self._model     = forest.ARFRegressor(**self._params)
        self._n_trained = 0
        self._last_pred = 0.0

    @property
    def is_warmed_up(self) -> bool:
        return self._n_trained >= self._warmup_steps

    @property
    def n_trained(self) -> int:
        return self._n_trained
