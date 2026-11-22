"""Suggestions and complaints from the site, emailed to the team (FEEDBACK_EMAIL).

Nothing is stored: the message goes out as an email and that's all. The sender's address, when
given, becomes Reply-To so the team can answer straight from their inbox.
"""

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users import turnstile
from apps.users.throttles import AuthRateThrottle

class FeedbackThrottle(AuthRateThrottle):
    """Per IP, same rate format as sign-in ("5/1h")."""

    scope = "feedback"


class FeedbackSerializer(serializers.Serializer):
    message = serializers.CharField(min_length=10, max_length=4000)
    email = serializers.EmailField(max_length=254, required=False, allow_blank=True)
    page = serializers.CharField(max_length=300, required=False, allow_blank=True)
    language = serializers.CharField(max_length=5, required=False, allow_blank=True)
    # Honeypot: people never see this field; form-filling bots do.
    website = serializers.CharField(max_length=200, required=False, allow_blank=True)


@shared_task(ignore_result=True, autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def send_feedback(message: str, email: str, page: str, language: str) -> None:
    subject = f"jichcha: feedback ({language or '-'})"
    body = f"{message}\n\n---\nReply to: {email or '(not given)'}\nPage: {page or '-'}\n"
    EmailMessage(subject, body, None, [settings.FEEDBACK_EMAIL], reply_to=[email] if email else None).send()


class FeedbackView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [FeedbackThrottle]

    def post(self, request: Request) -> Response:
        serializer = FeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data.get("website"):
            return Response(status=status.HTTP_202_ACCEPTED)  # a bot: look successful, send nothing
        turnstile.require(request.data.get("captcha"), FeedbackThrottle().get_ident(request))
        args = (data["message"], data.get("email", ""), data.get("page", ""), data.get("language", ""))
        transaction.on_commit(lambda: send_feedback.delay(*args))
        return Response(status=status.HTTP_202_ACCEPTED)
