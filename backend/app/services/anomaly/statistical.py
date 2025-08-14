"""
Statistical Anomaly Detector
Uses rolling Z-score to detect anomalies in each metric independently.
"""

from __future__ import annotations

import math
from collections import deque

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.anomaly.base import AnomalyDetector, AnomalyResult

logger = get_logger(__name__)

FEATURE_NAMES = [
    "packets_per_sec", "bytes_per_sec", "active_flows", "new_flows",
    "tcp_ratio", "udp_ratio", "icmp_ratio", "dns_ratio",
    "packet_loss_pct", "avg_latency_ms",
]


class _RollingStats:
    """Welford's online algorithm for rolling mean and std."""

    def __init__(self, window: int = 300):
        self.window = window
        self._values: deque[float] = deque(maxlen=window)
        self._n = 0
        self._mean = 0.0
        self._M2 = 0.0

    def update(self, x: float) -> None:
        if math.isnan(x) or math.isinf(x):
            return
        self._n += 1
        delta = x - self._mean
        self._mean += delta / self._n
        self._M2 += delta * (x - self._mean)
        self._values.append(x)
        if len(self._values) == self.window and self._n > self.window:
            vals = list(self._values)
            n = len(vals)
            m = sum(vals) / n
            v = sum((v - m) ** 2 for v in vals) / max(n - 1, 1)
            self._mean = m
            self._M2 = v * max(n - 1, 1)
            self._n = n

    @property
    def mean(self) -> float:
        return self._mean

    @property
    def std(self) -> float:
        if self._n < 2:
            return 0.0
        return math.sqrt(self._M2 / (self._n - 1))

    @property
    def count(self) -> int:
        return self._n


class StatisticalDetector(AnomalyDetector):
    """Per-feature Z-score anomaly detector with rolling statistics."""

    def __init__(self, threshold: float | None = None, window: int | None = None, min_samples: int | None = None):
        super().__init__(name="statistical")
        settings = get_settings()
        self.threshold = threshold or settings.anomaly_threshold
        self.window = window or settings.anomaly_training_window
        self.min_samples = min_samples or settings.anomaly_min_samples
        self._stats: list[_RollingStats] = [_RollingStats(window=self.window) for _ in FEATURE_NAMES]

    def fit(self, data: list[list[float]]) -> None:
        for features in data:
            for i, val in enumerate(features):
                if i < len(self._stats):
                    self._stats[i].update(val)
            self._samples_seen += 1
        if len(data) >= self.min_samples:
            self._fitted = True
        logger.info("statistical_detector_fitted", samples=len(data))

    def predict(self, features: list[float]) -> AnomalyResult:
        if self._samples_seen < self.min_samples:
            for i, val in enumerate(features):
                if i < len(self._stats):
                    self._stats[i].update(val)
            self._samples_seen += 1
            return AnomalyResult(is_anomalous=False, score=0.0, details={"reason": "insufficient_baseline"})

        max_z = 0.0
        worst_feature = None
        worst_observed = None
        worst_baseline = None
        z_scores: dict[str, float] = {}

        for i, (val, stats, name) in enumerate(zip(features, self._stats, FEATURE_NAMES)):
            self._stats[i].update(val)
            if stats.std < 1e-10:
                continue
            z = abs((val - stats.mean) / stats.std)
            z_scores[name] = round(z, 3)
            if z > max_z:
                max_z = z
                worst_feature = name
                worst_observed = val
                worst_baseline = stats.mean

        self._samples_seen += 1
        is_anomalous = max_z > self.threshold
        score = min(max_z / (self.threshold * 3), 1.0) if max_z > 0 else 0.0

        _anomaly_map = {
            "packets_per_sec": "packet_rate_spike", "bytes_per_sec": "traffic_spike",
            "active_flows": "connection_spike", "new_flows": "connection_spike",
            "tcp_ratio": "protocol_anomaly", "udp_ratio": "protocol_anomaly",
            "icmp_ratio": "protocol_anomaly", "dns_ratio": "protocol_anomaly",
        }

        if is_anomalous:
            logger.info("anomaly_detected", detector="statistical", feature=worst_feature, z_score=round(max_z, 2))

        return AnomalyResult(
            is_anomalous=is_anomalous, score=round(score, 4),
            anomaly_type=_anomaly_map.get(worst_feature or "", "statistical_anomaly") if is_anomalous else None,
            metric_name=worst_feature, observed_value=worst_observed,
            baseline_value=worst_baseline, deviation_sigma=round(max_z, 3),
            details={"z_scores": z_scores, "threshold": self.threshold},
        )

    def update(self, features: list[float]) -> AnomalyResult:
        return self.predict(features)

    def get_info(self) -> dict:
        info = super().get_info()
        info.update({"threshold": self.threshold, "window": self.window, "min_samples": self.min_samples})
        return info

    def set_threshold(self, threshold: float) -> None:
        """Update the detection threshold dynamically."""
        self.threshold = threshold
        logger.info("statistical_detector_threshold_updated", threshold=threshold)
