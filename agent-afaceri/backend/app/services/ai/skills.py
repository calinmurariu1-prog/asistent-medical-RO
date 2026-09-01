"""Skill-uri AI de avocat (juridic) și business — capabilități discrete.

Fiecare skill își declară intrările, construiește un prompt cu guardrails și
oferă un output offline determinist (`mock`), ca funcția să meargă și fără
cheie API. Adaugi o capabilitate nouă înregistrând încă un `Skill` — nimic
altceva nu se schimbă.

Toate răspunsurile sunt orientative (vezi DISCLAIMER). Contextul e România,
în limba română.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.services.ai.base import DISCLAIMER, AIProvider

# Guard juridic
_GUARD_LEGAL = (
    "Ești un asistent juridic informativ pentru România, care răspunde în limba "
    "română clar și structurat. NU oferi consultanță juridică definitivă și NU "
    "înlocuiești un avocat. Explică orientativ, semnalează riscurile și recomandă "
    "consultarea unui avocat pentru cazuri concrete. Folosește terminologie "
    "corectă din legislația română, dar pe înțeles."
)

# Guard business/fiscal
_GUARD_BIZ = (
    "Ești un consultant de afaceri informativ pentru România, care răspunde în "
    "limba română clar și structurat. NU oferi consultanță fiscală sau contabilă "
    "definitivă. Oferă informații orientative, practice și actuale, și recomandă "
    "verificarea cu un contabil autorizat sau cu ANAF pentru situații concrete."
)


@dataclass(frozen=True)
class Skill:
    name: str
    title: str
    description: str
    category: str  # "juridic" | "business"
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
    """Execută un skill: mock determinist pentru providerul offline, altfel LLM."""
    if getattr(provider, "name", "") == "mock":
        return _with_disclaimer(skill.mock(data))
    system, user = skill.prompt(data)
    return _with_disclaimer(provider.complete(system=system, user=user))


# ==========================================================================
# JURIDIC — Contracte
# ==========================================================================
register(
    Skill(
        name="draft_contract",
        title="Redactează un contract",
        description="Generează un draft de contract (colaborare, prestări servicii, muncă, închiriere) în limba română.",
        category="juridic",
        inputs=["type", "parties", "terms"],
        prompt=lambda d: (
            _GUARD_LEGAL,
            f"Redactează un draft de contract de tip „{d['type']}” în limba română, "
            f"între părțile: {d['parties']}.\n"
            f"Termeni și condiții dorite: {d.get('terms', '(nespecificat)')}.\n"
            "Include: părți, obiect, durată, preț/plată, obligațiile părților, "
            "răspundere, confidențialitate, încetare, forță majoră, litigii și "
            "clauze finale. Marchează câmpurile de completat cu [___]. "
            "Adaugă la final o listă scurtă de clauze la care părțile să fie atente.",
        ),
        mock=lambda d: (
            f"DRAFT CONTRACT — {d['type'].upper()}\n"
            f"Părți: {d['parties']}\n\n"
            "1. OBIECTUL CONTRACTULUI — [___]\n"
            "2. DURATA — [___]\n"
            f"3. PREȚ / PLATĂ — {d.get('terms', '[___]')}\n"
            "4. OBLIGAȚIILE PĂRȚILOR — [___]\n"
            "5. CONFIDENȚIALITATE — părțile păstrează confidențiale informațiile.\n"
            "6. RĂSPUNDERE — [___]\n"
            "7. ÎNCETARE — prin acord, expirare sau reziliere pentru neexecutare.\n"
            "8. FORȚĂ MAJORĂ — conform art. 1351 Cod civil.\n"
            "9. LITIGII — soluționate amiabil sau de instanțele competente.\n\n"
            "Atenție la: obiect clar, termene de plată, penalități, clauza de "
            "reziliere și instanța competentă. Verifică draftul cu un avocat."
        ),
    )
)

register(
    Skill(
        name="analyze_contract",
        title="Analizează un contract",
        description="Explică pe înțeles un contract și semnalează clauzele de risc.",
        category="juridic",
        inputs=["text"],
        prompt=lambda d: (
            _GUARD_LEGAL,
            "Analizează următorul text de contract. Explică pe scurt ce prevede, "
            "apoi semnalează clauzele dezavantajoase, ambigue sau riscante și ce "
            "ar trebui renegociat. Structurează în: Rezumat / Clauze de atenție / "
            f"Ce lipsește / Recomandări.\n\nCONTRACT:\n{d['text']}",
        ),
        mock=lambda d: (
            "Rezumat: contractul a fost recepționat pentru analiză orientativă.\n"
            "Clauze de atenție: verifică penalitățile, termenele de plată, clauza "
            "de reziliere unilaterală și limitarea răspunderii.\n"
            "Ce lipsește frecvent: confidențialitate, forță majoră, instanța "
            "competentă, modalitatea de notificare.\n"
            "Recomandări: negociază clauzele dezechilibrate și cere opinia unui avocat.\n"
            f"(Text primit: {len(d['text'])} caractere.)"
        ),
    )
)

# ==========================================================================
# JURIDIC / BUSINESS — Înființare firmă
# ==========================================================================
register(
    Skill(
        name="company_setup",
        title="Înființare firmă (SRL / PFA)",
        description="Pași, documente, CAEN, capital social și obligații pentru înființarea unei firme în România.",
        category="business",
        inputs=["form", "activity"],
        prompt=lambda d: (
            _GUARD_BIZ,
            f"Explică pașii pentru înființarea unei firme de tip „{d['form']}” în "
            f"România, pentru activitatea: „{d['activity']}”.\n"
            "Include: documente necesare, rezervare denumire la ONRC, capital "
            "social, alegerea codului/codurilor CAEN potrivite, sediu social, "
            "declarații, costuri orientative, termene și obligații fiscale de "
            "start (TVA, impozit micro/venit, contribuții). Prezintă ca listă de pași.",
        ),
        mock=lambda d: (
            f"Înființare {d['form']} pentru activitatea „{d['activity']}”:\n"
            "1. Alege și rezervă denumirea la ONRC.\n"
            "2. Stabilește sediul social (contract/acord proprietar).\n"
            "3. Alege codul CAEN principal potrivit activității.\n"
            "4. Pregătește actul constitutiv (la SRL) / documentele PFA.\n"
            "5. Depune capitalul social (min. 1 leu la SRL).\n"
            "6. Depune dosarul la ONRC și obține CUI-ul.\n"
            "7. Alege regimul fiscal (micro/venit real, plătitor sau neplătitor TVA).\n"
            "8. Contract cu un contabil și deschide cont bancar.\n"
            "Costuri și termene diferă — verifică la ONRC și cu un contabil."
        ),
    )
)

# ==========================================================================
# BUSINESS — Fiscalitate & obligații
# ==========================================================================
register(
    Skill(
        name="tax_obligations",
        title="Fiscalitate & obligații",
        description="Informații orientative despre TVA, impozit, declarații ANAF și termene.",
        category="business",
        inputs=["situation"],
        prompt=lambda d: (
            _GUARD_BIZ,
            "Pentru situația de mai jos, explică orientativ obligațiile fiscale în "
            "România: tipuri de impozit aplicabile (micro/profit/venit), TVA "
            "(prag, cotă), declarații ANAF relevante, termene uzuale și contribuții. "
            "Precizează clar că pragurile și cotele se pot schimba și trebuie "
            f"verificate la ANAF.\n\nSITUAȚIE:\n{d['situation']}",
        ),
        mock=lambda d: (
            "Obligații fiscale (orientativ):\n"
            "- Impozit: micro (pe venit) sau pe profit, în funcție de eligibilitate.\n"
            "- TVA: verifică pragul de înregistrare și cota aplicabilă activității.\n"
            "- Declarații ANAF uzuale: D300 (TVA), D394, D101/D100, D112 (salarii).\n"
            "- Termene: de regulă lunar/trimestrial; verifică calendarul ANAF.\n"
            "Pragurile și cotele se schimbă des — confirmă cu un contabil și pe anaf.ro.\n"
            f"(Situație analizată: {d['situation'][:150]})"
        ),
    )
)

# ==========================================================================
# BUSINESS — Plan de afaceri & analiză
# ==========================================================================
register(
    Skill(
        name="business_plan",
        title="Plan de afaceri",
        description="Structurează un plan de afaceri pornind de la o idee.",
        category="business",
        inputs=["idea"],
        prompt=lambda d: (
            _GUARD_BIZ,
            f"Construiește un plan de afaceri structurat pentru ideea: „{d['idea']}”.\n"
            "Include secțiunile: Rezumat executiv, Problemă & soluție, Piață țintă & "
            "clienți, Concurență, Model de venituri, Strategie de marketing/vânzări, "
            "Operațiuni, Echipă, Proiecție financiară simplă (venituri/costuri/prag "
            "de rentabilitate) și Riscuri. Concret și acționabil.",
        ),
        mock=lambda d: (
            f"Plan de afaceri — „{d['idea']}”\n"
            "1. Rezumat executiv: [___]\n"
            "2. Problemă & soluție: ce nevoie rezolvi.\n"
            "3. Piață țintă: cine sunt clienții.\n"
            "4. Concurență: cine mai oferă asta.\n"
            "5. Model de venituri: cum câștigi bani.\n"
            "6. Marketing & vânzări: cum ajungi la clienți.\n"
            "7. Operațiuni & echipă: cum livrezi.\n"
            "8. Proiecție financiară: venituri – costuri = profit; prag de rentabilitate.\n"
            "9. Riscuri și cum le reduci.\n"
            "Detaliază fiecare secțiune cu cifre realiste."
        ),
    )
)

register(
    Skill(
        name="swot_analysis",
        title="Analiză SWOT",
        description="Generează o analiză SWOT pentru o afacere sau idee.",
        category="business",
        inputs=["business"],
        prompt=lambda d: (
            _GUARD_BIZ,
            f"Realizează o analiză SWOT pentru: „{d['business']}”. Oferă 4-6 puncte "
            "la fiecare din: Puncte forte (S), Puncte slabe (W), Oportunități (O), "
            "Amenințări (T). La final, 3 recomandări strategice concrete.",
        ),
        mock=lambda d: (
            f"Analiză SWOT — „{d['business']}”\n"
            "PUNCTE FORTE: [___]\n"
            "PUNCTE SLABE: [___]\n"
            "OPORTUNITĂȚI: cerere în creștere, digitalizare, nișe neacoperite.\n"
            "AMENINȚĂRI: concurență, schimbări legislative/fiscale, costuri.\n"
            "Recomandări: 1) valorifică punctele forte pe o nișă clară; "
            "2) reduce dependențele riscante; 3) testează piața înainte de scalare."
        ),
    )
)
