"""
Anomaly Detector Abstract Base
================================
All anomaly detectors implement this interface.
The pluggable architecture allows switching between statistical
and ML-based detectors via configuration.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any


@dataclass
class AnomalyResult:
    """Result from an anomaly detector."""
    is_anomalous: bool
    score: float            # 0.0 (normal) to 1.0 (highly anomalous)
    anomaly_type: str | None = None
    metric_name: str | None = None
    observed_value: float | None = None
    baseline_value: float | None = None
    deviation_sigma: float | None = None
    details: dict[str, Any] | None = None


class AnomalyDetector(abc.ABC):
    """
    Abstract base class for all anomaly detection strategies.

    Implementations:
        - StatisticalDetector: Z-score based rolling statistics
        - IsolationForestDetector: sklearn IsolationForest
    """

    def __init__(self, name: str):
        self.name = name
        self._fitted = False
        self._samples_seen = 0

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    @property
    def samples_seen(self) -> int:
        return self._samples_seen

    @abc.abstractmethod
    def fit(self, data: list[list[float]]) -> None:
        """
        Train the detector on baseline data.
        data: list of feature vectors (each a list of floats)
        """
        ...

    @abc.abstractmethod
    def predict(self, features: list[float]) -> AnomalyResult:
        """
        Predict whether the given feature vector is anomalous.
        features: single feature vector
        """
        ...

    def update(self, features: list[float]) -> AnomalyResult:
        """
        Online update: add sample to model and predict simultaneously.
        Default implementation just calls predict; subclasses may override
        to do true online learning.
        """
        self._samples_seen += 1
        return self.predict(features)

    def get_info(self) -> dict[str, Any]:
        """Return detector metadata for the health/system endpoint."""
        return {
            "name": self.name,
            "fitted": self._fitted,
            "samples_seen": self._samples_seen,
        }
