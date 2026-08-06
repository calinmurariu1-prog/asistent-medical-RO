"""Module 9 - medication interaction & duplicate checks.

Rule-based over a small curated knowledge base. This is intentionally NOT
exhaustive and is a decision-support aid only — it never replaces a doctor or
pharmacist. The KB is easy to extend and can later be augmented with an AI
provider or an external drug database (e.g. RxNorm / DrugBank).
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from app.models.medication import Medication

# Normalized-name pairs -> (severity, explanation). Severity: mild/moderate/severe.
_INTERACTIONS: dict[frozenset[str], tuple[str, str]] = {
    frozenset({"warfarina", "aspirina"}): (
        "severe",
        "Risc crescut de sângerare la administrarea concomitentă.",
    ),
    frozenset({"warfarina", "ibuprofen"}): (
        "severe",
        "AINS cresc riscul de sângerare la pacienții pe anticoagulant.",
    ),
    frozenset({"aspirina", "ibuprofen"}): (
        "moderate",
        "Ibuprofenul poate reduce efectul antiagregant al aspirinei.",
    ),
    frozenset({"simvastatina", "claritromicina"}): (
        "severe",
        "Risc crescut de miopatie/rabdomioliză (inhibiție CYP3A4).",
    ),
    frozenset({"enalapril", "spironolactona"}): (
        "moderate",
        "Risc de hiperkaliemie (potasiu crescut).",
    ),
    frozenset({"sertralina", "tramadol"}): (
        "severe",
        "Risc de sindrom serotoninergic.",
    ),
    frozenset({"metformin", "furosemid"}): (
        "mild",
        "Poate influența controlul glicemic; monitorizare recomandată.",
    ),
    frozenset({"levotiroxina", "omeprazol"}): (
        "moderate",
        "Reducerea acidității gastrice poate scădea absorbția levotiroxinei.",
    ),
}

DISCLAIMER = (
    "Verificarea este orientativă, bazată pe o listă limitată de interacțiuni "
    "cunoscute, și NU înlocuiește recomandarea medicului sau a farmacistului."
)


@dataclass
class InteractionWarning:
    drug_a: str
    drug_b: str
    severity: str
    description: str


@dataclass
class DuplicateWarning:
    substance: str
    medications: list[str]


@dataclass
class MedicationCheckResult:
    interactions: list[InteractionWarning]
    duplicates: list[DuplicateWarning]
    disclaimer: str = DISCLAIMER


def _normalize(name: str | None) -> str:
    if not name:
        return ""
    table = str.maketrans("ăâîșțĂÂÎȘȚ", "aaistAAIST")
    return name.strip().lower().translate(table)


def _key(med: Medication) -> str:
    """Prefer active substance; fall back to the commercial name."""
    return _normalize(med.active_substance) or _normalize(med.name)


def check_medications(meds: list[Medication]) -> MedicationCheckResult:
    active = [m for m in meds if m.is_active]

    interactions: list[InteractionWarning] = []
    for a, b in combinations(active, 2):
        pair = frozenset({_key(a), _key(b)})
        hit = _INTERACTIONS.get(pair)
        if hit and "" not in pair:
            severity, description = hit
            interactions.append(
                InteractionWarning(
                    drug_a=a.name,
                    drug_b=b.name,
                    severity=severity,
                    description=description,
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

    return MedicationCheckResult(interactions=interactions, duplicates=duplicates)
