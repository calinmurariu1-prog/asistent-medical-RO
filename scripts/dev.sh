#!/usr/bin/env bash
# ============================================================================
# Localhost de dezvoltare/test — fără Docker.
# Backend FastAPI pe SQLite (:8000) + frontend Next.js dev (:3000).
# Rulează:  bash scripts/dev.sh   (Ctrl+C oprește ambele)
# ============================================================================
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# ---- Backend ----
cd "$ROOT/backend"
[ -d .venv ] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

export SECRET_KEY="${SECRET_KEY:-$(openssl rand -hex 32)}"
export DATA_ENCRYPTION_KEY="${DATA_ENCRYPTION_KEY:-$(python -c 'import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())')}"
export DATABASE_URL="${DATABASE_URL:-sqlite:///$ROOT/backend/dev.db}"
export BACKEND_CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"

alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACK_PID=$!

# ---- Frontend ----
cd "$ROOT/frontend"
[ -d node_modules ] || npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev &
FRONT_PID=$!

trap 'kill $BACK_PID $FRONT_PID 2>/dev/null || true' EXIT INT TERM

echo ""
echo "  ▸ Backend  API   : http://localhost:8000"
echo "  ▸ API docs       : http://localhost:8000/docs"
echo "  ▸ Frontend       : http://localhost:3000"
echo "  (Ctrl+C oprește ambele)"
echo ""
wait
