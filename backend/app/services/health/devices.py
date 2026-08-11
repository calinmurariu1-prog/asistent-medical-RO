"""Detect & track wearables/health devices reported by the mobile app.

The native app reads the source device off each HealthKit / Health Connect sample
(e.g. "Apple Watch Series 9") and reports it here. We infer the brand and keep a
per-patient registry with last-seen time and the metrics each device provides.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import HealthSource
from app.models.health_device import HealthDevice

# name substring (lower-case) -> vendor brand.
_VENDOR_HINTS: list[tuple[str, str]] = [
    ("apple watch", "Apple"),
    ("iphone", "Apple"),
    ("ipad", "Apple"),
    ("galaxy watch", "Samsung"),
    ("galaxy fit", "Samsung"),
    ("samsung", "Samsung"),
    ("pixel watch", "Google"),
    ("fitbit", "Fitbit"),
    ("versa", "Fitbit"),
    ("charge", "Fitbit"),
    ("sense", "Fitbit"),
    ("garmin", "Garmin"),
    ("forerunner", "Garmin"),
    ("fenix", "Garmin"),
    ("venu", "Garmin"),
    ("vivoactive", "Garmin"),
    ("huawei", "Huawei"),
    ("watch gt", "Huawei"),
    ("honor", "Honor"),
    ("amazfit", "Amazfit"),
    ("zepp", "Amazfit"),
    ("mi band", "Xiaomi"),
    ("mi watch", "Xiaomi"),
    ("xiaomi", "Xiaomi"),
    ("redmi", "Xiaomi"),
    ("polar", "Polar"),
    ("withings", "Withings"),
    ("oura", "Oura"),
    ("wear os", "Wear OS"),
]


def infer_vendor(name: str) -> str | None:
    low = (name or "").lower()
    for hint, vendor in _VENDOR_HINTS:
        if hint in low:
            return vendor
    return None


@dataclass
class DetectedDevice:
    name: str
    model: str | None = None
    vendor: str | None = None
    metrics: list[str] = field(default_factory=list)


def upsert_devices(
    db: Session,
    patient_id: int,
    source: HealthSource,
    devices: list[DetectedDevice],
) -> int:
    """Create/update device rows; returns the number of distinct devices seen."""
    now = datetime.now(UTC)
    seen = 0
    for d in devices:
        name = (d.name or "").strip()
        if not name:
            continue
        seen += 1
        row = db.scalar(
            select(HealthDevice).where(
                HealthDevice.patient_id == patient_id,
                HealthDevice.source == source,
                HealthDevice.name == name,
            )
        )
        vendor = d.vendor or infer_vendor(name)
        metrics_json = json.dumps(sorted(set(d.metrics)), ensure_ascii=False)
        if row is None:
            db.add(
                HealthDevice(
                    patient_id=patient_id,
                    source=source,
                    name=name,
                    model=d.model,
                    vendor=vendor,
                    metrics=metrics_json,
                    sample_count=len(d.metrics),
                    last_seen_at=now,
                )
            )
        else:
            row.last_seen_at = now
            row.model = d.model or row.model
            row.vendor = vendor or row.vendor
            # Merge metric sets across syncs.
            existing = set(json.loads(row.metrics) if row.metrics else [])
            existing.update(d.metrics)
            row.metrics = json.dumps(sorted(existing), ensure_ascii=False)
            db.add(row)
    if seen:
        db.commit()
    return seen


def list_devices(db: Session, patient_id: int) -> list[HealthDevice]:
    return list(
        db.scalars(
            select(HealthDevice)
            .where(HealthDevice.patient_id == patient_id)
            .order_by(HealthDevice.last_seen_at.desc())
        ).all()
    )
