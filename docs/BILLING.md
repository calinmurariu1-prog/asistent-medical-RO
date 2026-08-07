# Abonamente & In-App Purchase (Apple / Google)

Abonamentele plătite pe mobil folosesc **StoreKit (iOS)** și **Google Play
Billing (Android)**, cu **validare pe server**. Apple și Google **impun** In-App
Purchase pentru abonamente digitale în aplicațiile din store — nu se poate doar
Stripe pe mobil (Stripe rămâne pentru web).

## Arhitectură

```
App (Capacitor)                Backend (FastAPI)                 Store
─────────────                  ─────────────────                 ─────
purchase(plan) ──StoreKit/Play──►  (UI nativ de plată)  ────────►  Apple / Google
      │  token/receipt
      └──► POST /billing/iap/verify ──► verifier (Apple/Google) ──► App Store / Play API
                                          │  PurchaseVerification
                                          └─► Subscription (plan, status, expiry)

Store server notifications ──► POST /billing/iap/{apple,google}/notifications ──► sync Subscription
```

Verifierele stau în spatele unei interfețe comune (`IAPVerifier`), exact ca
providerii AI: `apple`, `google` și un **mock determinist**. Fără credențiale de
store, factory-ul cade pe mock (`IAP_ALLOW_MOCK=true`), deci fluxul complet
poate fi testat offline.

## Produse & planuri
Product-ID-urile din store se mapează pe planuri prin `IAP_PRODUCTS`:
```
IAP_PRODUCTS="premium_monthly:premium,family_monthly:family"
```
Aceleași ID-uri trebuie configurate în App Store Connect / Play Console și în
`frontend/src/lib/iap.ts` (`PRODUCT_IDS`).

## Endpoint-uri backend
| Metodă | Rută | Rol |
|---|---|---|
| POST | `/billing/iap/verify` | Validează o achiziție (`{platform, product_id, token}`) și activează abonamentul. |
| POST | `/billing/iap/apple/notifications` | App Store Server Notifications V2. |
| POST | `/billing/iap/google/notifications` | Google Real-time Developer Notifications (Pub/Sub). |

Webhook-urile răspund mereu `200` (ca store-ul să nu reia agresiv) și
actualizează abonamentul găsit după `transaction_id`.

## Configurare Apple
1. **App Store Connect → Users and Access → Integrations → App Store Server API**:
   creează o cheie (fișier `.p8`). Notează *Issuer ID* și *Key ID*.
2. Creează produsele de abonament (ex. `premium_monthly`) în App Store Connect.
3. Setează pe backend:
   ```
   APPLE_IAP_BUNDLE_ID=ro.asistentmedical.app
   APPLE_IAP_ISSUER_ID=...
   APPLE_IAP_KEY_ID=...
   APPLE_IAP_PRIVATE_KEY=<conținutul PEM al cheii .p8>
   APPLE_IAP_ENVIRONMENT=production   # sau sandbox la testare
   ```
4. **App Store Server Notifications V2** → URL:
   `https://<backend>/api/v1/billing/iap/apple/notifications`.

## Configurare Google
1. **Google Play Console → Setup → API access**: leagă un proiect Google Cloud și
   creează un **service account** cu acces la Play Developer API (rol *Financial
   data / Manage orders and subscriptions*).
2. Creează produsele de abonament în Play Console.
3. Setează pe backend:
   ```
   GOOGLE_PLAY_PACKAGE_NAME=ro.asistentmedical.app
   GOOGLE_PLAY_SERVICE_ACCOUNT_JSON=<JSON-ul cheii de service account>
   ```
4. **RTDN**: creează un topic Pub/Sub, configurează-l în Play Console
   (Monetization setup → Real-time developer notifications) și un *push
   subscription* către:
   `https://<backend>/api/v1/billing/iap/google/notifications`.

## Client mobil
Fluxul de plată folosește `cordova-plugin-purchase` (expus ca
`window.CdvPurchase`), fără dependență npm hard (build-ul web rămâne neatins).
```bash
cd frontend
npm i cordova-plugin-purchase
npm run mobile:sync         # build:mobile + cap sync
```
`src/lib/iap.ts` prezintă UI-ul nativ de plată și trimite token-ul la
`/billing/iap/verify`. Pe web, `iapAvailable()` întoarce `false` și pagina
„Abonament" folosește schimbarea de plan în modul de testare (până la Stripe).

## Testare (fără store real)
Cu `IAP_ALLOW_MOCK=true` (implicit), verifier-ul mock acceptă orice token care nu
începe cu `invalid` și acordă planul mapat pe produs:
```bash
curl -X POST https://<backend>/api/v1/billing/iap/verify \
  -H "Authorization: Bearer <jwt>" -H "Content-Type: application/json" \
  -d '{"platform":"apple","product_id":"premium_monthly","token":"test123"}'
```
Suita `tests/test_iap.py` acoperă activare, respingere token invalid, produs
necunoscut, platformă greșită și webhook-ul de refund (downgrade).

## De întărit înainte de lansare
- **Verificare semnătură JWS Apple** (lanțul x5c) pe payload-urile primite în
  webhook (acum payload-ul e citit din endpoint-ul TLS autentificat Apple; la
  webhook se decodează fără verificarea lanțului).
- **Autentificarea Pub/Sub** pentru webhook-ul Google (OIDC token verification).
- **Dezactivează `IAP_ALLOW_MOCK`** în producție după ce credențialele reale sunt
  puse (altfel un token fals ar activa un abonament).
- **Idempotență/anti-replay** pe notificări (deduplică după `transaction_id` +
  tip eveniment).
