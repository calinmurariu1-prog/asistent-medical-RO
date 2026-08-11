"""Import health metrics from Apple Health / Google Health / Huawei Health.

For a web app these platforms have no usable server API (Apple has none, Google
Fit is retiring in favour of on-device Health Connect, Huawei needs an approved
developer account), so data is imported from the export files the user generates
in each app. Uploaded data is normalized into canonical metrics and stored.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_patient
from app.core.database import get_db
from app.models.enums import HealthMetricType, HealthSource
from app.models.health import HealthSample
from app.models.patient import Patient
from app.schemas.health import (
    HealthDeviceOut,
    HealthImportJsonRequest,
    HealthSampleOut,
    HealthSourceInfo,
    HealthSummaryOut,
    ImportResultOut,
)
from app.services.health import devices as devices_service
from app.services.health import get_importer, service
from app.services.health.base import parse_generic_samples
from app.services.health.devices import DetectedDevice
from app.services.health.mock import sample_series

router = APIRouter(prefix="/health-data", tags=["health-data"])

MAX_SIZE_BYTES = 60 * 1024 * 1024  # 60 MB (Apple exports are large)

_SOURCE_META = {
    HealthSource.APPLE_HEALTH: {
        "label": "Apple Health",
        "how_to": (
            "În aplicația Sănătate (Health) → poza de profil → „Exportă toate "
            "datele”. Încarcă aici fișierul export.zip rezultat."
        ),
        "accepts": "export.zip / export.xml",
    },
    HealthSource.GOOGLE_HEALTH: {
        "label": "Google Health",
        "how_to": (
            "Din Google Takeout (takeout.google.com) exportă „Fit”, sau folosește "
            "exportul Health Connect. Încarcă aici fișierul JSON."
        ),
        "accepts": "JSON (Google Fit / Takeout / Health Connect)",
    },
    HealthSource.HUAWEI_HEALTH: {
        "label": "Huawei Health",
        "how_to": (
            "În Huawei Health → Setări → exportul de date personale. Încarcă aici "
            "fișierul JSON rezultat."
        ),
        "accepts": "JSON (Huawei Health Kit)",
    },
}


@router.get("/sources", response_model=list[HealthSourceInfo])
def list_sources(
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> list[HealthSourceInfo]:
    counts = dict(
        db.execute(
            select(HealthSample.source, func.count(HealthSample.id))
            .where(HealthSample.patient_id == patient.id)
            .group_by(HealthSample.source)
        ).all()
    )
    out = []
    for source, meta in _SOURCE_META.items():
        n = int(counts.get(source, 0))
        out.append(
            HealthSourceInfo(
                source=source,
                label=meta["label"],
                connected=n > 0,
                sample_count=n,
                how_to=meta["how_to"],
                accepts=meta["accepts"],
            )
        )
    return out


@router.get("/devices", response_model=list[HealthDeviceOut])
def list_devices(
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> list[HealthDeviceOut]:
    """Wearables auto-detected from the synced data (e.g. Apple Watch)."""
    import json

    out = []
    for d in devices_service.list_devices(db, patient.id):
        out.append(
            HealthDeviceOut(
                source=d.source,
                name=d.name,
                model=d.model,
                vendor=d.vendor,
                metrics=json.loads(d.metrics) if d.metrics else [],
                last_seen_at=d.last_seen_at.isoformat(),
            )
        )
    return out


@router.post("/import/{source}", response_model=ImportResultOut)
def import_health_data(
    source: HealthSource,
    file: UploadFile = File(...),
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> ImportResultOut:
    if source == HealthSource.MANUAL:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Sursă neacceptată la import.")

    data = file.file.read()
    if len(data) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Fișier gol.")
    if len(data) > MAX_SIZE_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Fișier prea mare (max {MAX_SIZE_BYTES // (1024 * 1024)} MB).",
        )

    importer = get_importer(source)
    try:
        samples = importer.parse(data, file.filename)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001  (malformed export -> clean 422)
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Nu am putut procesa fișierul. Verifică formatul exportului.",
        ) from exc

    result = service.persist_samples(db, patient.id, source, samples)
    if result.imported == 0 and result.duplicates == 0:
        message = (
            "Nu am găsit valori compatibile în fișier. Verifică sursa și formatul."
        )
    else:
        message = (
            f"{result.imported} valori importate"
            + (f", {result.duplicates} deja existente" if result.duplicates else "")
            + "."
        )
    return ImportResultOut(
        source=result.source,
        imported=result.imported,
        duplicates=result.duplicates,
        skipped=result.skipped,
        metrics=result.metrics,
        message=message,
    )


MAX_JSON_SAMPLES = 20_000


@router.post("/import-json/{source}", response_model=ImportResultOut)
def import_health_json(
    source: HealthSource,
    payload: HealthImportJsonRequest,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> ImportResultOut:
    """Ingest already-normalized samples (native HealthKit / Health Connect sync).

    The mobile app reads on-device health data, maps it to canonical metric
    types, and pushes it here — no file export needed.
    """
    if source == HealthSource.MANUAL:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Sursă neacceptată.")
    if len(payload.samples) > MAX_JSON_SAMPLES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Prea multe valori într-o cerere (max {MAX_JSON_SAMPLES}).",
        )

    samples = parse_generic_samples(
        {"samples": [s.model_dump() for s in payload.samples]}
    )
    result = service.persist_samples(db, patient.id, source, samples)

    # Auto-detect the wearables that produced the data.
    if payload.devices:
        devices_service.upsert_devices(
            db,
            patient.id,
            source,
            [
                DetectedDevice(
                    name=d.name, model=d.model, vendor=d.vendor, metrics=d.metrics
                )
                for d in payload.devices
            ],
        )

    message = (
        f"{result.imported} valori sincronizate"
        + (f", {result.duplicates} deja existente" if result.duplicates else "")
        + "."
        if (result.imported or result.duplicates)
        else "Nu am găsit valori compatibile."
    )
    return ImportResultOut(
        source=result.source,
        imported=result.imported,
        duplicates=result.duplicates,
        skipped=result.skipped,
        metrics=result.metrics,
        message=message,
    )


@router.post("/import-sample", response_model=ImportResultOut)
def import_sample_data(
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> ImportResultOut:
    """Load a small deterministic demo series (no real export needed)."""
    result = service.persist_samples(
        db, patient.id, HealthSource.MANUAL, sample_series()
    )
    return ImportResultOut(
        source=result.source,
        imported=result.imported,
        duplicates=result.duplicates,
        skipped=result.skipped,
        metrics=result.metrics,
        message=f"{result.imported} valori demo adăugate.",
    )


@router.get("/summary", response_model=HealthSummaryOut)
def health_summary(
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> HealthSummaryOut:
    return HealthSummaryOut(**service.build_summary(db, patient.id))


@router.get("/metrics/{metric_type}", response_model=list[HealthSampleOut])
def metric_series(
    metric_type: HealthMetricType,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> list[HealthSample]:
    return service.series(db, patient.id, metric_type)


@router.delete("/{source}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source_data(
    source: HealthSource,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    from fastapi import Response

    db.query(HealthSample).filter(
        HealthSample.patient_id == patient.id, HealthSample.source == source
    ).delete()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
