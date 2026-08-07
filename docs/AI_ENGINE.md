# Asistent Medical AI — Specificație „Motorul AI" (pentru Codex)

> Document autonom, gata de dat unui agent de cod (Codex). Descrie **exact** cum
> este construit motorul AI al aplicației *Asistent Medical AI*: contracte,
> provideri, prompturi, guardrails, fluxuri, modele de date, endpoint-uri și
> puncte de extensie. Scopul: un agent poate **re-implementa sau extinde**
> motorul fără să vadă restul codului.

---

## 0. Context produs (ce e aplicația)

Aplicație web **patient-facing** în limba română care:
- centralizează dosarul medical al unui pacient (analize, documente, medicație,
  istoric, programări);
- încarcă și analizează documente (PDF/imagine/DICOM) prin OCR + AI;
- oferă **explicații orientative** generate de AI (NU diagnostic, NU prescripție);
- răspunde la întrebări **bazate exclusiv pe dosarul pacientului** (RAG);
- urmărește evoluția în timp a parametrilor de sănătate.

**Regula supremă a motorului AI:** informativ, orientativ, empatic. Niciodată
diagnostic definitiv sau prescripție. Fiecare rezultat afișat utilizatorului se
încheie cu un disclaimer și, la chat, citează sursele din dosar prin marcaje `[S#]`.

### Stack relevant pentru motor
- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2.0, Pydantic v2 /
  pydantic-settings, PostgreSQL (SQLite în teste).
- **AI SDKs (lazy import):** `anthropic`, `openai`, `google-generativeai`, `httpx`.
- **Micro-serviciu MedLLM:** Node.js (`med-llm-service/server.mjs`) care apelează
  CLI-ul `z-ai` (z.ai) și expune HTTP `/complete` + `/health`.

---

## 1. Arhitectura motorului (privire de ansamblu)

```
                         ┌────────────────────────────────────────────┐
  HTTP (FastAPI routes)  │  documents / labs / chats / ai_skills ...   │
                         └───────────────┬────────────────────────────┘
                                         │  Depends(get_ai_provider)
                                         ▼
              ┌───────────────────────────────────────────────┐
              │  factory.get_ai_provider()  (selectează din    │
              │  settings.AI_DEFAULT_PROVIDER; fallback → mock)│
              └───────┬───────────┬───────────┬───────────┬────┘
                      │           │           │           │
                 Anthropic     OpenAI      Gemini      MedLLM ──HTTP──► med-llm-service ──► z-ai CLI
                (LLMProvider base: _complete + prompt/JSON parsing)        │
                      │                                                 (fallback → Mock dacă
                      └───────────────► MockProvider (offline, determinist) │  micro-serviciul e down)
                                         └──────────────────────────────────┘

  Consumatori ai providerului:
    • document_processing.process_document()      → ai.extract_document()
    • lab_analysis / labs route                   → ai.explain_lab_value()
    • chat_service.answer()  (+ rag.build_context)→ ai.chat()
    • skills.run_skill() / record_ai.*            → ai.complete()
```

**Principiu de design:** un singur **Protocol** (`AIProvider`) cu 4 metode.
Orice provider concret (real sau mock) îl implementează structural. Selecția e
la runtime, prin factory. Dacă providerul real nu are cheie / SDK / e down,
**degradează automat la `MockProvider`** — aplicația funcționează mereu, chiar
offline și în CI, fără chei.

---

## 2. Contractul de bază — `app/services/ai/base.py`

Acesta este **contractul pe care Codex trebuie să-l respecte** pentru orice
provider nou.

