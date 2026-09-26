"""Pick the places provider from settings, degrading to the offline mock."""
from __future__ import annotations

import logging

from app.core.config import settings
from app.services.places.base import PlacesProvider
from app.services.places.mock import MockPlacesProvider

logger = logging.getLogger(__name__)


def get_places_provider() -> PlacesProvider:
    """FastAPI dependency. Google when a key is set, otherwise the mock."""
    if not settings.GOOGLE_MAPS_API_KEY:
        return MockPlacesProvider()
    try:
        from app.services.places.google import GooglePlacesProvider

        return GooglePlacesProvider()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Google Places init failed: %s; using mock.", type(exc).__name__)
        return MockPlacesProvider()
