# Deploy pe DigitalOcean (App Platform)

Echivalentul managed al blueprint-ului de Render. Spec-ul e în `.do/app.yaml`
și creează **PostgreSQL + backend (FastAPI) + frontend (Next.js)**.

> ⚠️ DigitalOcean **nu are tier gratuit** ca Render. Estimare pornire (dev):
> ~5 $/lună per serviciu (backend + frontend) + ~7 $/lună baza de date dev.

## Ce îți trebuie
- Cont DigitalOcean.
- 3 valori pe care le setezi ca **ENCRYPTED env vars** pe backend:
  - `SECRET_KEY`, `DATA_ENCRYPTION_KEY` — ți le-am generat (fișier separat).
  - `GROQ_API_KEY` — cheie gratuită de la <https://console.groq.com/keys>.

## Metoda A — din interfață (recomandat pe telefon)

1. **Apps → Create App**.
2. **GitHub** → alege `calinmurariu1-prog/asistent-medical-RO`, branch
   `claude/new-isolated-project-oheqvr`.
3. DO detectează Dockerfile-urile din `backend/` și `frontend/`. Dacă întreabă,
   confirmă **două componente** (backend, frontend) tip *Web Service*, Docker.
   - backend: **HTTP port 8000**, health check path `/health`.
   - frontend: **HTTP port 3000**.
4. **Add Resource → Database → PostgreSQL** (dev). Numește-o `asistent-medical-db`.
5. La **Environment Variables** pe backend adaugă:
   | Key | Value | Encrypt? |
   |-----|-------|----------|
   | `ENVIRONMENT` | `production` | nu |
   | `DATABASE_URL` | `${asistent-medical-db.DATABASE_URL}` | nu |
   | `AI_DEFAULT_PROVIDER` | `groq` | nu |
   | `GROQ_MODEL` | `llama-3.3-70b-versatile` | nu |
   | `BACKEND_CORS_ORIGINS` | `${frontend.PUBLIC_URL}` | nu |
   | `FRONTEND_URL` | `${frontend.PUBLIC_URL}` | nu |
   | `SECRET_KEY` | *(din fișierul de secrete)* | **da** |
   | `DATA_ENCRYPTION_KEY` | *(din fișierul de secrete)* | **da** |
   | `GROQ_API_KEY` | *(de la console.groq.com)* | **da** |
6. Pe frontend, la **Build-time** env: `NEXT_PUBLIC_API_URL` =
   `${backend.PUBLIC_URL}` (trebuie **Build Time**, se coace în build).
7. **Create Resources**. Prima construire durează ~5–10 min; backend-ul rulează
   migrațiile Alembic la pornire.

## Metoda B — cu doctl (CLI, mai rapid dacă ai laptop)

```bash
# 1. Instalează + autentifică
doctl auth init

# 2. Creează aplicația din spec
doctl apps create --spec .do/app.yaml

# 3. Setează secretele (nu sunt în spec)
#    Găsește APP_ID cu: doctl apps list
doctl apps update <APP_ID> --spec .do/app.yaml
#    apoi în UI: App → Settings → backend → Environment → editează
#    SECRET_KEY / DATA_ENCRYPTION_KEY / GROQ_API_KEY (Encrypt).
```

## Note
- **Port binding:** backend-ul și frontend-ul ascultă pe `$PORT` (injectat de DO),
  cu fallback local 8000/3000 — deci merge și pe DO, și pe Render, și local.
- **DB SSL:** stringul DO include `sslmode=require`; codul normalizează automat
  `postgresql://` → driverul `psycopg` v3, care îl acceptă.
- **AI:** implicit `groq`. Fără `GROQ_API_KEY`, serviciul folosește mock-ul
  offline (aplicația pornește oricum). Poți schimba în `gemini`/`anthropic`/
  `openai` setând `AI_DEFAULT_PROVIDER` + cheia respectivă.
- **Google Maps:** adaugă `GOOGLE_MAPS_API_KEY` (backend) și
  `NEXT_PUBLIC_GOOGLE_MAPS_KEY` (frontend, Build Time) — vezi `docs/AI_AND_MAPS.md`.
- **Deploy automat:** `deploy_on_push: true` → orice push pe branch reconstruiește.
