"""Apple Health importer.

Apple has no web API: users export their data from the Health app
(Profil → Exportă toate datele) which produces `export.zip` containing
`export.xml`. This importer accepts either the `.zip` or the raw `.xml`, and
streams the (potentially very large) XML with `iterparse` to keep memory flat.
"""
from __future__ import annotations

import io
import logging
import zipfile
from collections.abc import Iterator
from xml.etree.ElementTree import iterparse

from app.models.enums import HEALTH_METRIC_UNITS, HealthMetricType, HealthSource
from app.services.health.base import NormalizedSample, parse_timestamp, to_float

logger = logging.getLogger(__name__)

MT = HealthMetricType

# Apple HKQuantityTypeIdentifier<X> / HKCategoryTypeIdentifier<X>  ->  our type
_APPLE_TYPES: dict[str, HealthMetricType] = {
    "HKQuantityTypeIdentifierStepCount": MT.STEPS,
    "HKQuantityTypeIdentifierHeartRate": MT.HEART_RATE,
    "HKQuantityTypeIdentifierRestingHeartRate": MT.RESTING_HEART_RATE,
    "HKQuantityTypeIdentifierBloodPressureSystolic": MT.BLOOD_PRESSURE_SYSTOLIC,
    "HKQuantityTypeIdentifierBloodPressureDiastolic": MT.BLOOD_PRESSURE_DIASTOLIC,
    "HKQuantityTypeIdentifierBloodGlucose": MT.BLOOD_GLUCOSE,
    "HKQuantityTypeIdentifierOxygenSaturation": MT.OXYGEN_SATURATION,
    "HKQuantityTypeIdentifierBodyMass": MT.BODY_WEIGHT,
    "HKQuantityTypeIdentifierHeight": MT.HEIGHT,
    "HKQuantityTypeIdentifierBodyFatPercentage": MT.BODY_FAT,
    "HKQuantityTypeIdentifierBodyTemperature": MT.BODY_TEMPERATURE,
    "HKQuantityTypeIdentifierRespiratoryRate": MT.RESPIRATORY_RATE,
    "HKQuantityTypeIdentifierActiveEnergyBurned": MT.ACTIVE_ENERGY,
    "HKQuantityTypeIdentifierDistanceWalkingRunning": MT.DISTANCE,
    "HKQuantityTypeIdentifierVO2Max": MT.VO2MAX,
}


def _convert(metric: HealthMetricType, value: float, unit: str) -> float:
    """Convert an Apple value+unit into our canonical unit."""
    u = (unit or "").strip().lower()
    if metric in (MT.OXYGEN_SATURATION, MT.BODY_FAT) and value <= 1.0:
        return value * 100.0                       # fraction -> %
    if metric == MT.BODY_WEIGHT and u in ("lb", "lbs"):
        return value * 0.45359237
    if metric == MT.HEIGHT:
        if u in ("m",):
            return value * 100.0
        if u in ("in",):
            return value * 2.54
        if u in ("ft",):
            return value * 30.48
    if metric == MT.BODY_TEMPERATURE and u in ("degf", "°f", "f"):
        return (value - 32.0) * 5.0 / 9.0
    if metric == MT.DISTANCE:
        if u in ("m",):
            return value / 1000.0
        if u in ("mi",):
            return value * 1.609344
    if metric == MT.BLOOD_GLUCOSE and "mmol" in u:
        return value * 18.0182
    return value


def _open_xml(data: bytes, filename: str | None) -> io.BufferedIOBase:
    """Return a binary stream over export.xml, unwrapping a .zip if needed."""
    looks_zip = data[:2] == b"PK" or (filename or "").lower().endswith(".zip")
    if looks_zip:
        zf = zipfile.ZipFile(io.BytesIO(data))
        name = next(
            (n for n in zf.namelist() if n.endswith("export.xml")),
            None,
        )
        if name is None:
            raise ValueError("Arhiva nu conține export.xml (export Apple Health).")
        return zf.open(name)
    return io.BytesIO(data)


def _iter_records(stream: io.BufferedIOBase) -> Iterator[NormalizedSample]:
    for _event, elem in iterparse(stream, events=("end",)):
        if elem.tag != "Record":
            continue
        rtype = elem.get("type")
        metric = _APPLE_TYPES.get(rtype or "")
        if metric is not None:
            value = to_float(elem.get("value"))
            recorded_at = parse_timestamp(
                elem.get("startDate") or elem.get("endDate") or elem.get("creationDate")
            )
            if value is not None and recorded_at is not None:
                yield NormalizedSample(
                    metric_type=metric,
                    value=round(_convert(metric, value, elem.get("unit") or ""), 4),
                    unit=HEALTH_METRIC_UNITS[metric],
                    recorded_at=recorded_at,
                )
        elif rtype == "HKCategoryTypeIdentifierSleepAnalysis":
            sample = _sleep_sample(elem)
            if sample is not None:
                yield sample
        # Free the element (and its now-processed children) to keep memory flat.
        elem.clear()


def _sleep_sample(elem) -> NormalizedSample | None:
    """Turn an 'asleep' sleep-analysis record into minutes of sleep."""
    if "Asleep" not in (elem.get("value") or ""):
        return None
    start = parse_timestamp(elem.get("startDate"))
    end = parse_timestamp(elem.get("endDate"))
    if start is None or end is None:
        return None
    minutes = (end - start).total_seconds() / 60.0
    if minutes <= 0:
        return None
    return NormalizedSample(
        metric_type=MT.SLEEP,
        value=round(minutes, 2),
        unit=HEALTH_METRIC_UNITS[MT.SLEEP],
        recorded_at=start,
    )


class AppleHealthImporter:
    source = HealthSource.APPLE_HEALTH

    def parse(self, data: bytes, filename: str | None = None) -> list[NormalizedSample]:
        stream = _open_xml(data, filename)
        try:
            return list(_iter_records(stream))
        finally:
            stream.close()
