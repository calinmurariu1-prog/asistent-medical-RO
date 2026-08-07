# Aplicații mobile (Android & iOS) — Capacitor

Aplicațiile native împachetează **exact frontend-ul web** (Next.js) printr-un
export static, folosind [Capacitor](https://capacitorjs.com). Nu există codebase
paralel: același UI rulează pe web, Android și iOS.

```
Next.js (static export → out/)  ──►  Capacitor WebView  ──►  APK/AAB (Android) / IPA (iOS)
                                         └─ apelează backend-ul FastAPI de pe Render
```

## Cerințe
- **Android:** [Android Studio](https://developer.android.com/studio) (SDK + emulator).
- **iOS:** **macOS** cu **Xcode** (obligatoriu — Apple nu permite build iOS pe alt OS).
- Node 18+ și dependențele instalate (`npm ci` în `frontend/`).

> Build-ul iOS/semnarea și publicarea în store se fac pe mașina ta (Xcode /
> Android Studio) — nu în CI-ul actual.

## Configurare inițială (o singură dată)
Din `frontend/`:

```bash
# 1. Construiește exportul static (out/) cu URL-ul backend-ului de producție
npm run build:mobile

# 2. Adaugă platformele native (creează folderele android/ și ios/)
npx cap add android
npx cap add ios          # doar pe macOS
```

Folderele `android/` și `ios/` se **comit** în repo (convenția Capacitor):
conțin configul proiectului, iconițele și setările de semnare. Doar output-urile
de build (`android/app/build`, `ios/App/build`, `Pods/`) rămân ignorate.

## Dezvoltare & rulare
```bash
npm run mobile:sync        # build:mobile + cap sync (copiază web-ul în native)
npx cap open android       # deschide în Android Studio → Run
npx cap open ios           # deschide în Xcode → Run   (macOS)
```
Scurtături: `npm run mobile:android`, `npm run mobile:ios`.

## URL-ul backend-ului
`NEXT_PUBLIC_API_URL` e „copt" în build. Implicit folosește backend-ul de pe
Render:
```bash
NEXT_PUBLIC_API_URL=https://asistent-medical-backend.onrender.com npm run mobile:sync
```
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
