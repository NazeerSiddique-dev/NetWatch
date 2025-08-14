"""
Isolation Forest Anomaly Detector
Wraps scikit-learn's IsolationForest for multivariate anomaly detection.
"""

from __future__ import annotations

import numpy as np
from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.anomaly.base import AnomalyDetector, AnomalyResult
from app.services.anomaly.statistical import FEATURE_NAMES

logger = get_logger(__name__)


class IsolationForestDetector(AnomalyDetector):
    """
    ML-based anomaly detector using sklearn IsolationForest.
    Requires a training phase (fit) on baseline/normal traffic data.
    """

    def __init__(self, n_estimators: int = 100, contamination: float = 0.05, random_state: int = 42):
        super().__init__(name="isolation_forest")
        settings = get_settings()
        self.min_samples = settings.anomaly_min_samples
        self._n_estimators = n_estimators
        self._contamination = contamination
        self._random_state = random_state
        self._model = None
        self._training_buffer: list[list[float]] = []

    def fit(self, data: list[list[float]]) -> None:
        """Train the Isolation Forest on baseline traffic data."""
        if len(data) < self.min_samples:
            logger.warning("isolation_forest_insufficient_data", samples=len(data), required=self.min_samples)
            return

        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import StandardScaler

        X = np.array(data, dtype=float)
        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(X)

        self._model = IsolationForest(
            n_estimators=self._n_estimators,
            contamination=self._contamination,
            random_state=self._random_state,
            n_jobs=-1,
        )
        self._model.fit(X_scaled)
        self._fitted = True
        self._samples_seen = len(data)
        self._training_buffer.clear()
        logger.info("isolation_forest_fitted", samples=len(data))

    def predict(self, features: list[float]) -> AnomalyResult:
        """Predict anomaly score for a single feature vector."""
        # Collect samples until we have enough to train
        if not self._fitted:
            self._training_buffer.append(features)
            self._samples_seen += 1
            if len(self._training_buffer) >= self.min_samples:
                self.fit(self._training_buffer)
            return AnomalyResult(
                is_anomalous=False, score=0.0,
                details={"reason": "training", "samples": len(self._training_buffer)},
            )

        X = np.array([features], dtype=float)
        X_scaled = self._scaler.transform(X)

        # IsolationForest decision_function: negative = anomalous, positive = normal
        raw_score = float(self._model.decision_function(X_scaled)[0])
        prediction = int(self._model.predict(X_scaled)[0])  # -1 = anomaly, 1 = normal

        # Normalise score to [0, 1]: -0.5 = 1.0 (anomaly), +0.5 = 0.0 (normal)
        normalised = max(0.0, min(1.0, (-raw_score + 0.5) * 2))
        is_anomalous = prediction == -1

        if is_anomalous:
            logger.info("anomaly_detected", detector="isolation_forest", score=round(normalised, 4))

        return AnomalyResult(
            is_anomalous=is_anomalous,
            score=round(normalised, 4),
            anomaly_type="statistical_anomaly" if is_anomalous else None,
            details={"raw_score": round(raw_score, 4), "contamination": self._contamination},
        )

    def update(self, features: list[float]) -> AnomalyResult:
        return self.predict(features)

    def get_info(self) -> dict:
        info = super().get_info()
        info.update({
            "n_estimators": self._n_estimators,
            "contamination": self._contamination,
            "training_buffer_size": len(self._training_buffer),
        })
        return info
