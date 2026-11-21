# syntax=docker/dockerfile:1

ARG PYTHON_IMAGE=python:3.14-slim-trixie

# ---- build: install dependencies into an isolated virtualenv ----
FROM ${PYTHON_IMAGE} AS build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements/base.txt,target=/tmp/requirements.txt \
    pip install --only-binary=:all: -r /tmp/requirements.txt

# ---- runtime ----
FROM ${PYTHON_IMAGE} AS runtime
LABEL org.opencontainers.image.title="universe-backend"
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    MEDIA_ROOT=/data/media \
    TMPDIR=/data/work \
    LANG=C.UTF-8

# Optional faster Debian mirror for slow networks (e.g. DEBIAN_MIRROR=http://mirror.yandex.ru/debian).
# Security updates always come from Debian's own security archive.
ARG DEBIAN_MIRROR=""
RUN if [ -n "$DEBIAN_MIRROR" ]; then \
        sed -i "s|URIs: http://deb.debian.org/debian$|URIs: ${DEBIAN_MIRROR}|" /etc/apt/sources.list.d/debian.sources; \
    fi

# libarchive: archive tools (zip, rar, 7z, tar...) through libarchive-c. DejaVu: a Unicode font for
# PDF page numbers and watermarks (Uzbek, Cyrillic).
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean \
    && apt-get update \
    && apt-get install -y --no-install-recommends libarchive13t64 fonts-dejavu-core

RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --home-dir /app --shell /usr/sbin/nologin app \
    && mkdir -p /data/media /data/work \
    && chown 1001:1001 /data/media /data/work

WORKDIR /app
COPY --link --from=build /opt/venv /opt/venv
COPY --link --chown=1001:1001 manage.py ./
COPY --link --chown=1001:1001 config ./config
COPY --link --chown=1001:1001 apps ./apps

# Static files are collected at build time; a throwaway key is enough for collectstatic.
RUN DJANGO_SECRET_KEY=collectstatic-only DATABASE_URL=sqlite:////tmp/x.db DJANGO_ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput \
    && chown -R 1001:1001 /app/staticfiles

USER 1001:1001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/tools/', timeout=2).status == 200 else 1)"]
# Threads: an upload streamed through nginx (no request buffering) occupies its handler for the whole
# transfer; with plain sync workers three slow uploads would stall every other request.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--worker-class", "gthread", "--threads", "8", "--timeout", "120", "--access-logfile", "-"]

# ---- runtime-office: adds LibreOffice and fonts for office -> PDF (separate, larger image) ----
FROM runtime AS runtime-office
USER root
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        libreoffice-writer-nogui libreoffice-calc-nogui libreoffice-impress-nogui \
        fonts-dejavu-core fonts-liberation2 fonts-noto-core fonts-crosextra-carlito fonts-crosextra-caladea
USER 1001:1001
ENV SOFFICE_BINARY=soffice
HEALTHCHECK NONE
CMD ["celery", "-A", "config", "worker", "-Q", "office", "--concurrency", "2", "--loglevel", "info"]
