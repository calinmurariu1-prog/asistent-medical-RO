# med-llm-service

Micro-serviciu Node.js care expune un endpoint HTTP simplu peste `z-ai` CLI
(`z-ai-web-dev-sdk`). Backend-ul Python (FastAPI) îl apelează prin `httpx`.

```
FastAPI  ─HTTP POST /complete─►  Node.js (:3031)  ─►  z-ai CLI  ─►  LLM
```

## API

- `GET /health` → `{"status":"ok","provider":"z-ai-medllm"}`
- `POST /complete` — body `{"system": "...", "user": "..."}` → `{"response": "..."}`

## Rulare

Cu Docker Compose (recomandat): pornește automat ca serviciul `med-llm`.

Local, fără Docker:

```bash
npm install -g z-ai-web-dev-sdk
node server.mjs
# apoi în backend: AI_DEFAULT_PROVIDER=medllm  MED_LLM_URL=http://localhost:3031
```

## Verificare

```bash
curl http://localhost:3031/health
curl -X POST http://localhost:3031/complete \
  -H 'Content-Type: application/json' \
  -d '{"user":"Ce este tensiunea arterială?"}'
```

Timeout implicit: 90 s. La orice eroare, providerul Python întoarce
disclaimer-ul (fără să pice cererea).
