"""Small source-backed educational catalog; requires clinical review before launch."""
from __future__ import annotations

import re
import unicodedata

from app.services.ai.base import DISCLAIMER, AIProvider

# Paraphrased from primary NHS pages, consulted 2026-09-21. No dosing advice.
_CATALOG = {
    "warfarina": ("Warfarin", "warfarin",
                  "Warfarina este un anticoagulant folosit pentru prevenirea și tratarea "
                  "cheagurilor de sânge. Principalul efect advers este riscul crescut "
                  "de sângerare."),
    "aspirina": ("Aspirin", "aspirin",
                 "Aspirina este utilizată pentru calmarea durerii sau, în anumite situații, "
                 "pentru prevenirea cheagurilor de sânge. Utilizarea depinde de indicație. "
                 "Poate provoca disconfort gastric și sângerare mai ușoară."),
    "levotiroxina": ("Levothyroxine", "levothyroxine",
                     "Levotiroxina este folosită în principal pentru hipotiroidism. "
                     "Monitorizarea prin analize ajută medicul să verifice tratamentul."),
}
_ALIASES = {"warfarin": "warfarina", "aspirin": "aspirina",
            "acid acetilsalicilic": "aspirina", "levothyroxine": "levotiroxina"}


def explain(provider: AIProvider, name: str) -> dict:
    normalized = "".join(c for c in unicodedata.normalize("NFKD", name.strip().lower())
                         if not unicodedata.combining(c))
    entry = _CATALOG.get(_ALIASES.get(normalized, normalized))
    simulated = provider.name == "mock"
    fallback = (f'Nu am o sursă suficientă pentru a explica verificabil „{name}”. '
                "Folosește denumirea exactă a substanței active și discută prospectul cu "
                f"medicul sau farmacistul. {DISCLAIMER}")
    if not entry:
        return dict(result=fallback, sources=[], abstained=True, simulated=simulated)
    title, slug, excerpt = entry
    source = {"ref": "M1", "title": f"NHS — {title}",
              "url": f"https://www.nhs.uk/medicines/{slug}/", "checked_on": "2026-09-21"}
    if simulated:
        candidate = f"Mod simulat — rezumat educațional local, fără interpretare AI. {excerpt} [M1]"
    else:
        candidate = provider.complete(
            system=("Răspunde în română, numai pe baza fragmentului de referință. "
                    "Fiecare afirmație medicală trebuie să citeze [M1]. Nu adăuga alte indicații, "
                    "diagnostice, doze, orare sau modificări de tratament. Nu interpreta situația "
                    "personală. Dacă fragmentul nu este suficient, spune acest lucru."),
            user=f"Explică pe scurt această substanță: {title}.\nSursa [M1]: {excerpt}",
        )
        # Citation identity alone does not prove entailment or clinical correctness.
        refs = re.findall(r"\[([^\]\n]+)\]", candidate)
        if not candidate.strip() or not refs or set(refs) != {"M1"}:
            return dict(result=fallback, sources=[], abstained=True, simulated=False)
    result = (f"{candidate}\n\nNu modifica tratamentul pe baza acestei explicații. "
              f"{DISCLAIMER}\n[M1] {source['title']}: {source['url']}")
    return dict(result=result, sources=[source], abstained=False, simulated=simulated)
