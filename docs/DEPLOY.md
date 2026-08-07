# Deploy pe Render

Blueprint-ul `render.yaml` din rădăcină creează tot stack-ul: **PostgreSQL +
backend (FastAPI) + frontend (Next.js)**, cu URL-uri publice permanente.

## Pași

1. **Push pe GitHub** (branch-ul tău e deja acolo).
2. Intră pe [dashboard.render.com](https://dashboard.render.com) →
   **New → Blueprint**.
3. Conectează repo-ul `asistent-medical-ro` și selectează branch-ul.
   Render citește `render.yaml` și listează cele 3 resurse.
4. **Apply** → Render construiește imaginile Docker și pornește serviciile.
   Backend-ul rulează automat migrațiile Alembic la pornire.

După ~5–10 minute vei avea:

| Resursă | URL |
|---|---|
| Frontend | `https://asistent-medical-frontend.onrender.com` |
| Backend API | `https://asistent-medical-backend.onrender.com` |
| API docs | `https://asistent-medical-backend.onrender.com/docs` |

> URL-urile cross-service sunt deja configurate în blueprint (Render folosește
> nume predictibile `https://<serviciu>.onrender.com`). Dacă redenumești
> serviciile, actualizează `BACKEND_CORS_ORIGINS`, `NEXT_PUBLIC_API_URL` și
> `FRONTEND_URL` corespunzător.

## Secrete generate automat
`SECRET_KEY` și `DATA_ENCRYPTION_KEY` sunt generate de Render (`generateValue`)
— nu le pui manual. `validate_production_config()` verifică la boot că nu sunt
valori implicite, deci deploy-ul se oprește dacă lipsesc.

## AI real (opțional)
Implicit `AI_DEFAULT_PROVIDER=mock` (funcționează fără chei). Pentru AI real,
în Render → serviciul backend → Environment, setează:
- `AI_DEFAULT_PROVIDER=anthropic` (sau `openai` / `gemini`)
- `ANTHROPIC_API_KEY=...`

Pentru providerul `medllm` (z.ai) e nevoie și de micro-serviciul `med-llm` — pe
Render adaugă-l ca serviciu Docker separat din `./med-llm-service`, cu configul
z.ai montat ca Secret File `.z-ai-config`.

## Găsire medici (Google Maps, opțional)
Setează `GOOGLE_MAPS_API_KEY` pe backend (Places activat, restricționat pe IP).
Fără cheie, funcția rulează pe providerul mock.

## Deploy automat din GitHub (CI/CD)

Workflow-ul `.github/workflows/ci.yml` rulează la fiecare push: **testează
backend-ul (lint + pytest) și construiește frontend-ul**, apoi — dacă ambele
trec — declanșează deploy-ul pe Render. Astfel se publică doar cod „verde".

Setup (o singură dată):

1. În Render, pentru fiecare serviciu (backend + frontend):
   **Settings → Deploy Hook** → copiază URL-ul.
2. (Opțional) Dezactivează *Auto-Deploy* pe Render, ca deploy-ul să vină doar
   prin GitHub Actions (după teste).
3. În GitHub: **Settings → Secrets and variables → Actions → New secret**.
   Ai două variante:
   - **Blueprint (un singur hook):** `RENDER_DEPLOY_HOOK` = hook-ul de sync al
     blueprint-ului (`https://api.render.com/sync/exs-...?key=...`) — declanșează
     deploy la tot stack-ul.
   - **Per serviciu:** `RENDER_DEPLOY_HOOK_BACKEND` și
     `RENDER_DEPLOY_HOOK_FRONTEND` (`https://api.render.com/deploy/srv-...?key=...`).

Fără aceste secrete, jobul de deploy pur și simplu se sare (CI rămâne verde).

**Dependabot** (`.github/dependabot.yml`) deschide săptămânal PR-uri de
actualizare pentru pip, npm, GitHub Actions și Docker.

## IP-uri de ieșire Render (allowlist)

Serviciile de pe Render fac request-uri externe de la aceste intervale de IP:

```
74.220.50.0/24
74.220.58.0/24
```

Folosește-le pentru a **restricționa** accesul acolo unde e cazul:

- **Google Maps / Places API key** (server-side): în Google Cloud Console →
  Credentials → cheia → *Application restrictions* → **IP addresses** → adaugă
  cele două intervale. Astfel cheia funcționează doar din backend-ul de pe Render.
- **Bază de date externă / API-uri terțe / SMTP**: adaugă aceste intervale în
  firewall-ul/allowlist-ul furnizorului, ca doar Render să poată accesa.
- **Micro-serviciul z.ai (med-llm)**: dacă `internal-api.z.ai` are allowlist pe
  IP, adaugă aceste intervale.

> Notă: intervalele de IP Render pot fi actualizate de Render în timp —
> verifică periodic în dashboard-ul Render (Connections / Outbound IPs).

## Note free tier
Serviciile free Render „adorm" după inactivitate (primul request după pauză e
mai lent). Postgres free are limită de stocare/retenție — potrivit pentru test,
nu pentru producție reală.

## Email (SMTP, opțional)
Pentru verificare email + resetare parolă reale, setează `SMTP_HOST`,
`SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`. Fără ele, linkurile se loghează.
