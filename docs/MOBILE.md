# Aplicații mobile (Android & iOS) — Capacitor

Aplicațiile native împachetează **exact frontend-ul web** (Next.js) printr-un
export static, folosind [Capacitor](https://capacitorjs.com). Nu există codebase
paralel: același UI rulează pe web, Android și iOS.

```
Next.js (static export → out/)  ──►  Capacitor WebView  ──►  APK/AAB (Android) / IPA (iOS)
                                         └─ apelează backend-ul FastAPI de pe Render
```

## Cerințe
- **Android:** Android Studio Otter 2025.2.1+, JDK 21, SDK 36; Android 7/API 24 minim.
- **iOS:** iOS 15+, **macOS** cu **Xcode 26+** (obligatoriu — Apple nu permite build iOS pe alt OS).
- Node 22+ și dependențele instalate (`npm ci` în `frontend/`).

> Build-ul iOS/semnarea și publicarea în store se fac pe mașina ta (Xcode /
> Android Studio) — nu în CI-ul actual.

## Configurare inițială (o singură dată)
Din `frontend/`:

```bash
# iOS (doar pe macOS) — Android e deja în repo (frontend/android/)
npx cap add ios
```

Proiectul nativ **Android este deja generat și comis** în `frontend/android/`
(appId `ro.asistentmedical.app`). Nu mai rulezi `npx cap add android`. Folderul
`ios/` se adaugă pe macOS. Output-urile de build și asset-urile web copiate
(`android/app/build`, `android/app/src/main/assets/public`, `ios/App/build`,
`Pods/`) sunt ignorate — se regenerează cu `cap sync`.

## Test rapid pe Android Studio (pas cu pas)
```bash
cd frontend
npm ci                 # instalează dependențele (o singură dată)
npm run mobile:sync    # build:mobile + cap sync → copiază web-ul în android/
npx cap open android   # deschide proiectul în Android Studio
```
În Android Studio: așteaptă Gradle sync (prima dată descarcă dependențele),
alege un emulator (Device Manager → creează un Pixel cu Google Play) sau un
telefon cu USB debugging, apoi **Run ▶**.

> Prima sincronizare Gradle are nevoie de internet (descarcă Gradle + SDK-urile).
> Ai nevoie de Android SDK instalat din Android Studio (SDK Manager).

Scurtături: `npm run mobile:android` (sync + open), `npm run mobile:ios`.

## URL-ul backend-ului
`NEXT_PUBLIC_API_URL` e „copt" în build. Implicit folosește backend-ul de pe
Render (merge din emulator, care are internet):
```bash
NEXT_PUBLIC_API_URL=https://asistent-medical-backend.onrender.com npm run mobile:sync
```
> ⚠️ Un backend local pe `localhost:8000` **nu** e vizibil din emulatorul
> Android ca `localhost` (acela e emulatorul însuși). Folosește
> `http://10.0.2.2:8000` pentru backend-ul de pe mașina gazdă, sau URL-ul de pe
> Render. Pentru `http://` (necriptat) în emulator, adaugă
> `android:usesCleartextTraffic="true"` în `AndroidManifest.xml`.
Backend-ul acceptă deja originile WebView-ului Capacitor
(`capacitor://localhost`, `https://localhost`, …) în CORS — vezi
`settings.cors_origins`. Autentificarea folosește token Bearer (nu cookie-uri),
deci merge din aplicația nativă fără configurări suplimentare.

## Iconiță & splash
Marca „Puls & scânteie" (`frontend/public/icon.svg`) e sursa. Generează seturile
native cu:
```bash
npm i -D @capacitor/assets
npx capacitor-assets generate --iconBackgroundColor '#2563EB'
```

## Sănătate nativă (HealthKit / Health Connect)
Pe telefon, aplicația poate citi datele **direct de pe dispozitiv** (fără export
de fișiere) și le trimite în același pipeline normalizat (`/health-data`).

1. Instalează un plugin de sănătate (recomandat `capacitor-health`, care acoperă
   HealthKit + Health Connect):
   ```bash
   npm i capacitor-health && npx cap sync
   ```
2. **iOS:** activează *HealthKit* în capabilitățile app-ului (Xcode → Signing &
   Capabilities) și adaugă cheile de privacy în `Info.plist`
   (`NSHealthShareUsageDescription`).
3. **Android:** Health Connect + permisiunile `android.permission.health.READ_*`
   în manifest.
4. Codul client e în `frontend/src/lib/health-native.ts`. `readSamples()` este
   „cusătura" care vorbește cu pluginul — ajustează numele metodelor la pluginul
   ales. Pagina „Date de sănătate" afișează automat butonul *Sincronizează acum*
   când rulează nativ.

Datele native se mapează pe aceleași `HealthMetricType` și se trimit la
`POST /health-data/import-json/{apple_health|google_health}` (import idempotent).

**Detectare automată a ceasului + auto-sync.** Fiecare probă din HealthKit /
Health Connect poartă dispozitivul-sursă (ex. „Apple Watch Series 9"). Clientul
îl citește și îl trimite în câmpul `devices`; backend-ul deduce brandul
(`infer_vendor`) și îl afișează la `GET /health-data/devices` („Dispozitive
detectate" în UI). `useHealthAutoSync()` (montat în `AppShell`) sincronizează
automat la **deschiderea** aplicației și la fiecare **resume** din fundal, gated
de o preferință (`@capacitor/preferences`) — fără upload de fișiere, fără acțiune
din partea utilizatorului. Sincronizarea reală în **background** (iOS
`HKObserverQuery` + background delivery, Android WorkManager / Health Connect
background reads) se activează în codul nativ al pluginului ales.

## Ce urmează (upgrade-uri native)
- **Push notifications:** `@capacitor/push-notifications` + FCM/APNs.
- **Stocare sigură:** token-urile pot trece de la `localStorage` la
  `@capacitor/preferences` (deja instalat) pe nativ.

## Abonamente în store (important pentru SaaS)
Apple și Google **impun In-App Purchase** pentru abonamente digitale în
aplicațiile din store (nu poți folosi doar Stripe pe mobil). Planul:
- **Web:** Stripe Checkout.
- **iOS:** StoreKit / App Store In-App Purchase.
- **Android:** Google Play Billing.

Backend-ul e deja pregătit: modelul `Subscription` are `provider`
(`stripe`/`apple`/`google`) și `external_*` pentru a lega abonamentul de
webhook-urile fiecărui furnizor. Vezi `docs/BILLING.md` (în lucru).

## Actualizare Capacitor 8.5

Pachetele native și pluginurile sunt actualizate împreună. Ghiduri oficiale: [Capacitor 8](https://capacitorjs.com/docs/updating/8-0), [8.5](https://capacitorjs.com/docs/updating/8-5). Proiectul iOS se generează din șablonul actual pe macOS. Nu există încă verificare pe dispozitiv fizic sau build iOS în această livrare.

Versiunile indirecte tar, sharp, uuid și minimatch sunt corectate prin overrides; utilitarul de iconițe folosește același CLI Capacitor ca proiectul. CI rulează auditul npm complet, generarea iconițelor și buildul APK pentru a detecta incompatibilități.

## Stocarea nativă a sesiunii

Exportul mobil setează `NEXT_PUBLIC_SESSION_TRANSPORT=native`. Tokenurile sunt păstrate ca o singură pereche în [SecureStorage](https://github.com/aparajita/capacitor-secure-storage), prin iOS Keychain și Android Keystore. Sincronizarea iCloud este dezactivată; pe iOS cheia este accesibilă numai când dispozitivul este deblocat și nu migrează la alt dispozitiv. Backupul Android al aplicației este dezactivat.

Copia veche din localStorage este eliminată, fără transfer automat: autentifică-te din nou după actualizare. Pluginul este apelat numai pe platformă nativă și numai dacă este disponibil. Nu se folosește implementarea web necriptată și nu se revine la localStorage dacă sistemul refuză stocarea. Deschiderea exportului mobil într-un browser obișnuit nu permite autentificarea; folosește versiunea web cu HttpOnly.

Testele automatizate verifică restaurarea, datele incomplete, erorile de scriere/ștergere și concurența salvare–logout. Ele nu înlocuiesc verificarea pe dispozitive: login, închiderea/redeschiderea aplicației, blocare/deblocare, refresh, logout și reinstalare. iOS Keychain poate păstra datele după dezinstalare; revocarea server-side rămâne autoritatea pentru validitatea sesiunii.


## Exporturi prin dialogul nativ
Exportul JSON din Setări, rapoartele PDF/DOCX din Profil și originalele din Documente folosesc `@capacitor/filesystem` 8.1.3 și `@capacitor/share` 8.0.2. Se scrie o copie în cache-ul privat `medical-exports/<timestamp-uuid>/export.<extensie>`, apoi se deschide dialogul sistemului, fără alegerea automată a unei aplicații destinatare. Android FileProvider expune numai acest subdirector. Nu se cer permisiuni generale pentru stocare externă. Fișierul temporar este necriptat pentru a putea fi citit de aplicația aleasă; utilizatorul inițiază explicit exportul. Nu se șterge imediat la închiderea dialogului, deoarece destinatarul poate citi ulterior.
La următorul export se șterg numai directoarele proprii mai vechi de 24 de ore. Închiderea aplicației nu garantează ștergerea exact la 24 de ore; sistemul poate curăța cache-ul. Copiile salvate/trimise de utilizator nu sunt controlate de aplicație. Limita nativă este 25 MB; fișierele mai mari necesită versiunea web. Anularea/eroarea nu este prezentată drept salvare reușită. Toate aceste descărcări folosesc adaptorul comun, cu răspunsuri autentificate și erori vizibile. Browserul păstrează numele original; copia nativă are un nume generic și extensia fișierului.
Pe macOS, după crearea proiectului iOS și `npx cap sync ios`, adaugă în manifestul de confidențialitate al targetului App motivul `C617.1` pentru `NSPrivacyAccessedAPICategoryFileTimestamp`, păstrând celelalte declarații deja necesare. Acesta este motivul recomandat de documentația oficială Filesystem pentru API-urile de timestamp ale fișierelor. Verifică includerea manifestului în target înainte de arhivare.
Surse: [Filesystem](https://capacitorjs.com/docs/apis/filesystem), [Share](https://capacitorjs.com/docs/apis/share). Testele automate folosesc adaptoare simulate pentru bytes, cale privată, curățare, anulare și erori; buildul web/Capacitor și sincronizarea Android nu dovedesc funcționarea pe un dispozitiv real. Buildul și semnarea iOS necesită macOS/Xcode și contul dezvoltatorului.
