"""
Anomaly Detector Factory
Returns the configured detector based on settings.
"""

from __future__ import annotations

from app.core.config import AnomalyMethod, get_settings
from app.core.logging import get_logger
from app.services.anomaly.base import AnomalyDetector

logger = get_logger(__name__)

_detector_instance: AnomalyDetector | None = None


def get_detector() -> AnomalyDetector:
    """Return the singleton anomaly detector configured in settings."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = _create_detector()
    return _detector_instance


def _create_detector() -> AnomalyDetector:
    settings = get_settings()
    method = settings.anomaly_method

    if method == AnomalyMethod.ISOLATION_FOREST:
        from app.services.anomaly.isolation_forest import IsolationForestDetector
        logger.info("anomaly_detector_created", type="isolation_forest")
        return IsolationForestDetector()
    else:
        from app.services.anomaly.statistical import StatisticalDetector
        logger.info("anomaly_detector_created", type="statistical")
        return StatisticalDetector()


def reset_detector() -> None:
    """Reset the detector singleton (useful for testing or reconfiguration)."""
    global _detector_instance
    _detector_instance = None


def update_detector_threshold(threshold: float) -> None:
    """Dynamically update the threshold of the active detector instance."""
    if _detector_instance is not None and hasattr(_detector_instance, "set_threshold"):
        _detector_instance.set_threshold(threshold)
