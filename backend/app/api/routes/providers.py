"""Find doctors near the patient for the problems detected in their record."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_patient
from app.core.config import settings
from app.core.database import get_db
from app.models.patient import Patient
from app.schemas.provider import (
    NearbyProvidersOut,
    ProviderOut,
    SpecialtySuggestionOut,
)
from app.services import specialty_map
from app.services.places import PlacesProvider, get_places_provider

router = APIRouter(prefix="/providers", tags=["providers"])

_DISCLAIMER = (
    "Rezultatele provin dintr-o sursă externă de hărți și au caracter "
    "informativ. Verifică disponibilitatea și acreditarea medicului direct."
)


@router.get("/suggested-specialties", response_model=list[SpecialtySuggestionOut])
def suggested_specialties(
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> list[SpecialtySuggestionOut]:
    return [
        SpecialtySuggestionOut(specialty=s.specialty, reasons=s.reasons)
        for s in specialty_map.specialties_for_patient(db, patient)
    ]


@router.get("/nearby", response_model=NearbyProvidersOut)
def nearby(
    lat: float | None = Query(default=None, ge=-90, le=90),
    lng: float | None = Query(default=None, ge=-180, le=180),
    city: str | None = None,
    specialty: str | None = None,
    radius_m: int | None = Query(default=None, ge=100, le=50000),
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
    places: PlacesProvider = Depends(get_places_provider),
) -> NearbyProvidersOut:
    # Resolve the search center: explicit coordinates, else geocode the city.
    if lat is None or lng is None:
        if not city:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Trimite lat & lng (din GPS) sau un oraș.",
            )
        coords = places.geocode(city)
        if coords is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Locație negăsită.")
        lat, lng = coords

    # Resolve the specialty: explicit, else the top suggestion from the record.
    if not specialty:
        suggestions = specialty_map.specialties_for_patient(db, patient)
        specialty = suggestions[0].specialty

    radius = radius_m or settings.PLACES_DEFAULT_RADIUS_M
    results = places.search_nearby(
        lat=lat, lng=lng, radius_m=radius, specialty=specialty
    )
    return NearbyProvidersOut(
        specialty=specialty,
        center={"lat": lat, "lng": lng},
        radius_m=radius,
        provider_source=places.name,
        results=[ProviderOut(**r.__dict__) for r in results],
        disclaimer=_DISCLAIMER,
    )
