#!/bin/bash
set -e

# ──────────────────────────────────────────────
# Step 1: Configure HuggingFace cache location
# ──────────────────────────────────────────────
export HF_HOME=/app/model_cache
export HF_HUB_CACHE=/app/model_cache/hub

MODEL_DIR="$HF_HUB_CACHE/models--BAAI--bge-small-zh-v1.5"

# ──────────────────────────────────────────────
# Step 2: Download embedding model if not cached
# ──────────────────────────────────────────────
# Check for actual model files, not just the directory — a partial download
# creates the directory structure but leaves it empty, which would cause
# OSError "no file named model.safetensors" at startup.
MODEL_FOUND=0
if [ -d "$MODEL_DIR" ]; then
    # Check if any snapshot directory contains a real model file
    for snap in "$MODEL_DIR"/snapshots/*/; do
        if [ -f "$snap/model.safetensors" ] || [ -f "$snap/pytorch_model.bin" ]; then
            MODEL_FOUND=1
            break
        fi
    done
fi

if [ "$MODEL_FOUND" -eq 0 ]; then
    echo "[entrypoint] Embedding model not found or incomplete, downloading BAAI/bge-small-zh-v1.5 ..."
    python -c "
import os
os.environ['HF_HUB_OFFLINE'] = '0'
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
from huggingface_hub import snapshot_download
snapshot_download(repo_id='BAAI/bge-small-zh-v1.5')
print('[entrypoint] Model downloaded.')
"
    echo "[entrypoint] Model download complete."
else
    echo "[entrypoint] Embedding model found in cache, skipping download."
fi

# ──────────────────────────────────────────────
# Step 3: Set offline mode & start server
# ──────────────────────────────────────────────
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

echo "[entrypoint] Starting uvicorn on 0.0.0.0:8080 ..."
if [ "${UVICORN_RELOAD:-0}" = "1" ]; then
    exec uvicorn server.app:app --host 0.0.0.0 --port 8080 --reload
else
    exec uvicorn server.app:app --host 0.0.0.0 --port 8080
fi