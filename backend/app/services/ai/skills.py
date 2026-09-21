"""Discoverable skills with source-bound execution; never free-form medical completion."""
from __future__ import annotations

from dataclasses import dataclass

from app.services.ai.base import AIProvider
from app.services.ai.grounded_skills import run
from app.services.ai.medication_education import explain


@dataclass(frozen=True)
class Skill:
    name: str
    title: str
    description: str
    inputs: list[str]


_REGISTRY: dict[str, Skill] = {}


def register(skill: Skill) -> None:
    _REGISTRY[skill.name] = skill


def list_skills() -> list[Skill]:
    return list(_REGISTRY.values())


def get_skill(name: str) -> Skill | None:
    return _REGISTRY.get(name)


def run_skill_result(provider: AIProvider, skill: Skill, data: dict) -> dict:
    if skill.name == "explain_medication":
        return explain(provider, data["name"])
    return run(provider, skill.name, data)


def run_skill(provider: AIProvider, skill: Skill, data: dict) -> str:
    return run_skill_result(provider, skill, data)["result"]


for item in (
    Skill("explain_medication", "Explică un medicament",
          "Informații din catalogul educațional; introdu substanța activă, nu marca.", ["name"]),
    Skill("prepare_doctor_visit", "Pregătește vizita la medic",
          "Întrebări de pregătire, fără evaluare clinică.", ["concern"]),
    Skill("simplify_text", "Simplifică un text medical",
          "Reformulare cu citarea textului introdus; nu verifică adevărul medical.", ["text"]),
    Skill("lifestyle_tips", "Sfaturi de stil de viață",
          "Catalog inițial: diabet tip 2. Alte teme sunt încă neevaluate.", ["condition"]),
    Skill("review_prescription", "Verifică o rețetă",
          "Listă limitată: substanțe active separate prin punct și virgulă, fără doze.",
          ["medications"]),
    Skill("symptom_info", "Informații despre un simptom",
          "Catalog inițial: durere de cap, oboseală. Nu stabilește cauza simptomelor.",
          ["symptom"]),
):
    register(item)
