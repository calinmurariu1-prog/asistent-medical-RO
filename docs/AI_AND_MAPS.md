# AI (Gemini) & Google Maps — setup

Both features work out of the box with **no keys** (AI → offline mock, Maps →
mock provider + no visual map). Add the keys below to enable the real services.

## 1. AI — Google Gemini (free)

Default provider is **Gemini 2.0 Flash** (`AI_DEFAULT_PROVIDER=gemini`).

1. Get a free key: https://aistudio.google.com/app/apikey
2. Set it in the backend environment:
   ```
   GEMINI_API_KEY=AIza...
   GEMINI_MODEL=gemini-2.0-flash
   ```
3. Restart the backend. That's it — document extraction, record summaries and
   chat now use Gemini. With no key, the service silently uses the mock, so the
   app never breaks.

Notes:
- Gemini reads images/PDFs, has a large context window and good Romanian.
- Safety filters are relaxed in `GeminiProvider` so clinical terms (diagnoses,
  medication, dosages) are not false-flagged.
- To switch providers later, set `AI_DEFAULT_PROVIDER` to `anthropic` / `openai`
  and add that provider's key. Groq (Llama, OpenAI-compatible) can be added as a
  new provider if a fast open-source fallback is wanted.

## 2. Google Maps — nearby doctors + interactive map

Two keys, from the same Google Cloud project (https://console.cloud.google.com/):

| Key | Where | Restriction | APIs to enable |
|-----|-------|-------------|----------------|
| `GOOGLE_MAPS_API_KEY` | backend (server) | IP / none | **Places API (New)**, **Geocoding API** |
| `NEXT_PUBLIC_GOOGLE_MAPS_KEY` | frontend (browser) | HTTP referrer + Android app | **Maps JavaScript API** |

Steps:
1. Create a project, enable the 3 APIs above.
2. Create **two** API keys:
   - Server key → `GOOGLE_MAPS_API_KEY` (restrict to the backend's IP, or leave
     unrestricted while testing).
   - Browser key → `NEXT_PUBLIC_GOOGLE_MAPS_KEY`. Restrict by:
     - HTTP referrers: your web domain (e.g. `https://*.onrender.com/*`) and
       `http://localhost:3000/*` for dev.
     - For the Android app, add an **Android** restriction with the package
       `ro.asistentmedical.app` and the app's SHA-1.
3. Set both in the environment and rebuild.

Behavior:
- The **Găsește medici** page uses the browser key to render an interactive map
  with a pin per result and the user's location; tapping a pin or a result card
  links the two. Without the browser key the list still works, just no map.
- The nearby search itself runs **server-side** with the server key (the browser
  never sees it).

### Baking the browser key into the Android build

The APK/AAB build reads `NEXT_PUBLIC_*` at compile time. To ship the map in the
native app, pass the browser key to the release workflow (e.g. as a
`NEXT_PUBLIC_GOOGLE_MAPS_KEY` secret wired into the build step). Until then the
web app has the map and the app shows the list.
