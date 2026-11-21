import time

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.db import transaction
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenBackendError, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.state import token_backend
from rest_framework_simplejwt.tokens import RefreshToken

from apps.conversions.models import UsageCounter
from apps.core.exceptions import AppError

from . import google, totp, turnstile
from .models import User
from .serializers import (
    DeleteAccountSerializer,
    EmailVerifySerializer,
    GoogleSerializer,
    LoginSerializer,
    MeSerializer,
    OtpCodeSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    TwoFactorDisableSerializer,
    check_password_strength,
)
from .tasks import send_email_verification, send_password_reset
from .throttles import AuthRateThrottle
from .tokens import clear_refresh_cookie, issue_tokens, revoke_all_sessions, set_refresh_cookie
from .verification import user_for_token


def session_response(user: User, status_code: int = status.HTTP_200_OK) -> Response:
    access, refresh = issue_tokens(user)
    response = Response({"access": access, "user": MeSerializer(user).data}, status=status_code)
    return set_refresh_cookie(response, refresh)


# A Google sign-in used to confirm account deletion must be this recent (seconds).
REAUTH_MAX_AGE = 600


def _confirm_identity(user: User, data: dict) -> None:
    """Destructive actions need proof beyond the access token: the password, or a fresh Google sign-in."""
    if user.has_usable_password():
        if not user.check_password(data.get("password", "")):
            raise AppError("invalid_credentials", "Wrong password.", status.HTTP_403_FORBIDDEN)
        return
    credential = data.get("google_credential")
    if not settings.GOOGLE_CLIENT_ID or not credential:
        raise AppError("reauth_required", "Confirm with Google to continue.", status.HTTP_403_FORBIDDEN)
    try:
        identity = google.verify_credential(credential)
    except google.GoogleTokenError:
        raise AppError("google_failed", "Google sign-in failed.", status.HTTP_403_FORBIDDEN) from None
    if identity.email != user.email.lower():
        raise AppError("google_account_mismatch", "That Google account is not this one.", status.HTTP_403_FORBIDDEN)
    if time.time() - identity.issued_at > REAUTH_MAX_AGE:
        raise AppError("reauth_required", "Confirm with Google to continue.", status.HTTP_403_FORBIDDEN)


def _session_expired() -> AppError:
    return AppError("session_expired", "Please sign in again.", status.HTTP_401_UNAUTHORIZED)


