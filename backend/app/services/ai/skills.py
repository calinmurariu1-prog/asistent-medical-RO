"""Medical AI skills — discrete, reusable AI capabilities.

Each skill declares its inputs, builds a guarded prompt, and provides a
deterministic offline `mock` output so the feature works without an API key.
Add a new capability by registering another `Skill` — nothing else changes.

All skills are informational only: no diagnosis, no prescription, disclaimer
appended to every result.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.services.ai.base import DISCLAIMER, AIProvider

_GUARD = (
    "Ești un asistent medical informativ, în limba română. NU pui diagnostic și "
    "NU prescrii tratament. Oferă informații orientative, clare și empatice, și "
    "recomandă consultarea medicului pentru decizii."
)


@dataclass(frozen=True)
class Skill:
    name: str
    title: str
    description: str
    inputs: list[str]
    prompt: Callable[[dict], tuple[str, str]]  # -> (system, user)
    mock: Callable[[dict], str]


_REGISTRY: dict[str, Skill] = {}


def register(skill: Skill) -> None:
    _REGISTRY[skill.name] = skill


def list_skills() -> list[Skill]:
    return list(_REGISTRY.values())


def get_skill(name: str) -> Skill | None:
    return _REGISTRY.get(name)


def _with_disclaimer(text: str) -> str:
    return text if "orientativ" in text.lower() else f"{text}\n\n{DISCLAIMER}"


def run_skill(provider: AIProvider, skill: Skill, data: dict) -> str:
    """Execute a skill: deterministic mock for the offline provider, else LLM."""
    if getattr(provider, "name", "") == "mock":
        return _with_disclaimer(skill.mock(data))
    system, user = skill.prompt(data)
    return _with_disclaimer(provider.complete(system=system, user=user))


# --------------------------------------------------------------------------
# Skill definitions
# --------------------------------------------------------------------------
register(
    Skill(
        name="explain_medication",
        title="Explică un medicament",
        description="Explică pe înțeles pentru ce se folosește un medicament.",
        inputs=["name"],
        prompt=lambda d: (
            _GUARD,
            f"Explică pe scurt medicamentul „{d['name']}”: pentru ce se folosește "
            "în general, cum se administrează uzual și la ce reacții adverse "
            "frecvente să fie atent pacientul. Nu recomanda doze specifice.",
        ),
        mock=lambda d: (
            f"„{d['name']}” este un medicament. În general, medicamentele se iau "
            "conform indicațiilor din prospect și ale medicului. Fii atent la "
            "reacțiile adverse menționate în prospect și la interacțiuni cu alte "
            "medicamente. Pentru indicație, doză și durată, întreabă medicul sau "
            "farmacistul."
        ),
    )
)

register(
    Skill(
        name="prepare_doctor_visit",
        title="Pregătește vizita la medic",
        description="Generează întrebări utile de pus medicului pentru o preocupare.",
        inputs=["concern"],
        prompt=lambda d: (
            _GUARD,
            f"Pacientul are următoarea preocupare: „{d['concern']}”. Propune 5 "
            "întrebări utile de pus medicului și ce informații să pregătească "
            "pentru consultație.",
        ),
        mock=lambda d: (
            f"Pentru „{d['concern']}”, poți întreba medicul:\n"
            "1. Care ar putea fi cauzele acestor simptome?\n"
            "2. Ce investigații sunt recomandate?\n"
            "3. Cât timp ar trebui să dureze/monitorizez?\n"
            "4. Ce semne de alarmă necesită revenire urgentă?\n"
            "5. Ce pot face acasă între timp?\n"
            "Pregătește: de când au apărut, ce le agravează/ameliorează, "
            "medicamentele curente și analizele recente."
        ),
    )
)

register(
    Skill(
        name="simplify_text",
        title="Simplifică un text medical",
        description="Rescrie un text medical în limbaj simplu, pe înțelesul pacientului.",
        inputs=["text"],
        prompt=lambda d: (
            _GUARD,
            "Rescrie următorul text medical în limbaj simplu, pe înțelesul unui "
            f"pacient, păstrând informația esențială:\n\n{d['text']}",
        ),
        mock=lambda d: (
            "Pe scurt (simplificat): "
            + (d["text"][:220] + ("…" if len(d["text"]) > 220 else ""))
            + "\nÎntreabă medicul pentru clarificarea termenilor pe care nu îi înțelegi."
        ),
    )
)

register(
    Skill(
        name="lifestyle_tips",
        title="Sfaturi de stil de viață",
        description="Sugestii generale de stil de viață pentru o afecțiune.",
        inputs=["condition"],
        prompt=lambda d: (
            _GUARD,
            f"Oferă sugestii generale de stil de viață pentru: „{d['condition']}” "
            "(alimentație, activitate fizică, somn, monitorizare). Fără doze sau "
            "tratamente.",
        ),
        mock=lambda d: (
            f"Sugestii generale pentru „{d['condition']}”: alimentație echilibrată, "
            "activitate fizică regulată (ex. 30 min/zi), somn suficient, hidratare, "
            "evitarea fumatului și a excesului de alcool, și monitorizarea "
            "periodică a parametrilor relevanți împreună cu medicul."
        ),
    )
)

register(
    Skill(
        name="review_prescription",
        title="Verifică o rețetă",
        description="Trecere în revistă orientativă a unei liste de medicamente.",
        inputs=["medications"],
        prompt=lambda d: (
            _GUARD,
            "Pacientul are următoarea listă de medicamente:\n"
            f"{d['medications']}\n"
            "Explică orientativ pentru ce se folosesc, semnalează posibile "
            "interacțiuni sau dubluri de care să întrebe medicul/farmacistul. "
            "Nu recomanda doze.",
        ),
        mock=lambda d: (
            "Trecere în revistă orientativă a medicamentelor:\n"
            f"{d['medications']}\n"
            "Verifică cu medicul sau farmacistul dacă există interacțiuni, "
            "dubluri terapeutice sau contraindicații pentru situația ta. Respectă "
            "dozele și programul indicate de medic."
        ),
    )
)

register(
    Skill(
        name="symptom_info",
        title="Informații despre un simptom",
        description="Explică orientativ un simptom și semnele care cer urgență.",
        inputs=["symptom"],
        prompt=lambda d: (
            _GUARD,
            f"Explică orientativ ce poate însemna simptomul „{d['symptom']}” (fără "
            "a pune diagnostic) și enumeră semnele de alarmă care necesită "
            "prezentare urgentă la medic.",
        ),
        mock=lambda d: (
            f"„{d['symptom']}” poate avea multe cauze, de la unele banale la altele "
            "care necesită evaluare. Semne de alarmă care cer prezentare urgentă: "
            "durere intensă bruscă, dificultăți de respirație, durere în piept, "
            "leșin, sângerare importantă, febră mare persistentă. Dacă apar, "
            "solicită asistență medicală de urgență."
        ),
    )
)
