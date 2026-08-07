"""Offline provider: deterministic fake clinics near the given point.

Lets the whole feature work in dev/tests/demo without a Google API key.
"""
from __future__ import annotations

import hashlib
from urllib.parse import quote_plus

from app.services.geo import haversine_km
from app.services.places.base import PlaceResult

# Bucharest center — used as the geocode fallback for any city string.
_DEFAULT_COORDS = (44.4268, 26.1025)

_STREETS = [
    "Str. Sănătății 12",
    "Bd. Independenței 45",
    "Str. Doctorilor 8",
    "Calea Victoriei 120",
    "Str. Spitalului 3",
]


def _seed(specialty: str, lat: float, lng: float) -> int:
    raw = f"{specialty}:{lat:.3f}:{lng:.3f}".encode()
    return int(hashlib.md5(raw).hexdigest(), 16)


class MockPlacesProvider:
    name = "mock"

    def geocode(self, query: str) -> tuple[float, float] | None:
        return _DEFAULT_COORDS

    def search_nearby(
        self, *, lat: float, lng: float, radius_m: int, specialty: str
    ) -> list[PlaceResult]:
        seed = _seed(specialty, lat, lng)
        results: list[PlaceResult] = []
        for i in range(4):
            # Spread points a few hundred metres around the origin.
            d_lat = ((seed >> (i * 3)) % 7 - 3) * 0.004
            d_lng = ((seed >> (i * 3 + 1)) % 7 - 3) * 0.004
            plat, plng = lat + d_lat, lng + d_lng
            dist = haversine_km(lat, lng, plat, plng)
            if dist * 1000 > radius_m:
                continue
            name = f"Cabinet {specialty} {_STREETS[i % len(_STREETS)].split()[-1]}"
            results.append(
                PlaceResult(
                    name=name,
                    specialty=specialty,
                    address=_STREETS[i % len(_STREETS)],
                    lat=plat,
                    lng=plng,
                    distance_km=dist,
                    rating=round(3.8 + ((seed >> i) % 12) / 10, 1),
                    ratings_total=20 + (seed >> i) % 300,
                    place_id=f"mock_{seed % 100000}_{i}",
                    phone="+40 21 000 0000",
                    maps_url=(
                        "https://www.google.com/maps/search/?api=1&query="
                        + quote_plus(f"{name} {plat},{plng}")
                    ),
                )
            )
        results.sort(key=lambda r: r.distance_km or 0)
        return results
