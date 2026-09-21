"""Module 9 - medication interaction & duplicate checks.

Rule-based over a small source-linked educational catalog. This is intentionally NOT
exhaustive and is a decision-support aid only — it never replaces a doctor or
pharmacist. The KB is easy to extend and can later be augmented with an AI
provider or an external drug database (e.g. RxNorm / DrugBank).
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from app.models.medication import Medication

# Educational catalog, source-checked 2026-09-21; not clinically validated.
# No severity scoring, dose assessment, brand inference or network lookup.
_SOURCE_DATE = "2026-09-21"
_INTERACTIONS: dict[frozenset[str], tuple[str, str, str]] = {
    frozenset({"warfarina", "aspirina"}): (
        "NHS menționează aspirina printre medicamentele care pot interacționa cu warfarina.",
        "NHS — Warfarin", "https://www.nhs.uk/medicines/warfarin/",
    ),
    frozenset({"warfarina", "ibuprofen"}): (
        "NHS menționează ibuprofenul printre medicamentele care pot interacționa cu warfarina.",
        "NHS — Warfarin", "https://www.nhs.uk/medicines/warfarin/",
    ),
    frozenset({"aspirina", "ibuprofen"}): (
        "NHS semnalează posibile interacțiuni între aspirină și alte antiinflamatoare, "
        "inclusiv ibuprofen.",
        "NHS — Aspirin", "https://www.nhs.uk/medicines/aspirin/",
    ),
    frozenset({"simvastatina", "claritromicina"}): (
        "NHS SPS descrie asocierea claritromicinei cu simvastatina ca fiind contraindicată. "
        "Cere verificarea tratamentului de către medic sau farmacist.",
        "NHS SPS — Macrolides and statins",
        "https://sps.nhs.uk/articles/managing-interactions-between-macrolides-and-statins/",
    ),
    frozenset({"levotiroxina", "omeprazol"}): (
        "NHS menționează omeprazolul printre medicamentele care pot interacționa cu levotiroxina.",
        "NHS — Levothyroxine", "https://www.nhs.uk/medicines/levothyroxine/",
    ),
}
_ALIASES = {
    "warfarin": "warfarina", "aspirin": "aspirina", "acid acetilsalicilic": "aspirina",
    "simvastatin": "simvastatina", "clarithromycin": "claritromicina",
    "levothyroxine": "levotiroxina", "omeprazole": "omeprazol",
}
_KNOWN = set().union(*_INTERACTIONS)

DISCLAIMER = (
    "Verificarea este orientativă, bazată pe o listă limitată de interacțiuni "
    "cunoscute, și NU înlocuiește recomandarea medicului sau a farmacistului. "
    "Lipsa unei alerte nu confirmă siguranța. Nu modifica tratamentul pe baza aplicației. "
    "Dozele, bolile asociate și combinațiile de substanțe nu sunt evaluate."
)


@dataclass
class InteractionWarning:
    drug_a: str
    drug_b: str
    severity: str
    description: str
    source_title: str
    source_url: str
    source_checked_on: str


@dataclass
class DuplicateWarning:
    substance: str
    medications: list[str]


@dataclass
class MedicationCheckResult:
    interactions: list[InteractionWarning]
    duplicates: list[DuplicateWarning]
    unassessed_pairs: int
    unidentified_medications: list[str]
    disclaimer: str = DISCLAIMER


def _normalize(name: str | None) -> str:
    if not name:
        return ""
    table = str.maketrans("ăâîșțĂÂÎȘȚ", "aaistAAIST")
    return name.strip().lower().translate(table)


def _key(med: Medication) -> str:
    """Only explicit substance labels; never guess ingredients from brands."""
    value = _normalize(med.active_substance)
    return _ALIASES.get(value, value)


def check_medications(meds: list[Medication]) -> MedicationCheckResult:
    active = [m for m in meds if m.is_active]

    interactions: list[InteractionWarning] = []
    for a, b in combinations(active, 2):
        pair = frozenset({_key(a), _key(b)})
        hit = _INTERACTIONS.get(pair)
        if hit and "" not in pair:
            description, source_title, source_url = hit
            interactions.append(
                InteractionWarning(
                    drug_a=a.name,
                    drug_b=b.name,
                    severity="requires_review",
                    description=description,
                    source_title=source_title,
                    source_url=source_url,
                    source_checked_on=_SOURCE_DATE,
                )
            )

    by_substance: dict[str, list[str]] = {}
    for m in active:
        key = _key(m)
        if key:
            by_substance.setdefault(key, []).append(m.name)
    duplicates = [
        DuplicateWarning(substance=sub, medications=names)
        for sub, names in by_substance.items()
        if len(names) > 1
    ]

    return MedicationCheckResult(
        interactions=interactions, duplicates=duplicates,
        unassessed_pairs=len(active) * (len(active) - 1) // 2 - len(interactions),
        unidentified_medications=[m.name for m in active if _key(m) not in _KNOWN],
    )