```python
DISCLAIMER = (
    "Aceste informații sunt orientative, generate automat, și NU reprezintă "
    "un diagnostic. Consultați întotdeauna medicul."
)

@dataclass
class ExtractedLabValue:
    analyte: str
    value: float | None = None
    value_text: str | None = None
    unit: str | None = None
    ref_low: float | None = None
    ref_high: float | None = None

@dataclass
class DocumentExtraction:
    summary: str = ""
    diagnoses: list[str] = field(default_factory=list)
    treatments: list[str] = field(default_factory=list)
    medications: list[str] = field(default_factory=list)
    lab_values: list[ExtractedLabValue] = field(default_factory=list)
    def to_metadata(self) -> dict: ...   # serializează pt. Document.ai_metadata

class AIProvider(Protocol):
    name: str

    def extract_document(self, text: str, category: str) -> DocumentExtraction: ...

    def explain_lab_value(self, *, analyte, value, unit, ref_low, ref_high,
                          flag: str, trend: str | None = None) -> str: ...

    def chat(self, *, question: str, context: str,
             history: list[tuple[str, str]] | None = None) -> str: ...

    def complete(self, *, system: str, user: str) -> str: ...
```

**Semantica fiecărei metode:**

| Metodă | Rol | Reguli obligatorii |
|---|---|---|
| `extract_document(text, category)` | Extrage date structurate din textul OCR al unui document. | Nu inventează; câmp lipsă → gol/`null`. Întoarce mereu `DocumentExtraction`. |
| `explain_lab_value(...)` | Explică o valoare de laborator pe înțelesul pacientului (2–5 propoziții). | Fără diagnostic. Se încheie cu `DISCLAIMER`. |
| `chat(question, context, history)` | Răspunde **doar** pe baza `context` (dosarul) + cunoștințe generale. | Nu inventează date despre pacient; dacă lipsesc → spune explicit. Citează `[S#]`. Fără diagnostic/prescripție. Disclaimer la final. |
| `complete(system, user)` | Completare text generică folosită de framework-ul de skills și de `record_ai`. | Text simplu. Erorile → întoarce `DISCLAIMER` (nu aruncă). |

`history` = listă **plată** de tupluri `(role, content)`, unde `role ∈ {"user","assistant"}`.

---

## 3. Selecția providerului — `app/services/ai/factory.py`

`get_ai_provider() -> AIProvider` (dependency FastAPI). Logica:

1. Citește `settings.AI_DEFAULT_PROVIDER` (lower-case).
2. Dacă `== "medllm"`: instanțiază `MedLLMProvider`; dacă
   `MED_LLM_FALLBACK_MOCK` și health-check eșuează (cache TTL
   `MED_LLM_HEALTH_TTL`s) → `MockProvider`.
3. Altfel caută cheia providerului (`anthropic`/`openai`/`gemini`). **Fără cheie
   → `MockProvider`** (log info).
4. Instanțiază providerul real; orice excepție (SDK lipsă, config greșit) →
   `MockProvider` (log warning).

Health-check MedLLM e cache-uit într-un dict de modul; `reset_medllm_health_cache()`
îl resetează (folosit în teste).

**Invariant pe care Codex trebuie să-l păstreze:** factory-ul nu aruncă
niciodată — întotdeauna întoarce un provider valid; fallback-ul e `MockProvider`.

---

## 4. Providerii LLM reali — `app/services/ai/llm.py`

Bază comună `LLMProvider` care implementează TOATE metodele de business și
lasă providerilor concreți **doar** `_complete(system, user) -> str`.

- `extract_document`: construiește promptul de extracție, cere **JSON valid**,
  îl parsează (`_strip_code_fences` + `json.loads`), și — indiferent de LLM —
  rulează în paralel parserul determinist `parse_lab_values(text)` ca **plasă de
  siguranță** (dacă LLM-ul ratează valorile, tot avem lab values). Numerele se
  normalizează cu `_num` (acceptă virgulă zecimală RO).
- `explain_lab_value` / `chat`: prompturi dedicate (vezi §7). La orice excepție,
  întorc un fallback text + `DISCLAIMER` (nu aruncă).
- `complete`: wrapper peste `_complete` cu try/except → `DISCLAIMER` la eroare.

Providerii concreți și modelele implicite:

