# Schema bazei de date

Definită în `backend/app/models/` (SQLAlchemy 2, mapped classes).
Migrații gestionate cu Alembic (`backend/alembic/`).

## Tabele

| Tabel | Model | Rol |
|-------|-------|-----|
| `users` | `User` | Cont de autentificare (email, parolă, rol, MFA, OAuth) |
| `patients` | `Patient` | Profil pacient (1:1 cu user); CNP criptat |
| `consents` | `Consent` | Consimțăminte GDPR (istoric grant/revoke) |
| `audit_logs` | `AuditLog` | Jurnal de acces / acțiuni |
| `allergies` | `Allergy` | Alergii pacient |
| `vaccines` | `Vaccine` | Vaccinuri |
| `emergency_contacts` | `EmergencyContact` | Persoane de contact |
| `doctors` | `Doctor` | Medici (inclusiv medic de familie) |
| `hospitals` | `Hospital` | Spitale/clinici |
| `diagnoses` | `Diagnosis` | Diagnostice codificate (ICD-10) |
| `procedures` | `Procedure` | Proceduri/intervenții codificate |
| `medical_history` | `MedicalHistory` | Cronologie medicală unificată |
| `documents` | `Document` | Documente încărcate (PDF/JPG/PNG/DICOM) |
| `lab_results` | `LabResult` | Valori analize extrase din documente |
| `medications` | `Medication` | Tratamente/medicamente |
| `appointments` | `Appointment` | Programări (consultații/investigații) |
| `ai_chats` | `AIChat` | Sesiuni de chat AI |
| `ai_chat_messages` | `AIChatMessage` | Mesaje chat (cu surse RAG) |
| `notifications` | `Notification` | Notificări push/email/SMS |
| `feedback` | `Feedback` | Feedback utilizatori (Modul 15, admin) |

## Relații principale

- `User` **1—1** `Patient` (`patients.user_id` unic, `ON DELETE CASCADE`).
- `Patient` **1—N**: `allergies`, `vaccines`, `emergency_contacts`,
  `medical_history`, `documents`, `lab_results`, `medications`,
  `appointments`, `ai_chats` (toate `ON DELETE CASCADE`).
- `Document` **1—N** `LabResult` (`lab_results.document_id`, `SET NULL`).
- `AIChat` **1—N** `AIChatMessage` (`CASCADE`).
- `MedicalHistory` **N—1** opțional către `Diagnosis`, `Procedure`, `Doctor`,
  `Hospital` (`SET NULL`).
- `Doctor` **N—1** `Hospital`; `Patient.family_doctor_id` → `Doctor`.
- `Consent`, `AuditLog`, `Notification` **N—1** `User`.

## Indexuri (performanță)

- `users.email` (unic), `ix_users_oauth(provider, subject)`.
- `ix_history_patient_type_date(patient_id, event_type, event_date)`.
- `ix_documents_patient_category(patient_id, category)`.
- `ix_lab_patient_analyte_date(patient_id, analyte, measured_on)` — pentru
  compararea în timp a unui analit (Modul 5).
- `ix_medications_patient_active(patient_id, is_active)`.
- `ix_appointments_patient_start(patient_id, starts_at)`.
- `ix_notifications_user_status(user_id, status)`.
- `ix_chat_messages_chat(chat_id, id)`.
- FK-uri indexate individual pentru join-uri.

## Chei

- **PK:** `id` (integer autoincrement) pe toate tabelele.
- **FK:** cu `ondelete` explicit (`CASCADE` pentru date deținute de pacient,
  `SET NULL` pentru referințe opționale).

## Date sensibile

- `patients.cnp_encrypted` — CNP-ul **nu** se stochează în clar; e criptat cu
  `security.encrypt_field` și nu e returnat niciodată în răspunsuri API.

## Migrații

```bash
cd backend
alembic revision --autogenerate -m "descriere"   # generează
alembic upgrade head                              # aplică
alembic downgrade -1                              # revine un pas
```

Migrația inițială: `alembic/versions/*_initial_schema.py` (creează toate
tabelele de mai sus).
