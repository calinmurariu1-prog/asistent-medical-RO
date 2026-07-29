# Arhitectură — Asistent Medical AI

## Vedere de ansamblu

```
┌────────────┐     HTTPS      ┌──────────────────┐
│  Frontend  │ ─────────────▶ │   FastAPI API    │
│ Next.js /  │  JWT Bearer    │  (app/main.py)   │
│    PWA     │ ◀───────────── │                  │
└────────────┘                └───────┬──────────┘
                                       │
             ┌─────────────────────────┼──────────────────────────┐
             ▼                         ▼                          ▼
     ┌───────────────┐        ┌─────────────────┐        ┌───────────────┐
     │  PostgreSQL   │        │  MinIO / S3     │        │  AI Providers │
     │ (date + audit)│        │ (documente)     │        │ Claude/OpenAI │
     └───────────────┘        └─────────────────┘        │   /Gemini     │
                                                          └───────────────┘
                                       ▲
                                       │ OCR (Tesseract) + RAG
```

## Straturi (backend)

| Strat | Locație | Responsabilitate |
|-------|---------|------------------|
| Config | `app/core/config.py` | Setări din `.env` (pydantic-settings) |
| DB | `app/core/database.py` | Engine, sesiuni, `Base`, `TimestampMixin` |
| Securitate | `app/core/security.py` | Hash parole, JWT, criptare câmpuri AES |
| Modele | `app/models/` | Tabele SQLAlchemy 2 (mapped) |
| Scheme | `app/schemas/` | Validare I/O (Pydantic v2) |
| Rute | `app/api/routes/` | Endpoint-uri REST pe module |
| Dependențe | `app/api/deps.py` | `get_db`, `get_current_user`, roluri |
| Servicii | `app/services/` | Logică (token-uri, audit, AI, OCR…) |

Fiecare **modul** din cerință = un router în `app/api/routes/` + schemele și
serviciile aferente. Design modular: modulele noi se adaugă fără să atingă
codul existent (doar `include_router`).

## Autentificare (Modul 1)

- Access token (scurt) + refresh token (lung), semnate HS256.
- `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/me`.
- Reset parolă și verificare email prin token-uri JWT cu `type` dedicat
  (`app/services/token_service.py`).
- MFA TOTP: `/auth/mfa/setup` → `/auth/mfa/activate`; la login se cere
  `mfa_code` dacă e activat.
- OAuth Google/Apple: câmpuri pregătite pe `User` (`oauth_provider`,
  `oauth_subject`); fluxul complet se adaugă în faza de integrare OAuth.

## Securitate & GDPR

- **Parole:** bcrypt (passlib).
- **Transport:** TLS (terminare la reverse-proxy/ingress în producție).
- **La rest:** criptare de câmp pentru date sensibile (CNP) —
  `encrypt_field` / `decrypt_field` (Fernet/AES). Pentru AES-256-GCM strict,
  se poate înlocui implementarea Fernet cu `AESGCM` din `cryptography.hazmat`.
- **Audit:** fiecare acțiune sensibilă scrie în `audit_logs`
  (`app/services/audit.py`).
- **Consimțământ:** tabelul `consents` (un rând per grant/revoke).
- **RBAC:** `UserRole` (patient/doctor/admin), `require_admin`.
- **MFA:** TOTP per utilizator.
- **Backup:** volume Postgres/MinIO; în producție — snapshot-uri automate.

## Strategia AI (module 4/5/7/11)

Serviciul AI va fi o abstracție `AIProvider` cu implementări pentru Anthropic,
OpenAI și Gemini, selectate prin `AI_DEFAULT_PROVIDER`. Fluxul RAG:

1. OCR/parsare document (Tesseract / pypdf / pydicom) → `extracted_text`.
2. Chunking + embeddings → index vectorial (pgvector în Postgres).
3. La întrebare: retrieval din documentele **pacientului curent** + prompt cu
   instrucțiuni stricte („nu inventa; dacă nu știi, spune că datele sunt
   insuficiente"; „include disclaimer").
4. Răspuns cu referințe la sursele folosite (`AIChatMessage.sources`).

## Testare & CI

- `pytest` cu SQLite in-memory și override de `get_db` (`tests/conftest.py`).
- `ruff` pentru lint.
- GitHub Actions rulează lint + teste la fiecare push/PR.

## Producție (rezumat — vezi ROADMAP)

- Reverse proxy (Traefik/Nginx) cu TLS, rate limiting.
- Migrații Alembic la deploy; secrete în vault/secret manager.
- Observabilitate: logging structurat, metrics, tracing.
- Scalare orizontală backend (stateless) + Postgres gestionat + S3 gestionat.