```python
class AnthropicProvider(LLMProvider):   # settings.ANTHROPIC_MODEL = "claude-sonnet-5"
    def _complete(system, user):
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        msg = client.messages.create(model=..., max_tokens=2000,
                                     system=system, messages=[{"role":"user","content":user}])
        return "".join(b.text for b in msg.content if b.type == "text")

class OpenAIProvider(LLMProvider):      # settings.OPENAI_MODEL = "gpt-4o"
    def _complete(system, user):
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=..., response_format={"type":"json_object"},
            messages=[{"role":"system","content":system},{"role":"user","content":user}])
        return resp.choices[0].message.content or "{}"

class GeminiProvider(LLMProvider):      # settings.GEMINI_MODEL = "gemini-1.5-pro"
    def _complete(system, user):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(..., system_instruction=system)
        return model.generate_content(user).text or "{}"
```

SDK-urile se importă **lazy**, în interiorul `_complete`, ca aplicația să pornească
fără ele instalate.

> ⚠️ Notă pentru Codex: `response_format=json_object` la OpenAI e potrivit pentru
> `extract_document`, dar la `chat`/`explain_lab_value` textul e liber. Dacă
> unifici, tratează cazul în care providerul întoarce JSON acolo unde vrei text.

---

## 5. Providerul MedLLM (z.ai) — `app/services/ai/med_llm.py` + `med-llm-service/`

`MedLLMProvider` implementează același contract, dar delegă prin HTTP:

```
FastAPI → httpx POST {MED_LLM_URL}/complete {system,user} → Node server.mjs → `z-ai chat -p <user> --system <system>` → JSON → { "response": "..." }
```

