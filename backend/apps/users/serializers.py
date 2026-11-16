from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers, status

from apps.core.exceptions import AppError

from .models import User


def check_password_strength(password: str, user: User) -> None:
    """Raise AppError with validator codes so the UI can explain each reason in its language."""
    try:
        password_validation.validate_password(password, user=user)
    except DjangoValidationError as exc:
        codes = sorted({e.code or "invalid" for e in exc.error_list})
        raise AppError(
            "weak_password", "Password is too weak.", status.HTTP_400_BAD_REQUEST, {"reasons": codes}
        ) from None


class MeSerializer(serializers.ModelSerializer):
    has_password = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "language", "email_verified", "has_password", "date_joined", "is_staff"]
        read_only_fields = ["id", "email", "email_verified", "has_password", "date_joined", "is_staff"]

    def get_has_password(self, obj: User) -> bool:
        return obj.has_usable_password()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)
    language = serializers.ChoiceField(choices=User.Language.choices, default=User.Language.UZ)

    def validate_email(self, value: str) -> str:
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise AppError("email_taken", "This email is already registered.", status.HTTP_409_CONFLICT)
        return value

    def validate(self, attrs: dict) -> dict:
        check_password_strength(attrs["password"], User(email=attrs["email"]))
        return attrs

    def create(self, validated_data: dict) -> User:
        try:
            with transaction.atomic():
                return User.objects.create_user(**validated_data)
        except IntegrityError:
            # Two sign-ups for the same address raced past validate_email.
            raise AppError("email_taken", "This email is already registered.", status.HTTP_409_CONFLICT) from None


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)


class GoogleSerializer(serializers.Serializer):
    credential = serializers.CharField(max_length=4096)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    language = serializers.ChoiceField(choices=User.Language.choices, default=User.Language.UZ)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=64)
    token = serializers.CharField(max_length=128)
    new_password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)


class DeleteAccountSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False, required=False)
    # Accounts without a password confirm with a fresh Google sign-in instead.
    google_credential = serializers.CharField(write_only=True, max_length=4096, required=False)
