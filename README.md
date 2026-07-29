# Asistent Medical AI

Platformă medicală AI care permite utilizatorului să-și gestioneze dosarul
medical, să încarce analize și documente, să primească explicații orientative
generate de AI și să urmărească evoluția sănătății în timp.

> ⚠️ **Disclaimer.** Aplicația **NU pune diagnostice** și **NU înlocuiește
> medicul**. Toate informațiile au caracter pur orientativ.

---

## Stadiul proiectului

Proiectul este construit **în faze**, fiecare fază fiind cod funcțional și
testat. Vezi [`docs/ROADMAP.md`](docs/ROADMAP.md) pentru planul complet.

| Fază | Conținut | Stare |
|------|----------|-------|
| **1** | Fundație: schema DB completă (17 tabele), Modul 1 Autentificare (JWT, register/login/reset/verify, MFA TOTP), Modul 2 Profil pacient, Docker, CI, teste | ✅ **livrat** |
| 2 | Încărcare documente + OCR (Modul 4) | ⏳ |
| 3 | Interpretare analize + grafice (Modul 5) | ⏳ |
| 4 | RAG + Chat Medical AI (Modul 11) | ⏳ |
| 5 | Monitorizare cronice, medicamente, programări, notificări | ⏳ |
| 6 | Dashboard + Export + Admin | ⏳ |
| 7 | Frontend Next.js + PWA mobil | ⏳ |

---

## Stack

- **Backend:** FastAPI · SQLAlchemy 2 · PostgreSQL · Alembic
- **Auth:** JWT (access + refresh) · TOTP MFA · (OAuth Google/Apple pregătit)
- **Storage:** MinIO / S3 (documente)
- **AI:** abstracție multi-provider (Anthropic Claude / OpenAI / Gemini)
- **OCR:** Tesseract (ron+eng)
- **Infra:** Docker · Docker Compose · GitHub Actions CI

> Notă: „GPT-5.5" din cerință nu există ca model real. Serviciul AI este
> agnostic de provider și configurabil din `.env`; providerul implicit
> recomandat este Anthropic Claude.

---

## Rulare locală

### Cu Docker (recomandat)

```bash
cp .env.example .env
# editează .env: pune SECRET_KEY, DATA_ENCRYPTION_KEY și cheile AI
docker compose up --build
```

- API: http://localhost:8000
- Documentație interactivă (Swagger): http://localhost:8000/docs
- MinIO consolă: http://localhost:9001

Migrațiile Alembic rulează automat la pornirea containerului backend.

### Fără Docker (doar backend)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export SECRET_KEY=dev-secret
export DATA_ENCRYPTION_KEY=$(python -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())")
export DATABASE_URL="postgresql+psycopg://medai:medai_dev_password@localhost:5432/asistent_medical"

alembic upgrade head
uvicorn app.main:app --reload
```

### Teste

```bash
cd backend
export SECRET_KEY=test DATA_ENCRYPTION_KEY=test-key DATABASE_URL=sqlite://
pytest
```

---

## Documentație

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arhitectură și componente
- [`docs/DATABASE.md`](docs/DATABASE.md) — schema bazei de date
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — plan pe faze + scalare/producție

## Securitate & GDPR

- Parole hash-uite cu bcrypt; token-uri JWT semnate.
- Criptare la nivel de câmp (AES/Fernet) pentru date sensibile (ex. CNP).
- Jurnal de audit (`audit_logs`) pentru accountability GDPR.
- Model de consimțământ (`consents`) și control acces pe roluri.
- MFA (TOTP) disponibil per utilizator.

Detalii și plan complet de hardening în `docs/ARCHITECTURE.md`.
