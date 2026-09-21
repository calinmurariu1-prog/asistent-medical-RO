"""Google Places (New) + Geocoding provider. Runs server-side with a secret key."""
from __future__ import annotations

import logging

from app.core.config import settings
from app.services.geo import haversine_km
from app.services.places.base import PlaceResult

logger = logging.getLogger(__name__)

_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
_FIELD_MASK = ",".join(
    [
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.rating",
        "places.userRatingCount",
        "places.id",
        "places.internationalPhoneNumber",
        "places.googleMapsUri",
    ]
)


class GooglePlacesProvider:
    name = "google"

    def __init__(self) -> None:
        self._key = settings.GOOGLE_MAPS_API_KEY

    def geocode(self, query: str) -> tuple[float, float] | None:
        import httpx

        try:
            resp = httpx.get(
                _GEOCODE_URL,
                params={"address": query, "key": self._key},
                timeout=10,
            )
            data = resp.json()
            loc = data["results"][0]["geometry"]["location"]
            return float(loc["lat"]), float(loc["lng"])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Geocoding failed (%s)", type(exc).__name__)
            return None

    def search_nearby(
        self, *, lat: float, lng: float, radius_m: int, specialty: str
    ) -> list[PlaceResult]:
        import httpx

        body = {
            "textQuery": f"{specialty} cabinet clinică",
            "includedType": "doctor",
            "maxResultCount": settings.PLACES_MAX_RESULTS,
            "locationBias": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": float(radius_m),
                }
            },
        }
        try:
            resp = httpx.post(
                _SEARCH_URL,
                json=body,
                headers={
                    "X-Goog-Api-Key": self._key,
                    "X-Goog-FieldMask": _FIELD_MASK,
                },
                timeout=12,
            )
            places = resp.json().get("places", [])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Places search failed: %s", type(exc).__name__)
            return []

        results: list[PlaceResult] = []
        for p in places:
            loc = p.get("location", {})
            plat, plng = loc.get("latitude"), loc.get("longitude")
            if plat is None or plng is None:
                continue
            results.append(
                PlaceResult(
                    name=(p.get("displayName") or {}).get("text", "Cabinet medical"),
                    specialty=specialty,
                    address=p.get("formattedAddress"),
                    lat=float(plat),
                    lng=float(plng),
                    distance_km=haversine_km(lat, lng, float(plat), float(plng)),
                    rating=p.get("rating"),
                    ratings_total=p.get("userRatingCount"),
                    place_id=p.get("id"),
                    phone=p.get("internationalPhoneNumber"),
                    maps_url=p.get("googleMapsUri"),
                )
            )
        results.sort(key=lambda r: r.distance_km or 0)
        return results
