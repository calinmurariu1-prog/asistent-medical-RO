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

## Stripe (web)
Pe web, abonamentele se plătesc cu cardul prin **Stripe Checkout**, iar starea se
sincronizează prin **webhook** (exact ca la IAP pe mobil).

```
Web app ─POST /billing/stripe/checkout─► URL Checkout ─► pagina Stripe ─► card
   ▲                                                                       │
   └────── /subscription?status=success ◄── redirect ◄────────────────────┘
Stripe ─webhook─► POST /billing/stripe/webhook ─► actualizează Subscription
```

**Endpoint-uri:**
| Metodă | Rută | Rol |
|---|---|---|
| POST | `/billing/stripe/checkout` | Creează o sesiune Checkout (`{plan}`) → `{url}`. |
| POST | `/billing/stripe/portal` | Portal de facturare (gestionează/anulează) → `{url}`. |
| POST | `/billing/stripe/webhook` | Evenimente Stripe (checkout completat, reînnoire, anulare). |

**Configurare (o singură dată):**
1. În Stripe Dashboard creează **Produse + Prețuri recurente** (Premium, Familie).
2. Setează pe backend:
   ```
   STRIPE_SECRET_KEY=sk_live_...            # sau sk_test_... la testare
   STRIPE_WEBHOOK_SECRET=whsec_...
   STRIPE_PRICES="premium:price_xxx,family:price_yyy"
   # opțional (au default pe FRONTEND_URL):
   STRIPE_SUCCESS_URL=https://<web>/subscription?status=success
   STRIPE_CANCEL_URL=https://<web>/subscription?status=cancel
   STRIPE_PORTAL_RETURN_URL=https://<web>/subscription
   ```
3. În Stripe → Developers → Webhooks, adaugă endpoint-ul
   `https://<backend>/api/v1/billing/stripe/webhook` cu evenimentele
   `checkout.session.completed`, `customer.subscription.updated`,
   `customer.subscription.deleted`. Copiază *Signing secret* în
   `STRIPE_WEBHOOK_SECRET`.

**Fără chei (dev):** cu `STRIPE_ALLOW_MOCK=true` (implicit), `checkout`/`portal`
întorc URL-uri mock, iar pagina „Abonament" aplică planul direct pentru demo;
webhook-ul acceptă evenimente JSON fără verificarea semnăturii. Testele
(`tests/test_stripe.py`) acoperă checkout, portal și sincronizarea din webhook
(activare, anulare, schimbare de preț). **Dezactivează `STRIPE_ALLOW_MOCK` în
producție.**

## Produse & planuri (mobil)
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
