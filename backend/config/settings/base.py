"""Base settings shared by every environment."""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env", overwrite=False)

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "apps.core",
    "apps.users",
    "apps.conversions",
    "apps.staff",
]

MIDDLEWARE = [
    "apps.core.edge.EdgeSecretMiddleware",
    # First on the way in, so last on the way out: sees every cookie the others set.
    "apps.core.cookies.LocalCookieMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "uz"
LANGUAGES = [("uz", "O'zbekcha"), ("ru", "Русский"), ("en", "English")]
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# --- File storage ---------------------------------------------------------
# Local filesystem in development; S3-compatible (MinIO) when USE_S3 is set.
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR / "var" / "media")))
USE_S3 = env.bool("USE_S3", default=False)
if USE_S3:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "bucket_name": env("S3_BUCKET"),
                "endpoint_url": env("S3_ENDPOINT_URL"),
                "access_key": env("S3_ACCESS_KEY"),
                "secret_key": env("S3_SECRET_KEY"),
                "default_acl": None,
                "querystring_auth": True,
                "querystring_expire": 300,
                "file_overwrite": False,
            },
        },
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }

# Uploads above this size are streamed to a temp file instead of memory.
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FILES = 50

# --- Cache / Celery -------------------------------------------------------
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = None
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
# Defaults; run_conversion is dispatched with per-tool limits (Tool.time_limit).
CELERY_TASK_SOFT_TIME_LIMIT = 120
CELERY_TASK_TIME_LIMIT = 150
CELERY_TASK_ROUTES = {
    "apps.conversions.tasks.run_conversion": {"queue": "light"},
    "apps.conversions.tasks.purge_expired": {"queue": "maintenance"},
    "apps.users.tasks.*": {"queue": "maintenance"},
}
CELERY_BEAT_SCHEDULE = {
    "purge-expired-files": {
        "task": "apps.conversions.tasks.purge_expired",
        "schedule": 600.0,
    },
}

# --- DRF / JWT -------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "apps.conversions.throttles.GuestRateThrottle",
        "apps.conversions.throttles.AnonIPRateThrottle",
        "apps.conversions.throttles.SignedInUserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        # Guests: per browser (cookie), plus a ceiling per IP shared by everyone behind it.
        "anon": env("THROTTLE_ANON", default="120/min"),
        "anon_ip": env("THROTTLE_ANON_IP", default="1200/min"),
        "user": env("THROTTLE_USER", default="240/min"),
        "task_create": env("THROTTLE_TASK_CREATE", default="20/min"),
        "task_create_ip": env("THROTTLE_TASK_CREATE_IP", default="120/min"),
        # Login, registration and password reset: per client IP.
        "auth": env("THROTTLE_AUTH", default="10/15m"),
    },
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}

# --- CORS / CSRF -----------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# --- Security headers ------------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
SESSION_COOKIE_HTTPONLY = True

# --- Auth cookies ------------------------------------------------------------
# Refresh token lives only in an httpOnly cookie scoped to the auth endpoints;
# the access token is kept in memory by the SPA.
AUTH_REFRESH_COOKIE = "uv_refresh"
AUTH_REFRESH_COOKIE_PATH = "/api/v1/auth/"
AUTH_COOKIE_SECURE = env.bool("AUTH_COOKIE_SECURE", default=True)

# Public origin of the SPA, used for links in emails.
PUBLIC_ORIGIN = env("PUBLIC_ORIGIN", default="http://localhost:5173")

# Vercel + tunnel setup (compose.tunnel.yaml): requests for EDGE_HOST must carry EDGE_SECRET.
EDGE_HOST = env("EDGE_HOST", default="")
EDGE_SECRET = env("EDGE_SECRET", default="")

