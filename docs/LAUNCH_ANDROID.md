# Plan de lansare pe Android (Google Play) — Asistent Medical AI

Aplicație patient-facing (Capacitor peste Next.js), cu abonamente și, în curând,
conectare Bluetooth la dispozitive/ceas. Fiind **aplicație de sănătate**, Google
aplică politici suplimentare. Planul e pe faze; fiecare are un „Definition of
Done".

---

## Faza 0 — Decizii înainte de start
- [ ] **Cont Play Console**: personal sau firmă (SRL)? Firma dă mai multă
      credibilitate pentru o app medicală, dar cere verificare de identitate
      (D-U-N-S). Taxă unică dezvoltator: **25 USD**.
- [ ] **Scope v1**: lansăm cu ce avem (dosar, analize, sănătate prin import +
      sync nativ, AI, abonamente) și adăugăm **Bluetooth/ceas** în v1.1? (recomandat)
      sau îl includem în v1?
- [ ] **Traseu de lansare**: Internal testing → Closed testing → Production cu
      **staged rollout** (recomandat), nu direct în producție.
- [ ] **Model AI în producție**: care provider real (Anthropic/OpenAI/z.ai) și
      buget. Fără cheie rămâne pe mock (nu e ok pentru lansare reală).

---

## Faza 1 — Pregătire produs (feature freeze)
- [ ] Activează plugin-urile native necesare și testează pe telefon real:
      health (HealthKit/Health Connect), push (FCM), IAP (Play Billing).
