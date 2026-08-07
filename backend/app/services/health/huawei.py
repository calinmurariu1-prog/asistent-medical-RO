"""Huawei Health importer.

Huawei Health Kit's REST API requires an approved developer account + Huawei ID
OAuth, so the reliable web path is a file export. This importer reads the Huawei
Health Kit `sampleSet`/`samplePoints` JSON shape and falls back to the documented
generic normalized JSON shape.
"""
from __future__ import annotations

import json
import logging

from app.models.enums import HEALTH_METRIC_UNITS, HealthMetricType, HealthSource
from app.services.health.base import (
    NormalizedSample,
    parse_generic_samples,
    parse_timestamp,
    resolve_metric,
    to_float,
)

logger = logging.getLogger(__name__)

MT = HealthMetricType

# Huawei data-type integer codes -> our metric type (common subset).
_HUAWEI_TYPES: dict[int, HealthMetricType] = {
    257: MT.STEPS,               # DT_CONTINUOUS_STEPS_DELTA
    258: MT.DISTANCE,            # DT_CONTINUOUS_DISTANCE_DELTA
    259: MT.ACTIVE_ENERGY,       # DT_CONTINUOUS_CALORIES_BURNT
    260: MT.HEART_RATE,          # DT_INSTANTANEOUS_HEART_RATE
    280: MT.BODY_WEIGHT,         # DT_INSTANTANEOUS_BODY_WEIGHT
}

# Huawei field names -> metric type (used within a samplePoint's value list).
_HUAWEI_FIELDS: dict[str, HealthMetricType] = {
    "steps": MT.STEPS,
    "distance": MT.DISTANCE,
    "calories": MT.ACTIVE_ENERGY,
    "heart_rate": MT.HEART_RATE,
    "bpm": MT.HEART_RATE,
    "body_weight": MT.BODY_WEIGHT,
    "spo2": MT.OXYGEN_SATURATION,
    "systolic_pressure": MT.BLOOD_PRESSURE_SYSTOLIC,
    "diastolic_pressure": MT.BLOOD_PRESSURE_DIASTOLIC,
}


def _point_samples(point: dict, default_metric: HealthMetricType | None) -> list[NormalizedSample]:
    recorded_at = parse_timestamp(
        point.get("startTime") or point.get("startTimeNs") or point.get("time")
    )
    if recorded_at is None:
        return []
    out: list[NormalizedSample] = []
    values = point.get("value")
    if isinstance(values, list):
        for field in values:
            if not isinstance(field, dict):
                continue
            metric = (
                _HUAWEI_FIELDS.get(str(field.get("fieldName", "")).lower())
                or resolve_metric(field.get("fieldName"))
                or default_metric
            )
            val = to_float(
                field.get("floatValue")
                if field.get("floatValue") is not None
                else field.get("integerValue", field.get("value"))
            )
            if metric is not None and val is not None:
                out.append(
                    NormalizedSample(metric, val, HEALTH_METRIC_UNITS[metric], recorded_at)
                )
    else:
        val = to_float(point.get("value"))
        if default_metric is not None and val is not None:
            out.append(
                NormalizedSample(
                    default_metric, val, HEALTH_METRIC_UNITS[default_metric], recorded_at
                )
            )
    return out


class HuaweiHealthImporter:
    source = HealthSource.HUAWEI_HEALTH

    def parse(self, data: bytes, filename: str | None = None) -> list[NormalizedSample]:
        try:
            payload = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Fișier Huawei Health invalid (JSON așteptat).") from exc

        sample_sets = None
        if isinstance(payload, dict):
            sample_sets = payload.get("sampleSet") or payload.get("sampleSets")
        if sample_sets:
            out: list[NormalizedSample] = []
            for s in sample_sets:
                if not isinstance(s, dict):
                    continue
                default_metric = _HUAWEI_TYPES.get(int(s.get("dataTypeId", -1) or -1))
                for p in s.get("samplePoints", []):
                    if isinstance(p, dict):
                        out.extend(_point_samples(p, default_metric))
            if out:
                return out

        return parse_generic_samples(payload)
