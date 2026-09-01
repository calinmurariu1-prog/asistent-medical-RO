# Agent Afaceri & Juridic AI

Agent AI **informativ** pentru afaceri și juridic, în limba română (context
România), cu **interfață web**. Combină skill-uri de **avocat** (juridic) și de
**business** cu un chat contextual, cont de utilizator, **salvarea documentelor**
și **export PDF / Word**.

> ⚖️ **Disclaimer.** Informațiile au caracter **pur orientativ** și **NU**
> constituie consultanță juridică, fiscală sau contabilă profesională. Pentru
> decizii concrete consultă un avocat, un contabil autorizat sau autoritatea
> competentă (ex. ANAF, ONRC, ANSPDCP, ANPC).

Proiect **izolat**, independent de restul repository-ului.

---

## Funcționalități

- 🖥️ **Interfață web** (Next.js): pagina agentului, autentificare, „Documentele mele".
- 🤖 **Chat contextual** cu agentul (mod business sau juridic).
- 🧩 **Skill-uri** dedicate (vezi mai jos), fiecare cu formular propriu.
- 🔐 **Cont de utilizator** (înregistrare / autentificare, JWT).
- 💾 **Salvare documente** generate, per utilizator.
- 📄 **Export PDF și Word (.docx)** — cu diacritice corecte în PDF.

## Skill-uri incluse

### Juridic ⚖️
| Skill | Ce face |
|-------|---------|
| **Redactează un contract** | Draft de contract (colaborare, prestări servicii, muncă, închiriere). |
| **Analizează un contract** | Explică un contract și semnalează clauzele de risc / ce lipsește. |
| **Contract de muncă detaliat** | CIM conform Codului muncii (părți, durată, salariu, timp de muncă, concediu…). |
| **Conformitate GDPR** | Checklist de conformare GDPR pentru o afacere. |
| **Protecția consumatorului** | Obligații retur/garanție/informare pentru vânzări și online. |

### Business 📈
| Skill | Ce face |
|-------|---------|
| **Înființare firmă (SRL / PFA)** | Pași, documente, CAEN, capital social, obligații de start. |
| **Fiscalitate & obligații** | TVA, impozit micro/profit, declarații ANAF, termene (orientativ). |
| **Plan de afaceri** | Structură completă de plan de afaceri pornind de la o idee. |
| **Analiză SWOT** | Puncte forte/slabe, oportunități, amenințări + recomandări. |

Adaugi un skill nou înregistrând încă un `Skill` în
`backend/app/services/ai/skills.py` — nimic altceva nu trebuie schimbat.

---

## Stack

- **Backend:** FastAPI · SQLAlchemy 2 · Pydantic v2 · pytest
- **Frontend:** Next.js 14 (App Router, TypeScript) · Tailwind CSS
- **Auth:** JWT (PyJWT) · parole bcrypt
- **Export:** reportlab (PDF) · python-docx (Word)
- **AI:** Anthropic **Claude** (implicit) cu fallback offline `mock` (fără cheie API)
- **Infra:** Docker · Docker Compose · SQLite implicit (Postgres opțional)

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
export SECRET_KEY=dev-secret
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

| Metodă | Rută | Auth | Descriere |
|--------|------|:----:|-----------|
| `GET` | `/health` | — | Status + provider activ |
| `GET` | `/skills` | — | Listează skill-urile |
| `POST` | `/skills/{name}/run` | — | Rulează un skill: `{"inputs": {...}}` |
| `POST` | `/chat` | — | Chat: `{"message", "domain", "history"}` |
| `POST` | `/auth/register` | — | Cont nou → token |
| `POST` | `/auth/login` | — | Autentificare (form) → token |
| `GET` | `/auth/me` | ✅ | Utilizatorul curent |
| `POST` | `/documents` | ✅ | Salvează un document |
| `GET` | `/documents` | ✅ | Documentele mele |
| `DELETE` | `/documents/{id}` | ✅ | Șterge un document |
| `GET` | `/documents/{id}/export?format=pdf\|docx` | ✅ | Descarcă documentul salvat |
| `POST` | `/export` | ✅ | Export direct: `{"title","content","format"}` |

Exemplu:
```bash
curl -X POST http://localhost:8000/skills/gdpr_compliance/run \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"business": "magazin online", "data_types": "nume, email, adresă"}}'
```

---

## Configurare (`.env`)

| Variabilă | Implicit | Rol |
|-----------|----------|-----|
| `AI_PROVIDER` | `anthropic` | `anthropic` sau gol → mod demo `mock` |
| `ANTHROPIC_API_KEY` | — | Cheia Claude; fără ea → mod demo offline |
| `ANTHROPIC_MODEL` | `claude-sonnet-5` | Modelul Claude |
| `SECRET_KEY` | `dev-secret-change-me` | Semnarea token-urilor JWT (**schimbă** în producție) |
| `DATABASE_URL` | `sqlite:///./app.db` | Baza de date (SQLite implicit; Postgres opțional) |
| `CORS_ORIGINS` | `*` | Origini permise pentru frontend |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | URL backend, folosit de frontend |
