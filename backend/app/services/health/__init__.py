"""Health-platform integration: import & normalize data from Apple/Google/Huawei.

No web APIs are used (Apple has none; Google Fit is retiring; Huawei needs an
approved developer account), so the reliable path is file import. Each provider
parses its export format into canonical `HealthMetricType` samples; OAuth
connectors can be added later behind the same `HealthImporter` interface.
"""
from app.services.health import service
from app.services.health.base import (
    HealthImporter,
    ImportResult,
    NormalizedSample,
)
from app.services.health.factory import get_importer

__all__ = [
    "HealthImporter",
    "ImportResult",
    "NormalizedSample",
    "get_importer",
    "service",
]