# Staff must turn on two-step sign-in before the admin panel API answers them.
STAFF_REQUIRE_2FA = env.bool("STAFF_REQUIRE_2FA", default=True)
# Django's own /admin/ has no two-step sign-in, so it is off unless a path is set. Keep the
# "admin/" prefix (nginx routes it) and add something hard to guess, e.g. "admin/k3x9-panel/".
DJANGO_ADMIN_URL = env("DJANGO_ADMIN_URL", default="")

# Google Identity Services. Sign-in with Google is disabled while this is empty.
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="")

# --- Email -------------------------------------------------------------------
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="jichcha <no-reply@localhost>")
_mail_backend = env("MAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
_mail_options = {}
if _mail_backend.endswith("smtp.EmailBackend"):
    _mail_options = {
        "host": env("SMTP_HOST", default="localhost"),
        "port": env.int("SMTP_PORT", default=587),
        "username": env("SMTP_USER", default=""),
        "password": env("SMTP_PASSWORD", default=""),
        "use_tls": env.bool("SMTP_USE_TLS", default=True),
        "timeout": 10,
    }
MAILERS = {"default": {"BACKEND": _mail_backend, "OPTIONS": _mail_options}}

# --- App settings ----------------------------------------------------------
# Guest identity: random id in a signed, httpOnly cookie.
GUEST_COOKIE_NAME = "uv_guest"
GUEST_COOKIE_MAX_AGE = 60 * 60 * 24 * 365
GUEST_COOKIE_SECURE = env.bool("GUEST_COOKIE_SECURE", default=True)

# Hard ceiling on decoded image size (pixels) to stop decompression bombs.
IMAGE_MAX_PIXELS = env.int("IMAGE_MAX_PIXELS", default=100_000_000)

# LibreOffice for office -> PDF. On macOS: /Applications/LibreOffice.app/Contents/MacOS/soffice
SOFFICE_BINARY = env("SOFFICE_BINARY", default="soffice")
OFFICE_TIMEOUT = env.int("OFFICE_TIMEOUT", default=120)

# Archives: limits checked while unpacking (zip bombs stop early). Applies to extract and repack.
ARCHIVE_MAX_ENTRIES = env.int("ARCHIVE_MAX_ENTRIES", default=1000)
ARCHIVE_MAX_UNPACKED_MB = env.int("ARCHIVE_MAX_UNPACKED_MB", default=1024)


# Cloudflare Turnstile on sign-up and password reset (optional). Site key goes to VITE_TURNSTILE_SITE_KEY.
TURNSTILE_SECRET_KEY = env("TURNSTILE_SECRET_KEY", default="")

# Shared secret of the Telegram bot (internal client). Empty = bot identity disabled.
BOT_API_SECRET = env("BOT_API_SECRET", default="")

# ClamAV daemon. Empty host = scanning off (local dev). In Docker it is the "clamav" service.
CLAMAV_HOST = env("CLAMAV_HOST", default="")
CLAMAV_PORT = env.int("CLAMAV_PORT", default=3310)
CLAMAV_TIMEOUT = env.int("CLAMAV_TIMEOUT", default=120)

# Alerts (`manage.py monitor`): a Telegram chat for the team. The token defaults to the bot's own.
ALERT_TELEGRAM_TOKEN = env("ALERT_TELEGRAM_TOKEN", default=env("TELEGRAM_BOT_TOKEN", default=""))
ALERT_TELEGRAM_CHAT_ID = env("ALERT_TELEGRAM_CHAT_ID", default="")
ALERT_QUEUE_MAX = env.int("ALERT_QUEUE_MAX", default=100)
ALERT_ERROR_RATE = env.float("ALERT_ERROR_RATE", default=0.3)
ALERT_MIN_TASKS = env.int("ALERT_MIN_TASKS", default=10)

# /api/v1/health/ reports "disk": false (HTTP 503) below this much free space on MEDIA_ROOT.
HEALTH_MIN_FREE_MB = env.int("HEALTH_MIN_FREE_MB", default=2048)

# How long task metadata (not files) is kept for history.
TASK_HISTORY_DAYS = 30

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
