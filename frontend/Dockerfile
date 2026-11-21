# syntax=docker/dockerfile:1

# ---- build: compile the SPA ----
FROM node:24-alpine AS build
WORKDIR /app
RUN --mount=type=cache,target=/root/.npm \
    --mount=type=bind,source=package.json,target=package.json \
    --mount=type=bind,source=package-lock.json,target=package-lock.json \
    npm ci --ignore-scripts
COPY . .
ARG VITE_GOOGLE_CLIENT_ID=""
ARG VITE_LEGAL_NAME=""
ARG VITE_CONTACT_EMAIL=""
ARG VITE_TURNSTILE_SITE_KEY=""
# Absolute links in prerendered pages, sitemap.xml and robots.txt.
ARG SITE_URL="http://localhost:8080"
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID \
    VITE_LEGAL_NAME=$VITE_LEGAL_NAME \
    VITE_CONTACT_EMAIL=$VITE_CONTACT_EMAIL \
    VITE_TURNSTILE_SITE_KEY=$VITE_TURNSTILE_SITE_KEY \
    SITE_URL=$SITE_URL
RUN npm run build

# ---- runtime: unprivileged nginx serves files and proxies the API ----
FROM nginxinc/nginx-unprivileged:1.31-alpine AS runtime
LABEL org.opencontainers.image.title="universe-web"
COPY --link nginx.conf /etc/nginx/conf.d/default.conf
COPY --link --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --retries=3 CMD ["wget", "-qO-", "http://127.0.0.1:8080/healthz"]
