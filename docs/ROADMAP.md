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

## ✅ Faza 4 — RAG & Chat Medical AI (Modul 11) — livrată

- Retriever lexical peste dosarul pacientului (`services/rag/`): documente,
  analize, istoric medical, medicamente active, alergii — cu scor pe cuvinte
  cheie și marcaje de sursă `[S#]`. Interfața `build_context` e pregătită să
  fie înlocuită cu un retriever vectorial (pgvector + embeddings) fără
  modificări în serviciul de chat.
- `AIProvider.chat` (mock offline + Anthropic/OpenAI/Gemini) cu guardrails
  stricte: răspunde doar din context, nu inventează, spune când datele sunt
  insuficiente, citează sursele, adaugă disclaimer.
- Orchestrare chat (`chat_service.py`): persistă mesajele user+assistant,
  păstrează istoricul conversației, atașează sursele folosite; titlu
  auto-generat din prima întrebare.
- Endpoint-uri `/chats`: creare, listă, detaliu (cu mesaje și surse), trimitere
  mesaj, ștergere. Fără schimbări de schemă (reutilizează `ai_chats` /
  `ai_chat_messages`).
- Robustețe: crearea lazy a profilului de pacient interoghează după `user_id`
  și tratează cursa pe constrângerea unică.

### Upgrade planificat pentru RAG
- Embeddings + `pgvector`, chunking al documentelor, re-ranking. Se conectează
  în locul retriever-ului lexical prin aceeași funcție `build_context`.

## ✅ Faza 5 — Cronice, medicamente, programări, notificări — livrată

- **Modul 9 — Medicamente:** CRUD + verificare interacțiuni și dubluri
  terapeutice (`medication_check.py`, bază de cunoștințe curată, extensibilă;
  cu disclaimer). Doar orientativ — nu înlocuiește medicul/farmacistul.
- **Modul 8 — Monitorizare cronice:** dashboard (`/monitoring/dashboard`) care
  grupează parametrii recunoscuți (glicemie, HbA1c, colesterol, TSH, tensiune,
  puls, greutate…) pe arii clinice, cu ultima valoare, tendință și serie pentru
  grafice; IMC calculat din profil. Reutilizează `lab_results` (fără migrație).
- **Modul 10 — Programări:** CRUD calendar + filtru „upcoming”, statusuri.
- **Modul 14 — Notificări:** creare/listare/marcare citit, dispatcher abstract
  (push/email/SMS — momentan logat, adaptoarele reale se conectează ușor),
  memento-uri idempotente pentru programări. Livrarea în timp real și
  programată necesită un worker în producție.

Fără schimbări de schemă — toate reutilizează tabelele existente.

## ✅ Faza 6 — Dosar complet, cronologie, recomandări, dashboard — livrată

- **Modul 3 — Dosar medical:** CRUD istoric (diagnostice, intervenții,
  operații, internări, tratamente, boli cronice, antecedente familiale prin
  `event_type`) + vaccinuri. Filtre pe an, medic, spital, tip, cronic.
- **Modul 6 — Cronologie:** timeline unificat peste istoric, documente,
  programări și medicamente, cu filtre pe an și tip.
- **Modul 7 — Recomandări AI (orientative):** întrebări pentru medic,
  investigații de discutat, sugestii de stil de viață, monitorizare și alerte —
  derivate din analize anormale, boli cronice și interacțiuni medicamentoase,
  cu disclaimer. Poate fi îmbogățit cu LLM prin `AIProvider`.
- **Modul 12 — Dashboard agregat:** rezumat analize, documente recente,
  tratamente active, programări viitoare, alerte, notificări necitite și
  preview de recomandări.

Fără schimbări de schemă — reutilizează tabelele existente.

## ✅ Faza 6.2 — Export & Admin (Module 13, 15) — livrată

- **Modul 13 — Export:** raport medical complet în **PDF** (reportlab) și
  **Word/DOCX** (python-docx) — profil, istoric, analize, tratamente,
  recomandări, cu disclaimer. `/export/report.pdf`, `/export/report.docx`.
- **Modul 15 — Admin:** panou protejat prin rol (`require_admin`) — statistici,
  listare/editare utilizatori (rol, activare), jurnal de audit, feedback.
  Utilizatorii trimit feedback prin `/feedback`. Tabel nou `feedback` (migrație
  Alembic `add feedback table`).

Backend-ul acoperă acum toate modulele de business (1–15).

## ✅ Faza 7 — Frontend & mobil — livrată

- **Next.js 14 (App Router) + TypeScript + TailwindCSS**, design system cu
  paletă alb/albastru/mov/verde prin variabile CSS, **dark mode** fără flash,
  componente UI proprii (Button/Card/Input/Badge — stil shadcn), responsive.
- Client API cu JWT (`lib/api.ts`), context de autentificare (`lib/auth.tsx`),
  guard de rute în shell-ul aplicației.
- Pagini: landing, login, register, dashboard, analize (cu explicații AI),
  documente (upload + OCR), chat AI, medicamente (+ verificare interacțiuni),
  programări, profil (+ export PDF/Word).
- **PWA**: `manifest.webmanifest` + icon + theme-color (instalabilă pe mobil).
- Build de producție verificat (`next build`, 13 rute). Dockerfile multi-stage
  + serviciu în Docker Compose (port 3000).

### Rămas opțional
- Native separat (Swift/Kotlin) dacă e nevoie dincolo de PWA.
- Service worker pentru offline complet; ecrane admin în UI.

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
