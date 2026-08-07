"""Google Health importer (Google Fit / Health Connect / Takeout export).

Google Fit's REST API is being retired in favour of Health Connect (on-device,
Android only), so the reliable web path is a file export. This importer reads
Google Fit "derived" JSON (a `Data Points` array with `dataTypeName` + `fitValue`)
and falls back to the documented generic normalized JSON shape.
"""
from __future__ import annotations

import json
import logging

from app.models.enums import HEALTH_METRIC_UNITS, HealthMetricType, HealthSource
from app.services.health.base import (
    NormalizedSample,
    parse_generic_samples,
    parse_timestamp,
)

logger = logging.getLogger(__name__)

MT = HealthMetricType

_GOOGLE_TYPES: dict[str, HealthMetricType] = {
    "com.google.step_count.delta": MT.STEPS,
    "com.google.step_count.cumulative": MT.STEPS,
    "com.google.heart_rate.bpm": MT.HEART_RATE,
    "com.google.heart_rate.resting": MT.RESTING_HEART_RATE,
    "com.google.weight": MT.BODY_WEIGHT,
    "com.google.height": MT.HEIGHT,
    "com.google.blood_glucose": MT.BLOOD_GLUCOSE,
    "com.google.oxygen_saturation": MT.OXYGEN_SATURATION,
    "com.google.body.fat.percentage": MT.BODY_FAT,
    "com.google.body.temperature": MT.BODY_TEMPERATURE,
    "com.google.respiratory_rate": MT.RESPIRATORY_RATE,
    "com.google.calories.expended": MT.ACTIVE_ENERGY,
    "com.google.distance.delta": MT.DISTANCE,
}


def _num(fitvalue: dict) -> float | None:
    v = fitvalue.get("value", fitvalue)
    if not isinstance(v, dict):
        return None
    if v.get("fpVal") is not None:
        return float(v["fpVal"])
    if v.get("intVal") is not None:
        return float(v["intVal"])
    return None


def _convert(metric: HealthMetricType, value: float) -> float:
    if metric == MT.HEIGHT and value < 3:        # metres -> cm
        return value * 100.0
    if metric == MT.DISTANCE and value > 100:    # metres -> km
        return value / 1000.0
    if metric == MT.BLOOD_GLUCOSE and value < 40:  # mmol/L -> mg/dL
        return value * 18.0182
    return value


def _point_samples(point: dict) -> list[NormalizedSample]:
    dtype = point.get("dataTypeName") or point.get("originDataSourceId", "")
    recorded_at = parse_timestamp(
        point.get("startTimeNanos") or point.get("startTimeMillis") or point.get("startTime")
    )
    fitvals = point.get("fitValue") or point.get("value") or []
    if recorded_at is None or not fitvals:
        return []

    # Blood pressure carries systolic + diastolic in one point.
    if dtype == "com.google.blood_pressure" and len(fitvals) >= 2:
        out = []
        for idx, mt in (
            (0, MT.BLOOD_PRESSURE_SYSTOLIC),
            (1, MT.BLOOD_PRESSURE_DIASTOLIC),
        ):
            val = _num(fitvals[idx])
            if val is not None:
                out.append(
                    NormalizedSample(mt, round(val, 4), HEALTH_METRIC_UNITS[mt], recorded_at)
                )
        return out

    metric = _GOOGLE_TYPES.get(dtype)
    if metric is None:
        return []
    val = _num(fitvals[0])
    if val is None:
        return []
    return [
        NormalizedSample(
            metric, round(_convert(metric, val), 4), HEALTH_METRIC_UNITS[metric], recorded_at
        )
    ]


class GoogleHealthImporter:
    source = HealthSource.GOOGLE_HEALTH

    def parse(self, data: bytes, filename: str | None = None) -> list[NormalizedSample]:
        try:
            payload = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Fișier Google Health invalid (JSON așteptat).") from exc

        points = None
        if isinstance(payload, dict):
            points = payload.get("Data Points") or payload.get("dataPoints")
        if points:
            out: list[NormalizedSample] = []
            for p in points:
                if isinstance(p, dict):
                    out.extend(_point_samples(p))
            if out:
                return out

        return parse_generic_samples(payload)
