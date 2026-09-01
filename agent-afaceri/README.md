# Agent Afaceri & Juridic AI

Agent AI **informativ** pentru afaceri și juridic, în limba română (context
România). Combină skill-uri de **avocat** (juridic) și de **business** cu un
chat contextual.

> ⚖️ **Disclaimer.** Informațiile au caracter **pur orientativ** și **NU**
> constituie consultanță juridică, fiscală sau contabilă profesională. Pentru
> decizii concrete consultă un avocat, un contabil autorizat sau autoritatea
> competentă (ex. ANAF, ONRC).

Proiect **izolat**, independent de restul repository-ului.

---

## Skill-uri incluse

### Juridic ⚖️
| Skill | Ce face |
|-------|---------|
| **Redactează un contract** | Draft de contract (colaborare, prestări servicii, muncă, închiriere) cu clauzele uzuale. |
| **Analizează un contract** | Explică un contract și semnalează clauzele de risc / ce lipsește. |

### Business 📈
| Skill | Ce face |
|-------|---------|
| **Înființare firmă (SRL / PFA)** | Pași, documente, CAEN, capital social, obligații de start. |
| **Fiscalitate & obligații** | TVA, impozit micro/profit, declarații ANAF, termene (orientativ). |
| **Plan de afaceri** | Structură completă de plan de afaceri pornind de la o idee. |
| **Analiză SWOT** | Puncte forte/slabe, oportunități, amenințări + recomandări. |

Plus **chat** contextual (mod business sau juridic).

Adaugi un skill nou înregistrând încă un `Skill` în
`backend/app/services/ai/skills.py` — nimic altceva nu trebuie schimbat.

---

## Stack

- **Backend:** FastAPI · Pydantic v2 · pytest
- **Frontend:** Next.js 14 (App Router, TypeScript) · Tailwind CSS
- **AI:** Anthropic **Claude** (implicit) cu fallback offline `mock` (fără
  cheie API — util pentru dezvoltare și teste)
- **Infra:** Docker · Docker Compose

---

## Rulare rapidă (Docker)

```bash
cd agent-afaceri
cp .env.example .env
# opțional: pune ANTHROPIC_API_KEY în .env pentru răspunsuri reale
docker compose up --build
```

- Frontend: http://localhost:3000
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs

Fără cheie API, agentul rulează în **mod demonstrativ offline** (răspunsuri
deterministe din fiecare skill), deci aplicația funcționează imediat.

## Rulare locală (fără Docker)

Backend:
```bash
cd agent-afaceri/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...   # opțional
uvicorn app.main:app --reload
```

Frontend:
```bash
cd agent-afaceri/frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev   # http://localhost:3000
```

## Teste

```bash
cd agent-afaceri/backend
python -m pytest
```

---

## API

| Metodă | Rută | Descriere |
|--------|------|-----------|
| `GET` | `/health` | Status + provider activ |
| `GET` | `/skills` | Listează skill-urile (nume, titlu, categorie, câmpuri) |
| `POST` | `/skills/{name}/run` | Rulează un skill: `{"inputs": {...}}` |
| `POST` | `/chat` | Chat: `{"message": "...", "domain": "business\|juridic", "history": []}` |

Exemplu:
```bash
curl -X POST http://localhost:8000/skills/company_setup/run \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"form": "SRL", "activity": "comerț online"}}'
```

---

## Configurare (`.env`)

| Variabilă | Implicit | Rol |
|-----------|----------|-----|
| `AI_PROVIDER` | `anthropic` | `anthropic` sau gol → mod demo `mock` |
| `ANTHROPIC_API_KEY` | — | Cheia Claude; fără ea → mod demo offline |
| `ANTHROPIC_MODEL` | `claude-sonnet-5` | Modelul Claude |
| `CORS_ORIGINS` | `*` | Origini permise pentru frontend |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | URL backend, folosit de frontend |
