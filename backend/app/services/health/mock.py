"""Offline importer used in tests / when a raw payload can't be parsed.

Also powers a "load sample data" affordance so the feature is demoable without
a real Apple/Google/Huawei export.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models.enums import HEALTH_METRIC_UNITS, HealthMetricType, HealthSource
from app.services.health.base import NormalizedSample


class MockHealthImporter:
    source = HealthSource.MANUAL

    def parse(self, data: bytes, filename: str | None = None) -> list[NormalizedSample]:
        return sample_series()


def sample_series(days: int = 7) -> list[NormalizedSample]:
    """Deterministic multi-metric series over the last `days` days."""
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    out: list[NormalizedSample] = []
    for d in range(days):
        ts = now - timedelta(days=d)
        for metric, value in (
            (HealthMetricType.STEPS, 6000 + d * 250),
            (HealthMetricType.HEART_RATE, 68 + (d % 5)),
            (HealthMetricType.BODY_WEIGHT, 74.5 - d * 0.1),
            (HealthMetricType.SLEEP, 420 - (d % 3) * 15),
            (HealthMetricType.OXYGEN_SATURATION, 97 + (d % 2)),
        ):
            out.append(
                NormalizedSample(
                    metric_type=metric,
                    value=float(value),
                    unit=HEALTH_METRIC_UNITS[metric],
                    recorded_at=ts,
                )
            )
    return out