- [ ] Backend de **producție** stabil și accesibil (nu free tier care „adoarme"):
      Render paid sau alt host; verifică `validate_production_config`.
- [ ] **Ștergere cont în aplicație** (Play o cere pentru apps cu cont): avem GDPR
      delete pe backend — expune-l clar în UI (Profil → Șterge contul) + o pagină
      web de ștergere (URL public cerut de Play).
- [ ] Verifică disclaimer medical vizibil (avem „NU pune diagnostice").

**DoD:** build de release rulează pe 2–3 telefoane reale fără crash pe fluxurile
principale.

---

## Faza 2 — Build de release semnat (AAB)
Play cere **Android App Bundle (.aab)**, semnat, nu APK.
- [ ] **targetSdk la zi**: Play cere apps noi să țintească un API recent (în
      2025–2026 e **API 35** minim, curând 36). Proiectul e pe **34** → bump
      `compileSdkVersion`/`targetSdkVersion` în `frontend/android/variables.gradle`
      și testează.
- [ ] **Versionare**: setează `versionCode`/`versionName` în
      `android/app/build.gradle` (ex. 1 / "1.0.0"); crește `versionCode` la fiecare
      upload.
- [ ] **Keystore de upload**: generează un `.jks`, activează **Play App Signing**
      (Google ține cheia de semnare a app-ului; tu ții cheia de upload).
- [ ] **CI de release**: workflow care construiește `bundleRelease` și semnează
      cu keystore-ul din **GitHub Secrets** (base64), produce `app-release.aab` ca
      artifact. (Extindem `android-apk.yml` sau adăugăm `android-release.yml`.)
- [ ] ProGuard/R8 minify (opțional) + testează că WebView-ul merge minificat.

**DoD:** `app-release.aab` semnat, instalabil, se urcă în Play Console fără erori.

---

## Faza 3 — Conformitate & politici Google Play (critic pentru sănătate)
- [ ] **Politică de confidențialitate** (URL public, obligatoriu). Trebuie să
      acopere: date medicale, AI, Bluetooth, Health Connect, ștergere date.
- [ ] **Data safety form** în Play Console: ce date colectezi (sănătate, cont),
      cum le folosești, criptare, ștergere. Datele de sănătate = categorie
      sensibilă.
- [ ] **Permisiuni justificate**: `INTERNET`, `POST_NOTIFICATIONS` (Android 13+),
      `BLUETOOTH_SCAN`/`BLUETOOTH_CONNECT` (Android 12+), Health Connect. Fiecare
      cere justificare; permisiunile „sensibile" cer declarație.
- [ ] **Health Connect**: dacă citim din Health Connect, aplicăm la programul de
      acces + respectăm politica Google pentru date de sănătate.
- [ ] **Play Billing obligatoriu** pentru abonamente digitale (avem IAP) — nu
      Stripe pe Android.
- [ ] **Content rating** (chestionar) + **target audience** (adulți; NU pentru
      copii, dată fiind natura medicală).
- [ ] Fără **claim-uri medicale** interzise (diagnostic/tratament) — mesajul
      „orientativ, nu înlocuiește medicul" ajută.

**DoD:** toate formularele Play completate, fără avertismente de politică.

---

## Faza 4 — Listing în magazin (assets)
- [ ] Iconiță (avem, generată din logo) — 512×512 pentru listing.
- [ ] **Feature graphic** 1024×500.
- [ ] **Screenshot-uri** telefon (min. 2–8): dashboard cu inele, sănătate,
      analize cu grafic, chat AI, abonament. (Le pot genera din aplicația reală.)
- [ ] Titlu, descriere scurtă (80), descriere lungă (4000) — în română (+ engleză
      opțional).
- [ ] Categorie: **Medical** sau **Health & Fitness**.

**DoD:** pagina de magazin completă, în review-ready.

---

## Faza 5 — Testare
- [ ] **Internal testing track**: urci AAB-ul, adaugi testeri (email-uri), instalezi
      via link Play.
- [ ] **Pre-launch report**: Google rulează automat app-ul pe device-uri reale și
      raportează crash-uri/accesibilitate/securitate.
- [ ] **Closed testing** (Play cere acum ~12–14 testeri, 14 zile pentru conturile
      personale înainte de producție).
- [ ] Matrice minimă de device-uri: 1 low-end (Android 10–12), 1 modern (13–15).

**DoD:** 0 crash-uri critice în pre-launch report; fluxuri validate de testeri.

---

## Faza 6 — Lansare
- [ ] Production track cu **staged rollout** (10% → 50% → 100%).
- [ ] Monitorizare **Android vitals** (crash rate, ANR) în Play Console.
- [ ] Crash reporting (opțional: Sentry/Crashlytics) legat în app.

---

## Faza 7 — Post-lansare & următoarele
- [ ] **v1.1 — Bluetooth & ceas** (vezi mai jos).
- [ ] iOS (App Store) — plan separat, pe macOS.
- [ ] Actualizări la politici/targetSdk pe măsură ce Google le cere.

---

## Feature: Setări → Bluetooth & conectare ceas
Ecran nou **Setări** cu o secțiune „Dispozitive & conexiuni":

**Două căi complementare (recomand ambele):**
1. **Health Connect / HealthKit (indirect, cel mai fiabil)** — ceasul (Wear OS,
   Galaxy Watch, Fitbit, Garmin, Huawei etc.) își scrie datele în hub-ul de
   sănătate al telefonului, iar noi le citim de acolo. Avem deja pipeline-ul
   (`/health-data`, sync nativ, detecție dispozitiv). E calea care acoperă cele
   mai multe ceasuri, fără să vorbim direct BLE.
2. **Bluetooth LE direct (pentru dispozitive fără hub)** — tensiometre,
   glucometre, oximetre, cântare BLE care expun profile standard GATT. Plugin:
   **`@capacitor-community/bluetooth-le`**:
   - permisiuni: `BLUETOOTH_SCAN`, `BLUETOOTH_CONNECT` (Android 12+), pe versiuni
     vechi și locație pentru scan;
   - flux UI: „Caută dispozitive" → listă cu semnal → „Conectează" → citește
     caracteristica GATT (ex. Blood Pressure 0x1810, Glucose 0x1808, Weight Scale
     0x181D, Pulse Oximeter 0x1822) → normalizează pe `HealthMetricType` → trimite
     la `/health-data/import-json`.
   - persistăm dispozitivele conectate (avem `health_devices`).

**Backend:** aproape gata — reutilizăm `import-json` + `health_devices`. Eventual
un tabel de „conexiuni" cu tip (health_connect | ble) și status.

**Efort:** mediu. Se testează doar pe telefon real cu un dispozitiv BLE.
Recomandare: **v1.1**, ca să nu întârziem lansarea; în v1 rămâne importul +
sync-ul nativ prin Health Connect.

---

## Ce pot începe imediat (fără să depind de contul tău Play)
1. **Ecranul Setări** + secțiunea „Dispozitive & conexiuni" (UI + Health Connect).
2. **Job CI de release semnat** (AAB) cu keystore din Secrets.
3. **Bump targetSdk 34 → 35** + `versionCode`/`versionName`.
4. **Ștergere cont în UI** + pagină web de ștergere.
5. **Screenshot-uri** pentru listing, generate din aplicația reală.
6. Plugin **BLE** integrat în ecranul Setări (v1.1).

> Ce ține strict de tine: contul Play (25 USD), cheia de semnare (o generez eu,
> tu o păstrezi), politica de confidențialitate (pot scrie o ciornă), și
> completarea formularelor în Play Console.
