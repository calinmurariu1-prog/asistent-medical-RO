"""Select the right importer for a health source."""
from __future__ import annotations

from app.models.enums import HealthSource
from app.services.health.apple import AppleHealthImporter
from app.services.health.base import HealthImporter
from app.services.health.google import GoogleHealthImporter
from app.services.health.huawei import HuaweiHealthImporter

_IMPORTERS: dict[HealthSource, type] = {
    HealthSource.APPLE_HEALTH: AppleHealthImporter,
    HealthSource.GOOGLE_HEALTH: GoogleHealthImporter,
    HealthSource.HUAWEI_HEALTH: HuaweiHealthImporter,
}


def get_importer(source: HealthSource) -> HealthImporter:
    importer_cls = _IMPORTERS.get(source)
    if importer_cls is None:
        raise ValueError(f"Sursă necunoscută: {source}")
    return importer_cls()
