# Variabile de mediu pe Render — inventar

Verificat la data de **26 septembrie 2026** față de:

- `render.yaml` (blueprint)
- `backend/app/core/config.py` (Settings)
- `.env.example` / `.env.prod.example`

## Setate automat de blueprint (`render.yaml`)

| Variabilă | Sursă | Valoare |
|---|---|---|
| `ENVIRONMENT` | value | `production` |
| `DATABASE_URL` | fromDatabase → `asistent-medical-db.connectionString` | `postgresql+psycopg://...` (normalizat automat) |
| `SECRET_KEY` | generateValue | random 256-bit base64 |
| `DATA_ENCRYPTION_KEY` | generateValue | random 256-bit base64 |
| `RATE_LIMIT_ENABLED` | value | `true` |
| `AI_DEFAULT_PROVIDER` | value | `mock` |
| `BACKEND_CORS_ORIGINS` | value | `https://asistent-medical-frontend.onrender.com` |
| `FRONTEND_URL` | value | `https://asistent-medical-frontend.onrender.com` |
| `NEXT_PUBLIC_API_URL` (frontend) | value | `https://asistent-medical-backend.onrender.com` |

## Lipsesc din blueprint — de setat manual

### AI (opțional, fără ele → mock)
- `GROQ_API_KEY`, `GROQ_MODEL`
- `GEMINI_API_KEY`, `GEMINI_MODEL`
- `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`
- `OPENAI_API_KEY`, `OPENAI_MODEL`
- `MED_LLM_URL`, `MED_LLM_TIMEOUT` (doar dacă rulezi micro-serviciul `med-llm`)

### Maps
- `GOOGLE_MAPS_API_KEY` (backend, IP-restricted pe intervalele Render)
- `NEXT_PUBLIC_GOOGLE_MAPS_KEY` (frontend, **build-time**, referrer-restricted)
- `PLACES_DEFAULT_RADIUS_M`, `PLACES_MAX_RESULTS`

### Email
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_TLS`

### Billing — Stripe (web)
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICES`
- `STRIPE_SUCCESS_URL`, `STRIPE_CANCEL_URL`, `STRIPE_PORTAL_RETURN_URL`
- `STRIPE_ALLOW_MOCK=false` în producție

### Billing — IAP (mobil)
- `IAP_PRODUCTS`, `IAP_ALLOW_MOCK=false`
- `APPLE_IAP_BUNDLE_ID`, `APPLE_IAP_ISSUER_ID`, `APPLE_IAP_KEY_ID`,
  `APPLE_IAP_PRIVATE_KEY`, `APPLE_IAP_ENVIRONMENT`
- `GOOGLE_PLAY_PACKAGE_NAME`, `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON`

### Push notifications
- `FCM_PROJECT_ID`, `FCM_SERVICE_ACCOUNT_JSON`, `PUSH_ALLOW_MOCK=false`

### Storage (dacă nu folosești MinIO din compose)
- `S3_ENDPOINT_URL`, `S3_PUBLIC_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`,
  `S3_BUCKET`, `S3_REGION`, `S3_USE_SSL`

### Altele
- `REQUIRE_AI_CONSENT`
- `OCR_LANGUAGES`
- `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`
- `RATE_LIMIT_LOGIN_TIMES`, `RATE_LIMIT_WINDOW_SECONDS`

## Cum verifici în dashboard

1. Render → serviciul `asistent-medical-backend` → **Environment**.
2. Compară lista cu tabelul de mai sus.
3. Orice lipsă din blueprint → adaugă manual (sau marcheaz-o `sync: false`
   în `render.yaml` ca să primești prompt la următorul sync).

## Notă despre `fromDatabase`

Render injectează `DATABASE_URL` ca `postgresql://...`. `config.py` are un
validator care rescrie automat `postgresql://` → `postgresql+psycopg://`, deci
driverul SQLAlchemy v3 funcționează fără intervenție manuală.
