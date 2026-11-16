# Universe

Free file converter platform. Requirements and roadmap: [docs/TZ.md](docs/TZ.md).

**Slice 1 (done):** image format conversion, image compression, images → PDF, for guests and
registered users, with anti-abuse limits, automatic file deletion and uz/ru/en UI.

**Slice 2 (done):** accounts: email + password sign-up and sign-in, Google sign-in (needs `GOOGLE_CLIENT_ID`),
password reset by email, account page with 30-day history, language preference and account deletion.

**Slice 3 (done):** Word/Excel/PowerPoint/OpenDocument → PDF (LibreOffice), PDF merge, split, page organizer
(reorder/rotate/delete with pdf.js thumbnails), PDF compression, PDF → JPG/PNG. PDF → Word is postponed until the
engine licence is decided (the best engine, pdf2docx/PyMuPDF, is AGPL).

**Slice 4 (done):** archives (extract ZIP/RAR/7Z/TAR/GZ/BZ2/XZ, pack any files into ZIP/7Z, RAR/7Z/TAR → ZIP/7Z) and
e-books (EPUB, FB2, MOBI, AZW3, PDF, DOCX → EPUB/MOBI/AZW3/PDF via Calibre). Production groundwork: ClamAV scanning,
daily database backups, health check, optional Sentry, CI, hardened worker containers, privacy policy and terms.

**Slice 5 (done):** Telegram bot (`bot/`, aiogram v3): send a file → action buttons that match the website's
sections; an album of photos → one PDF, an album of PDFs → merge; uz/ru/en; files over 20 MB get a link to the
website. Each Telegram user has their own limits and tasks.

## Stack

- **Backend:** Python 3.14, Django 6.1, DRF, Celery + Redis, PostgreSQL 18, Pillow + pillow-heif, img2pdf,
  pikepdf (MPL), pypdfium2 (BSD/Apache), LibreOffice headless (MPL), libarchive (BSD), Calibre (GPL, run as a
  separate process) — no AGPL engines
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS 4, TanStack Query, Zustand, react-i18next
- **Runtime:** Docker Compose (nginx → gunicorn, Celery workers + beat, ClamAV, Postgres backups)

## Run everything in Docker

```bash
cp .env.example .env   # then set DJANGO_SECRET_KEY, POSTGRES_PASSWORD, VITE_LEGAL_NAME, VITE_CONTACT_EMAIL
docker compose up -d --build --wait
```

The first start takes a few minutes: ClamAV downloads its virus signatures before the workers start.

Open http://localhost:8080. Create an admin account with
`docker compose exec backend python manage.py createsuperuser` (admin at `/admin/`).

## Local development

Postgres and Redis run in Docker on ports **15432** and **16379** (the default ports are often taken
by other projects on this machine). The `.env` URLs already point there.

Don't run the host Celery worker while the full Docker stack is up: both read the same Redis queues, and a
task picked up by the host worker can't find its files (they are in the Docker volume).

```bash
docker compose up -d --wait db cache

cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements/dev.txt
brew install --cask libreoffice calibre       # optional: office -> PDF and e-books
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver            # API on :8000
.venv/bin/python -m celery -A config worker -Q light,office,ebook,maintenance -l info

cd ../frontend
npm ci --ignore-scripts
npm run dev                                      # UI on :5173, proxies /api to :8000
```

## Tests

```bash
cd backend && .venv/bin/pytest --cov                 # unit + API tests
cd frontend && npm test                              # unit tests
cd frontend && npx playwright test                   # E2E against :5173 (needs backend + worker)
cd frontend && E2E_BASE_URL=http://localhost:8080 npx playwright test   # E2E against Docker stack
deploy/test-office-image.sh                           # LibreOffice + Calibre tests inside the worker image, offline
```

CI (`.github/workflows/ci.yml`) runs lint, backend and frontend tests, E2E and the Docker builds on every push and
pull request. Actions are pinned to commit SHAs and the token is read-only.

