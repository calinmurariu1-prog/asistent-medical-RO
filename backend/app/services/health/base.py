"""Shared types and the importer interface for health-platform data.

Every provider (Apple Health / Google Health / Huawei Health) parses its own
export format and yields a stream of `NormalizedSample`s using the canonical
`HealthMetricType` + unit. The rest of the app never sees vendor codes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from app.models.enums import HealthMetricType, HealthSource


@dataclass(frozen=True)
class NormalizedSample:
    metric_type: HealthMetricType
    value: float
    unit: str
    recorded_at: datetime


@dataclass
class ImportResult:
    source: HealthSource
    imported: int = 0            # rows actually inserted
    duplicates: int = 0          # skipped because already present
    skipped: int = 0            # unrecognised / unparseable entries
    metrics: dict[str, int] = field(default_factory=dict)  # per metric_type count


class HealthImporter(Protocol):
    """Parse a raw export payload into normalized samples."""

    source: HealthSource

    def parse(self, data: bytes, filename: str | None = None) -> list[NormalizedSample]:
        ...


# ---------------------------------------------------------------------------
# Helpers shared by the concrete importers
# ---------------------------------------------------------------------------
def parse_timestamp(raw: object) -> datetime | None:
    """Best-effort parse of the many timestamp shapes health exports use."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=UTC)
    if isinstance(raw, (int, float)):
        # Heuristic: ns > ms > s by magnitude.
        v = float(raw)
        if v > 1e17:      # nanoseconds
            v /= 1e9
        elif v > 1e14:    # microseconds
            v /= 1e6
        elif v > 1e11:    # milliseconds
            v /= 1e3
        try:
            return datetime.fromtimestamp(v, tz=UTC)
        except (OverflowError, OSError, ValueError):
            return None
    s = str(raw).strip()
    if not s:
        return None
    # Numeric string epoch (Google Fit sends nanos as a string).
    if s.lstrip("-").isdigit():
        return parse_timestamp(int(s))
    # Apple: "2024-01-01 08:00:00 +0000"
    for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except ValueError:
            pass
    # ISO 8601 (allow trailing Z)
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except ValueError:
        return None


def to_float(raw: object) -> float | None:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        return float(str(raw).replace(",", "."))
    except (TypeError, ValueError):
        return None


# Common human/vendor aliases -> canonical metric type. Used by the generic
# JSON fallback so a plain export still maps onto known metrics.
_METRIC_ALIASES: dict[str, HealthMetricType] = {}
for _mt in HealthMetricType:
    _METRIC_ALIASES[_mt.value] = _mt
    _METRIC_ALIASES[_mt.value.replace("_", "")] = _mt
_METRIC_ALIASES.update({
    "step": HealthMetricType.STEPS,
    "steps_count": HealthMetricType.STEPS,
    "hr": HealthMetricType.HEART_RATE,
    "heartrate": HealthMetricType.HEART_RATE,
    "bpm": HealthMetricType.HEART_RATE,
    "pulse": HealthMetricType.HEART_RATE,
    "puls": HealthMetricType.HEART_RATE,
    "resting_hr": HealthMetricType.RESTING_HEART_RATE,
    "systolic": HealthMetricType.BLOOD_PRESSURE_SYSTOLIC,
    "bp_systolic": HealthMetricType.BLOOD_PRESSURE_SYSTOLIC,
    "diastolic": HealthMetricType.BLOOD_PRESSURE_DIASTOLIC,
    "bp_diastolic": HealthMetricType.BLOOD_PRESSURE_DIASTOLIC,
    "glucose": HealthMetricType.BLOOD_GLUCOSE,
    "glicemie": HealthMetricType.BLOOD_GLUCOSE,
    "spo2": HealthMetricType.OXYGEN_SATURATION,
    "oxygen": HealthMetricType.OXYGEN_SATURATION,
    "weight": HealthMetricType.BODY_WEIGHT,
    "greutate": HealthMetricType.BODY_WEIGHT,
    "mass": HealthMetricType.BODY_WEIGHT,
    "fat": HealthMetricType.BODY_FAT,
    "temperature": HealthMetricType.BODY_TEMPERATURE,
    "temperatura": HealthMetricType.BODY_TEMPERATURE,
    "respiratory": HealthMetricType.RESPIRATORY_RATE,
    "calories": HealthMetricType.ACTIVE_ENERGY,
    "energy": HealthMetricType.ACTIVE_ENERGY,
    "distance": HealthMetricType.DISTANCE,
})


def resolve_metric(name: object) -> HealthMetricType | None:
    if name is None:
        return None
    return _METRIC_ALIASES.get(str(name).strip().lower())


def parse_generic_samples(payload: object) -> list[NormalizedSample]:
    """Parse the documented normalized JSON shape:

        {"samples": [{"type","value","unit","recorded_at"}, ...]}

    or a bare list of the same objects. Unknown metric types are skipped.
    """
    from app.models.enums import HEALTH_METRIC_UNITS

    if isinstance(payload, dict):
        rows = payload.get("samples") or payload.get("data") or []
    elif isinstance(payload, list):
        rows = payload
    else:
        rows = []

    out: list[NormalizedSample] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        metric = resolve_metric(row.get("type") or row.get("metric") or row.get("name"))
        value = to_float(row.get("value"))
        recorded_at = parse_timestamp(
            row.get("recorded_at")
            or row.get("timestamp")
            or row.get("date")
            or row.get("start")
        )
        if metric is None or value is None or recorded_at is None:
            continue
        out.append(
            NormalizedSample(
                metric_type=metric,
                value=value,
                unit=str(row.get("unit") or HEALTH_METRIC_UNITS[metric]),
                recorded_at=recorded_at,
            )
        )
    return out
