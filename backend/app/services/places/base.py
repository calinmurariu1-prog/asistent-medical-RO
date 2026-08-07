"""Shared types and the provider interface for nearby-search."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class PlaceResult:
    name: str
    specialty: str
    address: str | None
    lat: float
    lng: float
    distance_km: float | None = None
    rating: float | None = None
    ratings_total: int | None = None
    place_id: str | None = None
    phone: str | None = None
    maps_url: str | None = None
    score: int | None = None
    score_label: str | None = None


class PlacesProvider(Protocol):
    name: str

    def geocode(self, query: str) -> tuple[float, float] | None:
        """Resolve a free-text location (city/address) to (lat, lng)."""
        ...

    def search_nearby(
        self,
        *,
        lat: float,
        lng: float,
        radius_m: int,
        specialty: str,
    ) -> list[PlaceResult]:
        """Find providers of `specialty` within `radius_m` of (lat, lng)."""
        ...
