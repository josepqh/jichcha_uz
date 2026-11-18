from .base import *  # noqa: F403
from .base import env

DEBUG = True
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "backend"])
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:5173"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["http://localhost:5173"])
GUEST_COOKIE_SECURE = False
AUTH_COOKIE_SECURE = False

# runserver/tests serve static files themselves; whitenoise is for production.
MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m]  # noqa: F405

# Local convenience: no authenticator needed for the admin panel, and Django admin at /admin/.
STAFF_REQUIRE_2FA = env.bool("STAFF_REQUIRE_2FA", default=False)
DJANGO_ADMIN_URL = env("DJANGO_ADMIN_URL", default="admin/")
