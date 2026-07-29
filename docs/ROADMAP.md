# Roadmap — plan pe faze

Fiecare fază livrează cod funcțional, testat și integrat. Modulele se
raportează la numerotarea din specificația produsului.

## ✅ Faza 1 — Fundație (livrată)

- Structură monorepo + Docker Compose (Postgres + MinIO).
- Schema DB completă: 17 tabele, relații, chei, indexuri (`docs/DATABASE.md`).
- Migrație Alembic inițială + rulare automată la deploy.
- **Modul 1 — Autentificare:** register, login, refresh, reset parolă,
  verificare email, MFA (TOTP). JWT access+refresh.
- **Modul 2 — Profil pacient:** date personale, IMC calculat, alergii.
- Securitate: bcrypt, criptare câmp (CNP), audit log, consimțământ, RBAC.
- CI GitHub Actions (ruff + pytest). Teste pentru module 1 și 2.

## ✅ Faza 2 — Documente & OCR (Modul 4) — livrată

- Upload PDF/JPG/PNG/DICOM în MinIO/S3 (`documents`), cu validare tip și
  dimensiune și izolare per pacient.
- Pipeline extracție text: pypdf (PDF, cu fallback OCR pentru scanări) ·
  Tesseract (imagini) · pydicom (DICOM). Degradare grațioasă dacă un binar
  lipsește.
- Abstracție AI multi-provider (`app/services/ai/`): Anthropic / OpenAI /
  Gemini, cu **mock offline** determinist când nu există cheie API — extrage
  diagnostice/tratamente/medicamente/valori analize + rezumat.
- Parser de valori de laborator + flagging normal/crescut/scăzut/critic
  (`lab_results`).
- Endpoint-uri: upload, listă+filtru, detaliu, download (URL semnat),
  reprocesare, ștergere. Status `pending→processing→done/failed`.
- Notă: procesarea rulează sincron în request; în producție se mută pe o coadă
  (Celery/RQ) — lifecycle-ul de status e deja modelat.

## ✅ Faza 3 — Interpretare analize & grafice (Modul 5) — livrată

- Explicații AI per parametru (`ai.explain_lab_value`) cu o bază de referință
  offline pentru analite comune (`ai/lab_reference.py`) + disclaimer.
- Serii temporale per analit pentru grafice (`/labs/series/{analyte}`),
  ordonate cronologic, cu interval de referință și tendință.
- Comparație cu analizele anterioare: calcul de trend (creștere/scădere/stabil).
- Rezumat (`/labs/summary`): ultima valoare per analit + numărul de valori
  anormale și critice.
- Endpoint-uri: listă+filtre, analite distincte, serie, adăugare manuală,
  explicare individuală și în masă. Fără schimbări de schemă (reutilizează
  `lab_results`).

## Faza 4 — RAG & Chat Medical AI (Modul 11)

- Embeddings + `pgvector`; retrieval din documentele pacientului.
- Chat contextual cu surse citate; guardrails („nu inventa", disclaimer).

## Faza 5 — Cronice, medicamente, programări, notificări (Module 8–10, 14)

- Monitorizare boli cronice + grafice (glicemie, HbA1c, TSH, tensiune…).
- Verificare interacțiuni medicamentoase / dubluri (Modul 9).
- Calendar programări + notificări push/email/SMS.

## Faza 6 — Dashboard, Export, Admin (Module 12, 13, 15)

- Dashboard agregat; export PDF/Word raport complet; panou admin.

## Faza 7 — Frontend & mobil

- Next.js (App Router) · TailwindCSS · shadcn/ui · Framer Motion.
- Dark mode, responsive, paletă alb/albastru/mov/verde.
- PWA instalabilă (Android/iOS). Native separat, opțional, ulterior.

---

## Scalare & monitorizare în producție

**Scalare**
- Backend stateless → scalare orizontală (N replici) în spatele unui LB.
- Postgres gestionat (RDS/Cloud SQL) cu replici de citire; `pgvector` pentru RAG.
- S3 gestionat pentru documente; CDN pentru livrare.
- Cozi (Celery/RQ + Redis) pentru OCR/AI asincron.

**Observabilitate**
- Logging structurat (JSON) + agregare (Loki/ELK).
- Metrics (Prometheus) + dashboards (Grafana); tracing (OpenTelemetry).
- Alerting pe erori, latență, coadă de procesare.

**Securitate în producție**
- Secrete în secret manager; rotație chei de criptare.
- WAF + rate limiting; scanare dependențe; backup-uri testate.
- Jurnalizare acces conform GDPR; proces de export/ștergere date la cerere.
