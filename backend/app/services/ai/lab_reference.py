"""Small offline knowledge base for common Romanian lab analytes.

Used to enrich the deterministic (mock) explanations so the app is genuinely
useful without an LLM key. Not exhaustive and NOT a diagnostic source — every
explanation is paired with a disclaimer downstream.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalyteInfo:
    label: str
    about: str
    high_meaning: str
    low_meaning: str


# Keys are normalized analyte names (lowercase, no diacritics handled by caller).
_REFERENCE: dict[str, AnalyteInfo] = {
    "glicemie": AnalyteInfo(
        "Glicemie",
        "Nivelul glucozei din sânge.",
        "Valorile crescute pot fi asociate cu prediabet sau diabet.",
        "Valorile scăzute (hipoglicemie) pot apărea la post prelungit sau tratament.",
    ),
    "hemoglobina": AnalyteInfo(
        "Hemoglobină",
        "Proteina din globulele roșii care transportă oxigenul.",
        "Valorile crescute pot apărea la deshidratare sau alte cauze.",
        "Valorile scăzute pot sugera anemie.",
    ),
    "colesterol total": AnalyteInfo(
        "Colesterol total",
        "Grăsime din sânge, relevantă pentru riscul cardiovascular.",
        "Valorile crescute pot crește riscul cardiovascular.",
        "Valorile scăzute sunt rareori o problemă în sine.",
    ),
    "ldl": AnalyteInfo(
        "LDL colesterol",
        "Colesterolul „rău”.",
        "Valorile crescute sunt asociate cu risc cardiovascular mai mare.",
        "Valorile scăzute sunt în general favorabile.",
    ),
    "hdl": AnalyteInfo(
        "HDL colesterol",
        "Colesterolul „bun”.",
        "Valorile crescute sunt în general protectoare.",
        "Valorile scăzute pot crește riscul cardiovascular.",
    ),
    "trigliceride": AnalyteInfo(
        "Trigliceride",
        "Un tip de grăsime din sânge.",
        "Valorile crescute pot fi asociate cu risc metabolic și cardiovascular.",
        "Valorile scăzute sunt rareori relevante clinic.",
    ),
    "tsh": AnalyteInfo(
        "TSH",
        "Hormonul care reglează activitatea tiroidei.",
        "Valorile crescute pot sugera hipotiroidism.",
        "Valorile scăzute pot sugera hipertiroidism.",
    ),
    "creatinina": AnalyteInfo(
        "Creatinină",
        "Marker al funcției renale.",
        "Valorile crescute pot indica o funcție renală redusă.",
        "Valorile scăzute au de obicei semnificație clinică redusă.",
    ),
    "hba1c": AnalyteInfo(
        "HbA1c",
        "Media glicemiei pe ultimele ~3 luni.",
        "Valorile crescute indică un control glicemic slab.",
        "Valorile scăzute pot apărea în anumite condiții.",
    ),
    "tgp": AnalyteInfo(
        "TGP (ALT)",
        "Enzimă hepatică.",
        "Valorile crescute pot indica afectare hepatică.",
        "Valorile scăzute sunt rareori relevante.",
    ),
    "tgo": AnalyteInfo(
        "TGO (AST)",
        "Enzimă hepatică și musculară.",
        "Valorile crescute pot indica afectare hepatică sau musculară.",
        "Valorile scăzute sunt rareori relevante.",
    ),
}

_ALIASES = {
    "colesterol": "colesterol total",
    "ldl colesterol": "ldl",
    "hdl colesterol": "hdl",
    "alt": "tgp",
    "ast": "tgo",
}


def _normalize(analyte: str) -> str:
    table = str.maketrans("ăâîșțĂÂÎȘȚ", "aaistAAIST")
    key = analyte.strip().lower().translate(table)
    return _ALIASES.get(key, key)


def lookup(analyte: str) -> AnalyteInfo | None:
    return _REFERENCE.get(_normalize(analyte))
