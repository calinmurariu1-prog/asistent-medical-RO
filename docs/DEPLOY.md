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

## Note free tier
Serviciile free Render „adorm" după inactivitate (primul request după pauză e
mai lent). Postgres free are limită de stocare/retenție — potrivit pentru test,
nu pentru producție reală.

## Email (SMTP, opțional)
Pentru verificare email + resetare parolă reale, setează `SMTP_HOST`,
`SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`. Fără ele, linkurile se loghează.
