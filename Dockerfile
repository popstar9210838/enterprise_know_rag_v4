# ============================================================
# Stage 1: Build Vue frontend
# ============================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /build
COPY ui/package.json ui/package-lock.json ./
RUN npm config set registry https://registry.npmmirror.com/ && npm ci

COPY ui/ ./
ARG VITE_API_BASE=""
ENV VITE_API_BASE=${VITE_API_BASE}
RUN npm run build

# ============================================================
# Stage 2: Python runtime
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# Copy project metadata first for better layer caching
COPY pyproject.toml ./

# ── Single layer: install build deps → pip install → purge build deps ──
# This avoids layer leakage: if gcc/g++ were removed in a separate RUN,
# the files from the earlier layer would still occupy disk space forever.
RUN sed -i 's|https\?://deb.debian.org|http://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    \
    pip install --no-cache-dir --default-timeout 600 torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir --default-timeout 300 . && \
    \
    apt-get purge -y gcc g++ binutils cpp libgcc-*-dev libstdc++-*-dev linux-libc-dev manpages && \
    apt-get autoremove -y --purge && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /root/.cache/pip /tmp/* && \
    \
    python -c "import fastapi; print('[verify] fastapi OK')" && \
    python -c "import torch; print(f'[verify] torch {torch.__version__} ({torch.__config__.parallel_info()}) OK')"

# Copy application code
COPY server/ server/
COPY config.yaml ./

# Copy built frontend from Stage 1
COPY --from=frontend-builder /build/dist /app/ui/dist

# Create directories for volume mounts
RUN mkdir -p /app/chroma_db /app/data

# Copy entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]
