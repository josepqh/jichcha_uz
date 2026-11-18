from .base import *  # noqa: F403

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
GUEST_COOKIE_SECURE = False
AUTH_COOKIE_SECURE = False
GOOGLE_CLIENT_ID = "test-client.apps.googleusercontent.com"
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_RATES": {
        "anon": "1000/min",
        "anon_ip": "1000/min",
        "user": "1000/min",
        "task_create": "1000/min",
        "task_create_ip": "1000/min",
        "auth": "1000/min",
    },
}

# runserver/tests serve static files themselves; whitenoise is for production.
MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m]  # noqa: F405

TURNSTILE_SECRET_KEY = ""  # tests that need it switch it on

STAFF_REQUIRE_2FA = False  # tests that need it switch it on
DJANGO_ADMIN_URL = "admin/"