class PublicAuthView(APIView):
    """Credential endpoints: no JWT needed, strict per-IP throttle."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]


def _client_ip(request: Request) -> str | None:
    # Same client address the throttles use (respects NUM_PROXIES).
    return AuthRateThrottle().get_ident(request)


class RegisterView(PublicAuthView):
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        turnstile.require(request.data.get("captcha"), _client_ip(request))
        user = serializer.save()
        lang = serializer.validated_data["language"]
        transaction.on_commit(lambda: send_email_verification.delay(str(user.pk), lang))
        return session_response(user, status.HTTP_201_CREATED)


class LoginView(PublicAuthView):
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # ModelBackend hashes a dummy password for unknown emails, so timing does not reveal accounts.
        user = authenticate(
            request,
            username=serializer.validated_data["email"].strip().lower(),
            password=serializer.validated_data["password"],
        )
        if user is None:
            raise AppError("invalid_credentials", "Wrong email or password.", status.HTTP_401_UNAUTHORIZED)
        totp.require_for(user, serializer.validated_data.get("otp"))
        return session_response(user)


class GoogleLoginView(PublicAuthView):
    def post(self, request: Request) -> Response:
        if not settings.GOOGLE_CLIENT_ID:
            raise AppError("google_disabled", "Google sign-in is not configured.", status.HTTP_404_NOT_FOUND)
        serializer = GoogleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            identity = google.verify_credential(serializer.validated_data["credential"])
        except google.GoogleTokenError:
            raise AppError("google_failed", "Google sign-in failed.", status.HTTP_401_UNAUTHORIZED) from None

        with transaction.atomic():
            user = User.objects.select_for_update().filter(email__iexact=identity.email).first()
            if user is None:
                user = User.objects.create_user(email=identity.email, password=None, email_verified=True)
            else:
                if not user.is_active:
                    raise AppError("account_disabled", "This account is disabled.", status.HTTP_403_FORBIDDEN)
                if not user.email_verified:
                    # Someone may have registered this address before its owner (pre-account takeover):
                    # drop the unverified password and end all its sessions, then hand the account to Google's owner.
                    # The squatter's authenticator goes too, or it could lock the real owner out.
                    if user.has_usable_password():
                        user.set_unusable_password()
                    revoke_all_sessions(user)
                    user.email_verified = True
                    user.totp_secret, user.totp_enabled = "", False
                    user.save(update_fields=["password", "email_verified", "totp_secret", "totp_enabled"])
        totp.require_for(user, serializer.validated_data.get("otp"))
        return session_response(user)


# A rotated refresh token still works for this many seconds and yields the same successor. Covers a
# reload that aborts the refresh response before the browser stores the new cookie, and two tabs
# refreshing at once. Logout and "sign out everywhere" blacklist the successor too, so they still win.
REFRESH_GRACE_SECONDS = 30


def _grace_key(jti: str) -> str:
    return f"auth:rotated:{jti}"


def _rotated_jti(raw: str) -> str | None:
    """jti of a correctly signed, unexpired token, ignoring the blacklist."""
    try:
        return token_backend.decode(raw, verify=True).get("jti")
    except TokenBackendError:
        return None


# How long a refresh waits for another request that is rotating the same token right now.
ROTATION_WAIT_SECONDS = 3.0


def _successor(jti: str | None) -> str | None:
    """The token that replaced this one, if it was rotated within the grace period.

    One token is rotated once: the first request takes a short lock; one arriving meanwhile (two
    tabs, or a reload) waits for that rotation and gets the same successor instead of racing it
    and being refused between "old token blacklisted" and "successor remembered".
    """
    if not jti:
        return None
    key = _grace_key(jti)
    successor = cache.get(key)
    if successor or cache.add(f"{key}:lock", 1, int(ROTATION_WAIT_SECONDS) + 2):
        return successor  # rotated already, or the lock is ours: the caller rotates
    deadline = time.monotonic() + ROTATION_WAIT_SECONDS
    while time.monotonic() < deadline:
        time.sleep(0.05)
        if successor := cache.get(key):
            return successor
    return None


class RefreshView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        raw = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE)
        if not raw:
            raise _session_expired()
        jti = _rotated_jti(raw)
        try:
            new_refresh = _successor(jti)
            if new_refresh:
                access = str(RefreshToken(new_refresh).access_token)  # raises if the successor was revoked
            else:
                serializer = TokenRefreshSerializer(data={"refresh": raw})
                serializer.is_valid(raise_exception=True)
                new_refresh = serializer.validated_data["refresh"]
                access = serializer.validated_data["access"]
                if jti:
                    cache.set(_grace_key(jti), new_refresh, REFRESH_GRACE_SECONDS)
            user = User.objects.get(pk=RefreshToken(new_refresh)["user_id"], is_active=True)
        except TokenError, InvalidToken, User.DoesNotExist, KeyError:
            response = Response(
                {"error": {"code": "session_expired", "message": "Please sign in again.", "details": {}}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            return clear_refresh_cookie(response)
        response = Response({"access": access, "user": MeSerializer(user).data})
        return set_refresh_cookie(response, new_refresh)


class LogoutView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        raw = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE)
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except TokenError:
                pass  # already invalid: nothing to revoke
        return clear_refresh_cookie(Response(status=status.HTTP_204_NO_CONTENT))


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response(MeSerializer(request.user).data)

    def patch(self, request: Request) -> Response:
        serializer = MeSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request: Request) -> Response:
        user: User = request.user
        serializer = DeleteAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _confirm_identity(user, serializer.validated_data)
        with transaction.atomic():
            revoke_all_sessions(user)
            UsageCounter.objects.filter(subject=f"u:{user.pk}").delete()
            user.delete()  # cascades to tasks; stored files are removed by the TaskFile post_delete signal
        return clear_refresh_cookie(Response(status=status.HTTP_204_NO_CONTENT))


class PasswordResetRequestView(PublicAuthView):
    def post(self, request: Request) -> Response:
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        turnstile.require(request.data.get("captcha"), _client_ip(request))
        email = serializer.validated_data["email"].strip().lower()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user is not None:
            lang = serializer.validated_data["language"]
            transaction.on_commit(lambda: send_password_reset.delay(str(user.pk), lang))
        # Same answer whether or not the account exists.
        return Response(status=status.HTTP_202_ACCEPTED)


class PasswordResetConfirmView(PublicAuthView):
    def post(self, request: Request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(data["uid"])), is_active=True)
        except ValueError, TypeError, OverflowError, User.DoesNotExist:
            user = None
        if user is None or not default_token_generator.check_token(user, data["token"]):
            raise AppError("invalid_reset_link", "This link is invalid or has expired.")
        check_password_strength(data["new_password"], user)
        # The emailed link alone must not get past two-step sign-in.
        totp.require_for(user, data.get("otp"))
        with transaction.atomic():
            user.set_password(data["new_password"])
            user.email_verified = True  # following the emailed link proves control of the address
            user.save(update_fields=["password", "email_verified"])
            revoke_all_sessions(user)
        return session_response(user)


class PasswordChangeView(APIView):
    """Change the password while signed in. Ends every other session and starts a fresh one here."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request: Request) -> Response:
        user: User = request.user
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if not user.has_usable_password() or not user.check_password(data["current_password"]):
            raise AppError("invalid_credentials", "Wrong password.", status.HTTP_403_FORBIDDEN)
        check_password_strength(data["new_password"], user)
        with transaction.atomic():
            user.set_password(data["new_password"])
            user.save(update_fields=["password"])
            revoke_all_sessions(user)
        return session_response(user)