## API (v1)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/tools/` | Tool catalog |
| GET | `/api/v1/usage/` | Limits and today's usage for the caller |
| POST | `/api/v1/tasks/` | Multipart: `tool`, `options` (JSON), `files[]` → 202 + task |
| GET | `/api/v1/tasks/{id}/` | Task status and outputs (owner only) |
| DELETE | `/api/v1/tasks/{id}/` | Delete files now |
| GET | `/api/v1/tasks/history/` | Registered users' history |
| GET | `/api/v1/files/{file_id}/?t=…` | Download an output via its signed link (valid until the file expires) |
| POST | `/api/v1/auth/register/`, `/auth/login/`, `/auth/google/` | Start a session: access token in the body, refresh token in an httpOnly cookie |
| POST | `/api/v1/auth/refresh/`, `/auth/logout/` | Rotate / revoke the refresh cookie |
| POST | `/api/v1/auth/password/reset/`, `/auth/password/reset/confirm/` | Email a reset link / set a new password |
| GET, PATCH, DELETE | `/api/v1/me/` | Profile, language, delete account (password, or a fresh Google sign-in) |
| GET | `/api/v1/health/` | 200/503 with pass/fail for database, cache and free disk; for monitors |

Tools: `image-convert`, `image-compress`, `images-to-pdf`, `office-to-pdf`, `pdf-merge`, `pdf-split`,
`pdf-organize`, `pdf-compress`, `pdf-to-images`, `archive-extract`, `archive-create` (any file type),
`archive-convert`, `ebook-convert`.

## Conversion workers

- Queues: `light` (images, PDF, archives), `office` (LibreOffice) and `ebook` (Calibre). In Docker they run in
  separate containers (`worker`; `worker-office` for office + ebook) on an `internal` network with no internet
  access (only Postgres, Redis and ClamAV are reachable), as a non-root user with a read-only root filesystem, no
  Linux capabilities, `no-new-privileges`, and CPU/memory/process limits. Scratch files live in `/data/work`.
- Worker processes mark themselves non-dumpable, so a converter tricked into reading local files cannot read the
  worker's environment (database URL, secret key) from `/proc`.
- Archives are unpacked as a stream with limits checked on the fly (`ARCHIVE_MAX_ENTRIES`, default 1000;
  `ARCHIVE_MAX_UNPACKED_MB`, default 1024), into numbered files; names are cleaned (no `..`, no absolute paths),
  links and devices are skipped, and nested archives are not opened. Password-protected archives are refused.
- Each office conversion uses a fresh LibreOffice profile that blocks link/field updates on load, macros, OLE and
  DDE, so a document cannot pull server files (e.g. an `INCLUDETEXT` field) or URLs into its PDF.
- Calibre runs with its own throwaway home/config directory and a minimal environment, like LibreOffice. Tests
  check that EPUB manifest paths, embedded `file://` URLs and FB2 external entities cannot pull server files in.
- Local development needs LibreOffice and Calibre (`brew install --cask libreoffice calibre`), with
  `SOFFICE_BINARY` and `EBOOK_CONVERT_BINARY` in `.env`. In Docker both are on `PATH`.

## Telegram bot

- Code in `bot/` (aiogram 3, aiohttp, Redis). It talks to the API as a trusted internal client: every request
  carries `X-Bot-Secret` (`BOT_API_SECRET`) and `X-Telegram-User-Id`. The backend then treats each Telegram user as
  a guest of their own (separate daily limits, throttles and task ownership); IP ceilings don't apply, since all
  Telegram users arrive from the bot's address. nginx strips both headers from public traffic.
- Private chats only; a button works only for the user it was shown to; one job per user at a time.
- Telegram limits: the bot can fetch files up to 20 MB (bigger ones get a link to the right page of the website)
  and send files up to 50 MB (bigger results are sent as a signed download link). More than 10 results arrive as
  one zip.
