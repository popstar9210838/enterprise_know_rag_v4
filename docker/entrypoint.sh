#!/bin/bash
set -e

# ──────────────────────────────────────────────
# Start server
# ──────────────────────────────────────────────
echo "[entrypoint] Starting uvicorn on 0.0.0.0:8080 ..."
if [ "${UVICORN_RELOAD:-0}" = "1" ]; then
    exec uvicorn server.app:app --host 0.0.0.0 --port 8080 --reload
else
    exec uvicorn server.app:app --host 0.0.0.0 --port 8080
fi