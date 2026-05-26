# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION=3.12.7

FROM python:${PYTHON_VERSION}-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-deps .

FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

ARG APP_UID=10001
ARG APP_GID=10001

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    MCP_OAUTH_STORAGE_DIR=/data/oauth \
    PATH="/opt/venv/bin:${PATH}"

RUN groupadd --system --gid ${APP_GID} app \
    && useradd --system --uid ${APP_UID} --gid app --home-dir /app --shell /usr/sbin/nologin app \
    && mkdir -p /data/oauth \
    && chown -R app:app /data

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

USER app

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os, socket, sys; port=int(os.getenv('MCP_PORT', '8000')); s=socket.socket(); s.settimeout(3); sys.exit(0 if s.connect_ex(('127.0.0.1', port)) == 0 else 1)"

STOPSIGNAL SIGTERM

CMD ["python", "-m", "app"]