- Local run (long polling): set `TELEGRAM_BOT_TOKEN` and `BOT_API_SECRET` in `.env`, start the backend and a
  worker, then:

  ```bash
  cd bot && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
  .venv/bin/python -m universe_bot
  .venv/bin/pytest            # fake Telegram session and fake backend; no token needed
  ```

- Docker: `docker compose --profile bot up -d`. For production set `TELEGRAM_WEBHOOK_URL`
  (`https://<domain>/telegram/webhook`) and `TELEGRAM_WEBHOOK_SECRET`; nginx forwards that path to the bot, and
  updates without Telegram's secret header are rejected. Only one process may poll a token at a time.

## Operations

- **Virus scanning:** the `clamav` service (ClamAV, signatures auto-updated). Every upload is scanned on the
  worker before any converter opens it; infected files fail with `malware_detected` and are deleted. If clamd is
  unreachable, tasks fail with `scan_unavailable` instead of being processed unscanned. Disabled when
  `CLAMAV_HOST` is empty (local development).
- **Backups:** the `db-backup` service runs `pg_dump` daily into the `backups` volume and keeps
  `BACKUP_KEEP_DAYS` (7) days. For an off-site copy (a backup on the same disk does not survive losing the disk),
  copy `backup.env.example` to `backup.env` and fill in an rclone remote (S3-compatible storage behind rclone's
  `crypt` layer: the dumps contain emails and password hashes). Each dump is then copied off the server and remote
  copies older than `BACKUP_REMOTE_KEEP_DAYS` (30) are removed. User files are never backed up by design.
  Restore: `docker compose exec -T db pg_restore --clean --if-exists -U universe -d universe < universe-YYYYMMDD-HHMMSS.dump`
  (copy the dump out with `docker compose cp db-backup:/backups/<file> .`).
- **Alerts:** the `monitor` service checks the database, Redis, free disk, queue lengths, workers, ClamAV and the
  error rate every 5 minutes and posts to a Telegram chat: once when something breaks and once when it recovers.
  Add the bot to the team chat, send `/id`, and put the number in `ALERT_TELEGRAM_CHAT_ID`.
- **Robot check:** set `TURNSTILE_SECRET_KEY` and `VITE_TURNSTILE_SITE_KEY` (Cloudflare Turnstile) to protect
  sign-up and password reset from scripts. Off when empty.
- **Monitoring:** point an uptime monitor at `/api/v1/health/` (503 when the database, Redis or free disk —
  `HEALTH_MIN_FREE_MB`, default 2 GB — is not OK). Set `SENTRY_DSN` to send errors to Sentry; events are scrubbed
  of cookies, headers, query strings, bodies, local variables and user data.
- **Legal pages:** `/{lang}/privacy` and `/{lang}/terms`. Set `VITE_LEGAL_NAME` and `VITE_CONTACT_EMAIL` before
  launch, and have a lawyer review the texts.

## Auth notes

- The access token (15 min) lives in memory only; the refresh token (7 days, rotated, blacklisted on use) is an
  httpOnly `SameSite=Strict` cookie scoped to `/api/v1/auth/`.
- Google sign-in: create a "Web application" OAuth client in Google Cloud Console, add the site origin to
  *Authorized JavaScript origins*, then set `GOOGLE_CLIENT_ID` and `VITE_GOOGLE_CLIENT_ID` in `.env`.
- Emails go to the worker log by default (`MAIL_BACKEND` console). Set the `SMTP_*` values for real delivery.
- Deleting an account needs more than the access token: the password, or for Google-only accounts a Google
  sign-in made in the last 10 minutes with the same email (`google_credential` in the `DELETE /api/v1/me/` body).
- Conversion starts are limited per account or guest browser (`THROTTLE_TASK_CREATE`, 20/min), plus a shared
  ceiling for all guests behind one IP (`THROTTLE_TASK_CREATE_IP`, 120/min), so mobile CGNAT users don't block
  each other.

Errors use one envelope: `{"error": {"code", "message", "details"}}`; `code` is translated in the UI.
