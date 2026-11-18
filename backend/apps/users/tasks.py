from celery import shared_task
from django.core.mail import send_mail

from .emails import password_reset_message
from .models import User


@shared_task(ignore_result=True, autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def send_password_reset(user_id: str, lang: str) -> None:
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        return
    subject, body = password_reset_message(user, lang)
    send_mail(subject, body, None, [user.email])


@shared_task(ignore_result=True, autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def send_email_verification(user_id: str, lang: str) -> None:
    from .emails import email_verification_message

    user = User.objects.filter(pk=user_id, is_active=True, email_verified=False).first()
    if user is None:
        return
    subject, body = email_verification_message(user, lang)
    send_mail(subject, body, None, [user.email])
