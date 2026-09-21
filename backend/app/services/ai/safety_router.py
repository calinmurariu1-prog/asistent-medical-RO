"""Conservative local emergency signals, independent of external AI.

This limited lexical router is not a diagnostic or triage instrument. Absence of
an alert cannot establish safety. Rules also cover reports about another person.
"""
from __future__ import annotations

import re
import unicodedata

EMERGENCY_SOURCES = [
    {"ref": "E1", "type": "public_guidance", "title": "Serviciul de urgență 112",
     "url": "https://serviciipublice.gov.ro/serviciu/serviciul-de-urgenta-112-asigurat-cetatenilor"},
    {"ref": "E2", "type": "public_guidance", "title": "NHS: semne care necesită ajutor urgent",
     "url": "https://www.nhs.uk/conditions/heart-attack/"},
    {"ref": "E3", "type": "public_guidance", "title": "NHS: simptome de accident vascular cerebral",
     "url": "https://www.nhs.uk/conditions/stroke/symptoms/"},
]

_PATTERNS = (
    r"\bnu (?:mai )?pot (?:sa )?respira?\b",
    r"\b(?:ma sufoc|se sufoca|nu respira|este inconstient|e inconstient)\b",
    r"\b(?:durere|presiune|strangere) (?:puternica |severa )?(?:in|pe) piept\b",
    r"\b(?:ma doare|il doare|o doare) (?:tare )?pieptul\b",
    r"\b(?:fata|gura) (?:mi |i )?s-a strambat\b",
    r"\b(?:brusc|deodata).{0,60}\b(?:nu pot vorbi|nu poate vorbi|nu pot misca|nu poate misca)\b",
    r"\b(?:cred ca|suspectez ca) (?:am|are|fac|face) (?:un )?(?:infarct|avc)\b",
)


def emergency_reply(text: str) -> str | None:
    normalized = "".join(
        c for c in unicodedata.normalize("NFKD", text.lower())
        if not unicodedata.combining(c)
    )
    if not any(re.search(pattern, normalized) for pattern in _PATTERNS):
        return None
    return (
        "Mesajul menționează semne care pot necesita ajutor medical imediat. "
        "Dacă tu sau altcineva are aceste simptome acum ori le-a avut recent, "
        "sună imediat la 112 în România și urmează instrucțiunile operatorului. [E1] "
        "Nu aștepta un răspuns AI și nu conduce singur spre spital. [E2] [E3] "
        "Nu pot stabili cauza sau exclude o urgență prin chat. "
        "Acest mesaj de siguranță este generat local, fără analiză AI."
    )
