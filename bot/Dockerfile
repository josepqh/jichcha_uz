# syntax=docker/dockerfile:1
ARG PYTHON_IMAGE=python:3.14-slim-trixie

# ---- build: dependencies in a venv ----
FROM ${PYTHON_IMAGE} AS build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=/tmp/requirements.txt \
    pip install -r /tmp/requirements.txt

# ---- runtime ----
FROM ${PYTHON_IMAGE} AS runtime
LABEL org.opencontainers.image.title="universe-bot"
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --no-create-home --shell /usr/sbin/nologin app
WORKDIR /app
COPY --link --from=build /opt/venv /opt/venv
COPY --link --chown=1001:1001 universe_bot ./universe_bot
USER 1001:1001
# Webhook mode listens here (nginx forwards /telegram/webhook); polling mode needs no port.
EXPOSE 8081
CMD ["python", "-m", "universe_bot"]
