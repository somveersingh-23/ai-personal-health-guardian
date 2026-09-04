"""Legacy model module; canonical implementation is in quality_model.py."""

from sensor_intelligence.quality_model import (
    QualityPrediction,
    TransparentQualityModel,
    load_quality_model,
)

__all__ = [
    "QualityPrediction",
    "TransparentQualityModel",
    "load_quality_model",
]