- `health_check()` → `GET /health` (timeout 2s).
- `_complete()` → `POST /complete`; la eroare HTTP/conexiune întoarce `DISCLAIMER`.
- `extract_document` cere JSON strict (curăță ```-fences), fallback la
  `DocumentExtraction(summary=raw[:500])` dacă JSON invalid.
- `chat` include ultimele 6 tururi din `history`, etichetate „Pacient"/„Asistent".

Micro-serviciul (`med-llm-service/server.mjs`, port **3031**): server HTTP nativ
Node, fără dependențe; face `spawn('z-ai', ['chat','-p',user,'--system',system])`,
extrage primul bloc JSON din stdout și întoarce `choices[0].message.content`.
Config z.ai montat ca fișier `.z-ai-config` (Secret File pe Render / bind-mount în
docker-compose). Host extern folosit de CLI: `internal-api.z.ai`.

---

## 6. Providerul offline — `app/services/ai/mock.py`

Determinist, **fără rețea**. Folosit automat când nu există cheie și în teste/CI.
- `extract_document`: `parse_lab_values` + regex pentru diagnostice / tratamente /
  medicamente; compune un `summary`.
- `explain_lab_value`: folosește tabelul `lab_reference.lookup(analyte)` (label,
  „despre", semnificație high/low) + interpretarea flag-ului + trend + `DISCLAIMER`.
- `chat`: dacă `context` gol → mesaj „date insuficiente"; altfel rezumă
  determinist primele 3 snippet-uri, menționează `[S#]` + `DISCLAIMER`.
- `complete`: `"(răspuns simulat) " + DISCLAIMER` (skill-urile preferă mock-ul lor).

**Contract pentru Codex:** orice provider nou trebuie să aibă un echivalent
determinist / fallback ca funcțiile să meargă offline și testele să fie stabile.

---

## 7. Prompturi & guardrails (textul exact folosit azi)

**Extracție document (system):**
> „Ești un asistent care extrage date structurate din documente medicale
> românești. Nu inventezi informații; dacă un câmp lipsește, îl lași gol.
> Răspunzi EXCLUSIV cu JSON valid, fără text suplimentar."

JSON cerut: `summary`, `diagnoses[]`, `treatments[]`, `medications[]`,
`lab_values[]{analyte,value,unit,ref_low,ref_high}`. Textul e trunchiat la 12.000
caractere.

**Explicație valoare lab (system):**
> „Ești un asistent medical informativ. Oferi explicații orientative, nu
> diagnostice. Răspunzi doar cu text simplu."

**Chat (system) — 5 reguli stricte:**
1. Răspunde DOAR pe baza contextului furnizat (dosarul) + cunoștințe generale.
2. NU inventa date despre pacient; dacă lipsesc → spune clar „date insuficiente".
3. Nu pune diagnostic și nu prescrie tratament.
4. Când folosești o informație din context, indică sursa prin marcajul `[S#]`.
5. Încheie întotdeauna cu disclaimer.

**Guard skills (`_GUARD`):**
> „Ești un asistent medical informativ, în limba română. NU pui diagnostic și NU
> prescrii tratament. Oferă informații orientative, clare și empatice, și
> recomandă consultarea medicului pentru decizii."

`_with_disclaimer(text)` adaugă `DISCLAIMER` dacă textul nu conține deja „orientativ".

---

## 8. Framework-ul de AI Skills — `app/services/ai/skills.py`

Capacități AI discrete, reutilizabile, cu **mock determinist** per skill.

```python
@dataclass(frozen=True)
class Skill:
    name: str; title: str; description: str
    inputs: list[str]
    prompt: Callable[[dict], tuple[str, str]]  # -> (system, user)
    mock: Callable[[dict], str]

register(skill); list_skills(); get_skill(name)

def run_skill(provider, skill, data) -> str:
    if provider.name == "mock": return _with_disclaimer(skill.mock(data))
    system, user = skill.prompt(data)
    return _with_disclaimer(provider.complete(system=system, user=user))
```

Skill-uri înregistrate azi (nume → inputs):
1. `explain_medication` → `["name"]`
2. `prepare_doctor_visit` → `["concern"]`
3. `simplify_text` → `["text"]`
4. `lifestyle_tips` → `["condition"]`
5. `review_prescription` → `["medications"]`
6. `symptom_info` → `["symptom"]`

**Extensie:** un skill nou = un `register(Skill(...))`. Nimic altceva nu se
schimbă; endpoint-ul `/ai/skills` îl expune automat.

### Skills „data-aware" — `app/services/ai/record_ai.py`
Citesc întâi datele pacientului (via `lab_analysis`, `monitoring`), apoi rulează AI:
- `summarize_record(db, ai, patient)` — rezumat al întregului dosar.
- `compare_analyte(db, ai, patient, analyte)` — evoluția unui analit în timp.
Ambele au ramură `mock` deterministă din date.

---

## 9. RAG — `app/services/rag/retriever.py`

Retriever **lexical** (keyword) peste dosar, determinist, 100% offline.

```python
def build_context(db, patient_id, query, *, max_snippets=8) -> RetrievedContext
# RetrievedContext(context_text: str, sources: list[dict]); .is_empty
```

- Colectează snippet-uri din: `Document` (ai_summary/extracted_text),
  `LabResult`, `MedicalHistory`, `Medication` (active), `Allergy`.
- Scor = overlap de tokeni (RO+EN, cu stopwords) + `0.01` baseline (ca să existe
  mereu context).
- Întoarce top-N marcate `[S1]…[SN]` + listă `sources` cu `{ref, type, id, title}`.

> **Upgrade de producție (indicat în cod):** înlocuiește cu retriever vectorial
> (pgvector + embeddings) **cu aceeași semnătură `build_context`** — chat-service
> nu se schimbă.

Chat orchestration — `app/services/chat_service.py`:
`answer()` persistă întrebarea, apelează `build_context`, apoi `ai.chat(...)`,
persistă răspunsul cu `sources` (JSON). Include ultimele `HISTORY_TURNS = 6` tururi.

---

## 10. Pipeline-ul de documente — `app/services/document_processing.py`

`process_document(db, document, storage, ai)`:
1. `status = PROCESSING`.
2. `storage.get(storage_key)` → bytes; `ocr.extract_text(data, content_type, filename)`.
3. `ai.extract_document(text, category)` → `DocumentExtraction`.
4. Persistă: `extracted_text`, `ai_summary`, `ai_metadata` (JSON), și `LabResult`-uri.
5. `compute_flag(value, ref_low, ref_high)` clasifică fiecare valoare:
   `NORMAL / HIGH / CRITICAL_HIGH / LOW / CRITICAL_LOW` (critic la ≥150% peste sau
   ≤50% sub limită — margine generică, de rafinat per-analit).
6. `status = DONE` / la excepție `FAILED` + mesaj.

Rulează sincron azi; e proiectat să fie mutat pe o coadă (Celery/RQ) — câmpul de
status modelează deja lifecycle-ul.

---

## 11. Endpoint-uri AI — `app/api/routes/ai_skills.py` (prefix `/ai`)

| Metodă | Rută | Descriere | Auth / consimțământ |
|---|---|---|---|
| GET | `/ai/skills` | Listează skill-urile (name/title/description/inputs). | `get_current_user` |
| POST | `/ai/skills/{name}` | Rulează un skill; body `{inputs: {...}}`; validează inputurile obligatorii. | + `require_ai_consent` |
| POST | `/ai/summarize-record` | Rezumat AI al întregului dosar. | + `require_ai_consent` |
| POST | `/ai/compare-analyte` | Interpretare evoluție analit; body `{analyte}`. | + `require_ai_consent` |

Alte rute care folosesc providerul (via `Depends(get_ai_provider)`): `documents`
(procesare), `labs` (explain_lab_value), `chats` (chat RAG).

`require_ai_consent` (din `api/deps.py`) impune un consimțământ `AI_PROCESSING`
activ **doar dacă** `settings.REQUIRE_AI_CONSENT = True`.

---

## 12. Configurare — `app/core/config.py` (env vars)

```
AI_DEFAULT_PROVIDER   = "anthropic"        # anthropic|openai|gemini|medllm|mock
ANTHROPIC_API_KEY     = ""                  ANTHROPIC_MODEL = "claude-sonnet-5"
OPENAI_API_KEY        = ""                  OPENAI_MODEL    = "gpt-4o"
GEMINI_API_KEY        = ""                  GEMINI_MODEL    = "gemini-1.5-pro"
MED_LLM_URL           = "http://med-llm:3031"
MED_LLM_TIMEOUT       = 90.0
MED_LLM_FALLBACK_MOCK = True
MED_LLM_HEALTH_TTL    = 30.0
REQUIRE_AI_CONSENT    = False               # dacă True, skill-urile cer consimțământ AI
```

Fără nicio cheie setată, motorul rulează pe `MockProvider` (implicit în CI/teste).

---

## 13. Modele de date atinse de motor (rezumat)

- `Document(patient_id, category, storage_key, content_type, original_filename,
  extracted_text, ai_summary, ai_metadata, status, processed_at, document_date)`.
- `LabResult(patient_id, document_id, analyte, value, value_text, unit, ref_low,
  ref_high, flag, measured_on)`.
- `AIChat(patient_id, title, created_at)` / `AIChatMessage(chat_id, role, content,
  sources)`.
- `MedicalHistory`, `Medication`, `Allergy`, `Patient` — citite de RAG / record_ai.
- Enums: `LabFlag`, `ProcessingStatus`, `ChatRole`, `DocumentCategory`.

---

## 14. Guardrails, siguranță & GDPR (obligatorii)

1. **Fără diagnostic/prescripție** — impus prin system prompts la fiecare metodă.
2. **Grounding** — chat răspunde doar din context; „date insuficiente" când lipsesc.
3. **Citări `[S#]`** — trasabilitate către sursele din dosar.
4. **Disclaimer** — pe fiecare ieșire vizibilă utilizatorului.
5. **Degradare grațioasă** — providerii nu aruncă spre utilizator; fallback la
   `DISCLAIMER`/mock.
6. **Consimțământ AI** — `REQUIRE_AI_CONSENT` + `require_ai_consent`.
7. **Confidențialitate** — datele pacientului sunt trimise providerului AI ales;
   pentru date sensibile, preferă `medllm` (self-host) sau `mock`. Nu loga PII în clar.

---

## 15. Testare (ce trebuie să rămână verde)

- Toate testele rulează pe `MockProvider` (fără chei, `DATABASE_URL=sqlite://`).
- Contracte de verificat pentru orice provider nou:
  - `extract_document` întoarce mereu `DocumentExtraction` (nu aruncă);
  - `explain_lab_value` / `chat` / skill-uri se termină cu disclaimer;
  - factory nu aruncă și cade pe mock fără cheie;
  - `chat` fără context → „date insuficiente".
- CI: `ruff check .` + `pytest -q` (backend), `npm run build` (frontend).

---

## 16. Ce are Codex de făcut („creează motorul AI")

Puncte de extensie recomandate, în ordine de valoare:

1. **Retriever vectorial (pgvector + embeddings)** cu aceeași semnătură
   `build_context(db, patient_id, query, *, max_snippets=8) -> RetrievedContext`.
   Adaugă tabel de embeddings pe `Document`/`LabResult`; păstrează fallback lexical.
2. **Procesare asincronă** a documentelor (Celery/RQ) în jurul
   `process_document`, folosind câmpul `status`.
3. **Streaming** la chat (SSE) — nouă metodă opțională `chat_stream` pe provideri
   care o suportă, cu fallback la `chat`.
4. **Praguri critice per-analit** pentru `compute_flag` (tabel clinic), înlocuind
   marginea generică 150%/50%.
5. **Skill-uri noi** — doar `register(Skill(...))` în `skills.py` (+ mock determinist).
6. **Normalizare/validare JSON** mai robustă la `extract_document` (schema Pydantic
   pentru răspunsul LLM), păstrând plasa de siguranță `parse_lab_values`.
7. **Observabilitate** — logare structurată a latenței/erorilor per provider
   (fără PII), rate-limiting pe endpoint-urile AI.

**Reguli de aur pentru orice implementare nouă:**
- Respectă `AIProvider` Protocol; nu schimba semnăturile publice.
- Nu arunca excepții spre utilizator; degradează la mock/disclaimer.
- Păstrează guardrails-urile (fără diagnostic, grounding, `[S#]`, disclaimer).
- Import lazy pentru SDK-uri; totul trebuie să pornească și fără ele.
- Menține motorul funcțional 100% offline pe `MockProvider`.

---

## Anexă A — Fișiere-cheie ale motorului

```
backend/app/services/ai/
├── base.py            # Protocol AIProvider + dataclasses + DISCLAIMER
├── factory.py         # get_ai_provider() (selecție + fallback mock)
├── llm.py             # LLMProvider base + Anthropic/OpenAI/Gemini
├── med_llm.py         # MedLLMProvider (HTTP → micro-serviciu z.ai)
├── mock.py            # MockProvider (offline, determinist)
├── skills.py          # framework AI skills + 6 skill-uri
├── record_ai.py       # summarize_record / compare_analyte (data-aware)
├── lab_parser.py      # parse_lab_values() — extractor determinist
└── lab_reference.py   # lookup() — tabel de referință analite (RO)

backend/app/services/rag/retriever.py   # build_context() (RAG lexical)
backend/app/services/chat_service.py    # answer() (orchestrare chat)
backend/app/services/document_processing.py  # process_document() (OCR→AI→DB)
backend/app/api/routes/ai_skills.py     # endpoint-uri /ai/*
backend/app/core/config.py              # settings AI (chei, modele, medllm)

med-llm-service/server.mjs              # micro-serviciu Node → z-ai CLI
```
