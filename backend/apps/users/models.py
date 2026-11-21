import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra) -> User:
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra) -> User:
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email: str, password: str | None = None, **extra) -> User:
        extra["is_staff"] = True
        extra["is_superuser"] = True
        return self._create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """Account identified by email. Registration is optional on the platform."""

    class Language(models.TextChoices):
        UZ = "uz", "O'zbekcha"
        RU = "ru", "Русский"
        EN = "en", "English"
        ZH = "zh", "中文"
        ES = "es", "Español"
        HI = "hi", "हिन्दी"
        AR = "ar", "العربية"
        FR = "fr", "Français"
        PT = "pt", "Português"
        DE = "de", "Deutsch"
        JA = "ja", "日本語"
        TR = "tr", "Türkçe"
        KO = "ko", "한국어"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.UZ)
    # True once the person proved control of the address (Google sign-in or a password reset link).
    email_verified = models.BooleanField(default=False)
    # Two-step sign-in with an authenticator app (RFC 6238). The secret is set at setup and only
    # takes effect once a first code confirms it; last_step stops a code from being used twice.
    totp_secret = models.CharField(max_length=64, blank=True, default="")
    totp_enabled = models.BooleanField(default=False)
    totp_last_step = models.BigIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "users"
        constraints = [
            models.UniqueConstraint(Lower("email"), name="users_email_lower_uniq"),
        ]

    def __str__(self) -> str:
        return self.email
