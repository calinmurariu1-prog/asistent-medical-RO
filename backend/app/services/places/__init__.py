"""Nearby medical-provider search (Google Places) with an offline mock."""
from app.services.places.base import PlaceResult, PlacesProvider
from app.services.places.factory import get_places_provider

__all__ = ["PlaceResult", "PlacesProvider", "get_places_provider"]
