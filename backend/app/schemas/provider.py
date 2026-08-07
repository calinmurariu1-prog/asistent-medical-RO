"""Schemas for specialty suggestions and nearby providers."""
from __future__ import annotations

from pydantic import BaseModel


class SpecialtySuggestionOut(BaseModel):
    specialty: str
    reasons: list[str]


class ProviderOut(BaseModel):
    name: str
    specialty: str
    address: str | None
    lat: float
    lng: float
    distance_km: float | None
    rating: float | None
    ratings_total: int | None
    place_id: str | None
    phone: str | None
    maps_url: str | None


class NearbyProvidersOut(BaseModel):
    specialty: str
    center: dict[str, float]
    radius_m: int
    provider_source: str
    results: list[ProviderOut]
    disclaimer: str
