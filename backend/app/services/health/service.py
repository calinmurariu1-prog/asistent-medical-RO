"""Persist normalized samples (idempotently) and build UI summaries."""
from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import (
    HEALTH_METRIC_LABELS,
    HEALTH_METRIC_UNITS,
    HealthMetricType,
    HealthSource,
)
from app.models.health import HealthSample
from app.services.health.base import ImportResult, NormalizedSample

# A single upload can't insert more than this (memory / abuse guard).
MAX_SAMPLES_PER_IMPORT = 100_000


def _norm_ts(dt: datetime) -> datetime:
    """Normalize to naive-UTC so dedup keys match across backends.

    SQLite drops tzinfo on read while Postgres keeps it; comparing a normalized
    form keeps the natural-key set consistent either way.
    """
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def persist_samples(
    db: Session,
    patient_id: int,
    source: HealthSource,
    samples: list[NormalizedSample],
) -> ImportResult:
    """Insert new samples, skipping ones already present (idempotent import)."""
    result = ImportResult(source=source)
    if not samples:
        return result

    samples = samples[:MAX_SAMPLES_PER_IMPORT]

    # Existing natural keys for this patient+source, to skip duplicates cheaply.
    existing: set[tuple[HealthMetricType, datetime]] = {
        (mt, _norm_ts(ts))
        for mt, ts in db.execute(
            select(HealthSample.metric_type, HealthSample.recorded_at).where(
                HealthSample.patient_id == patient_id,
                HealthSample.source == source,
            )
        ).all()
    }

    seen_in_batch: set[tuple[HealthMetricType, datetime]] = set()
    for s in samples:
        key = (s.metric_type, _norm_ts(s.recorded_at))
        if key in existing or key in seen_in_batch:
            result.duplicates += 1
            continue
        seen_in_batch.add(key)
        db.add(
            HealthSample(
                patient_id=patient_id,
                source=source,
                metric_type=s.metric_type,
                value=s.value,
                unit=s.unit or HEALTH_METRIC_UNITS.get(s.metric_type, ""),
                recorded_at=s.recorded_at,
            )
        )
        result.imported += 1
        result.metrics[s.metric_type.value] = result.metrics.get(s.metric_type.value, 0) + 1

    db.commit()
    return result


def build_summary(db: Session, patient_id: int) -> dict:
    """Per-metric overview: latest value, count, min/max/avg, source set."""
    rows = db.execute(
        select(
            HealthSample.metric_type,
            func.count(HealthSample.id),
            func.min(HealthSample.value),
            func.max(HealthSample.value),
            func.avg(HealthSample.value),
        )
        .where(HealthSample.patient_id == patient_id)
        .group_by(HealthSample.metric_type)
    ).all()

    metrics = []
    for metric_type, count, vmin, vmax, vavg in rows:
        latest = db.scalar(
            select(HealthSample)
            .where(
                HealthSample.patient_id == patient_id,
                HealthSample.metric_type == metric_type,
            )
            .order_by(HealthSample.recorded_at.desc())
            .limit(1)
        )
        metrics.append(
            {
                "metric_type": metric_type.value,
                "label": HEALTH_METRIC_LABELS.get(metric_type, metric_type.value),
                "unit": HEALTH_METRIC_UNITS.get(metric_type, ""),
                "count": int(count),
                "min": round(float(vmin), 2) if vmin is not None else None,
                "max": round(float(vmax), 2) if vmax is not None else None,
                "avg": round(float(vavg), 2) if vavg is not None else None,
                "latest_value": latest.value if latest else None,
                "latest_at": latest.recorded_at.isoformat() if latest else None,
            }
        )

    # Sources connected (distinct).
    sources = [
        s for (s,) in db.execute(
            select(HealthSample.source).where(
                HealthSample.patient_id == patient_id
            ).distinct()
        ).all()
    ]
    metrics.sort(key=lambda m: m["metric_type"])
    return {
        "total_samples": sum(m["count"] for m in metrics),
        "connected_sources": [s.value for s in sources],
        "metrics": metrics,
    }


def series(
    db: Session, patient_id: int, metric_type: HealthMetricType, limit: int = 500
) -> list[HealthSample]:
    return list(
        db.scalars(
            select(HealthSample)
            .where(
                HealthSample.patient_id == patient_id,
                HealthSample.metric_type == metric_type,
            )
            .order_by(HealthSample.recorded_at.asc())
            .limit(limit)
        ).all()
    )


def group_by_metric(samples: list[NormalizedSample]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for s in samples:
        counts[s.metric_type.value] += 1
    return dict(counts)
