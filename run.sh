#!/usr/bin/env bash
# Start the Reboot server. Everything runs on localhost.
set -euo pipefail
cd "$(dirname "$0")"
PORT="${PORT:-8765}"
python3 -m pip install -q -r requirements.txt 2>/dev/null || true
if [ ! -f ui/dist/index.html ]; then
  echo "The React UI has not been built yet. Building it now…"
  ( cd ui && npm install --silent && npm run build ) || {
    echo "UI build failed. Run it manually:  cd ui && npm install && npm run build"; }
fi
echo "Reboot → http://127.0.0.1:${PORT}"
# HOST=0.0.0.0 lets other devices on your network push usage to this one. It also
# exposes the API to that network, so it stays opt-in and off by default.
HOST="${REBOOT_HOST:-127.0.0.1}"
export REBOOT_HOST="$HOST"
exec python3 -m uvicorn backend.main:app --host "$HOST" --port "${PORT}" "$@"