class TwoFactorSetupView(APIView):
    """Start (or restart) setup: a new secret that only counts once a code confirms it."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        user: User = request.user
        if user.totp_enabled:
            raise AppError("otp_already_enabled", "Two-step sign-in is already on.", status.HTTP_409_CONFLICT)
        if not user.email_verified:
            # Otherwise someone who registered another person's address could lock its owner out.
            raise AppError("email_unverified", "Confirm your email first.", status.HTTP_403_FORBIDDEN)
        user.totp_secret = totp.new_secret()
        user.totp_last_step = 0
        user.save(update_fields=["totp_secret", "totp_last_step"])
        uri = totp.provisioning_uri(user.totp_secret, user.email)
        return Response({"secret": user.totp_secret, "otpauth_uri": uri, "qr": totp.qr_data_uri(uri)})


class TwoFactorEnableView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request: Request) -> Response:
        user: User = request.user
        if user.totp_enabled:
            raise AppError("otp_already_enabled", "Two-step sign-in is already on.", status.HTTP_409_CONFLICT)
        if not user.totp_secret:
            raise AppError("otp_not_started", "Start the setup first.", status.HTTP_400_BAD_REQUEST)
        serializer = OtpCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        totp.check_code(user, serializer.validated_data["code"])
        user.totp_enabled = True
        user.save(update_fields=["totp_enabled"])
        return Response(MeSerializer(user).data)


class TwoFactorDisableView(APIView):
    """Turning it off needs both the password (or a fresh Google sign-in) and a current code."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request: Request) -> Response:
        user: User = request.user
        if not user.totp_enabled:
            raise AppError("otp_not_enabled", "Two-step sign-in is off.", status.HTTP_409_CONFLICT)
        serializer = TwoFactorDisableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _confirm_identity(user, serializer.validated_data)
        totp.check_code(user, serializer.validated_data["code"])
        user.totp_enabled, user.totp_secret = False, ""
        user.save(update_fields=["totp_enabled", "totp_secret"])
        return Response(MeSerializer(user).data)


class EmailVerifyView(PublicAuthView):
    def post(self, request: Request) -> Response:
        serializer = EmailVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = user_for_token(serializer.validated_data["token"])
        if user is None:
            raise AppError("invalid_verify_link", "This link is invalid or has expired.")
        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=["email_verified"])
        return Response({"email_verified": True})


class EmailVerifyResendView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request: Request) -> Response:
        user: User = request.user
        if user.email_verified:
            raise AppError("already_verified", "This email is already confirmed.", status.HTTP_409_CONFLICT)
        lang = request.data.get("language") if request.data.get("language") in User.Language.values else user.language
        transaction.on_commit(lambda: send_email_verification.delay(str(user.pk), lang))
        return Response(status=status.HTTP_202_ACCEPTED)
