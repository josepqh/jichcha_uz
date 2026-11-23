#!/usr/bin/env bash
# Runs the LibreOffice tests inside the office worker image, offline, as uid 1001.
# Usage: deploy/test-office-image.sh [image]   (default: jichcha-backend-office:dev)
set -euo pipefail

IMAGE="${1:-jichcha-backend-office:dev}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEV="$(mktemp -d)"
trap 'rm -rf "$DEV"' EXIT
chmod 777 "$DEV"

# 1. Test-only packages into a throwaway directory (needs network).
docker run --rm -u 1001:1001 -v "$DEV:/tmp/dev" --entrypoint python "$IMAGE" \
    -m pip install --no-cache-dir -q --disable-pip-version-check --target /tmp/dev \
    pytest==9.2.0 pytest-django==4.14.0 factory_boy==3.3.3

# 2. The tests themselves, with no network at all.
docker run --rm --network none -u 1001:1001 \
    -e DJANGO_SETTINGS_MODULE=config.settings.test \
    -e DJANGO_SECRET_KEY=test-only \
    -e DATABASE_URL=sqlite:////tmp/test.db \
    -e PYTHONPATH=/tmp/dev \
    -v "$DEV:/tmp/dev:ro" \
    -v "$ROOT/backend/tests:/app/tests:ro" \
    -v "$ROOT/backend/pyproject.toml:/app/pyproject.toml:ro" \
    --entrypoint python "$IMAGE" \
    -m pytest -q -p no:cacheprovider tests/test_pdf_tools.py tests/test_archives.py
