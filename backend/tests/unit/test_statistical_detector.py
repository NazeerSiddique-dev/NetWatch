"""Unit tests for StatisticalDetector."""

import pytest
from app.services.anomaly.statistical import StatisticalDetector


def make_normal_features(n: float = 100.0) -> list[float]:
    """Normal-looking feature vector."""
    return [n, n * 125, 10, 2, 0.68, 0.21, 0.04, 0.05, 0.01, 20.0]


def make_spike_features() -> list[float]:
    """Anomalous spike feature vector."""
    return [100000.0, 100000.0 * 125, 1000, 500, 0.98, 0.01, 0.01, 0.0, 0.5, 200.0]


def test_insufficient_baseline():
    """Detector should not flag anomalies before min_samples are collected."""
    detector = StatisticalDetector(min_samples=10)
    result = detector.predict(make_normal_features())
    assert not result.is_anomalous
    assert result.score == 0.0


def test_normal_traffic_not_flagged():
    """Normal traffic should not be flagged after sufficient baseline."""
    detector = StatisticalDetector(threshold=3.0, min_samples=5)
    baseline = [make_normal_features(n=100.0 + i * 0.5) for i in range(10)]
    detector.fit(baseline)
    result = detector.predict(make_normal_features(101.0))
    assert not result.is_anomalous


def test_spike_detected():
    """Traffic spike should be detected after baseline is established."""
    detector = StatisticalDetector(threshold=3.0, min_samples=5)
    baseline = [make_normal_features() for _ in range(15)]
    detector.fit(baseline)
    result = detector.predict(make_spike_features())
    assert result.is_anomalous
    assert result.score > 0.5
    assert result.deviation_sigma is not None
    assert result.deviation_sigma > 3.0


def test_score_bounded():
    """Anomaly score should be in [0, 1]."""
    detector = StatisticalDetector(threshold=3.0, min_samples=5)
    detector.fit([make_normal_features() for _ in range(20)])
    result = detector.predict(make_spike_features())
    assert 0.0 <= result.score <= 1.0


def test_anomaly_type_set():
    """Anomaly type should be set when anomaly is detected."""
    detector = StatisticalDetector(threshold=3.0, min_samples=5)
    detector.fit([make_normal_features() for _ in range(20)])
    result = detector.predict(make_spike_features())
    if result.is_anomalous:
        assert result.anomaly_type is not None
