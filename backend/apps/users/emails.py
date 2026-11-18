"""Plain-text transactional emails in the user's language."""

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import User

RESET = {
    "uz": (
        "Universe: parolni tiklash",
        "Salom!\n\nUniverse akkauntingiz uchun parolni tiklash soʻraldi. "
        "Yangi parol oʻrnatish uchun havolani oching:\n\n"
        "{link}\n\nHavola bir marta ishlaydi va 3 kun amal qiladi. "
        "Agar bu siz boʻlmasangiz, xatni eʼtiborsiz qoldiring: "
        "parolingiz oʻzgarmaydi.\n",
    ),
    "ru": (
        "Universe: восстановление пароля",
        "Здравствуйте!\n\nДля вашего аккаунта Universe запросили сброс пароля. "
        "Чтобы задать новый пароль, откройте ссылку:\n\n"
        "{link}\n\nСсылка одноразовая и действует 3 дня. Если это были не вы, просто проигнорируйте письмо: "
        "пароль не изменится.\n",
    ),
    "en": (
        "Universe: reset your password",
        "Hi,\n\nSomeone asked to reset the password for your Universe account. "
        "Open this link to set a new password:\n\n"
        "{link}\n\nThe link works once and expires in 3 days. If this wasn't you, ignore this email and your password "
        "stays the same.\n",
    ),
}


def password_reset_message(user: User, lang: str) -> tuple[str, str]:
    lang = lang if lang in RESET else user.language
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link = f"{settings.PUBLIC_ORIGIN.rstrip('/')}/{lang}/reset/{uid}/{token}"
    subject, body = RESET[lang]
    return subject, body.format(link=link)


VERIFY = {
    "uz": (
        "Universe: emailingizni tasdiqlang",
        "Salom!\n\nUniverse akkauntingiz uchun shu emailni tasdiqlang. Havolani oching:\n\n"
        "{link}\n\nHavola 3 kun amal qiladi. Agar akkauntni siz ochmagan boʻlsangiz, xatni eʼtiborsiz qoldiring.\n",
    ),
    "ru": (
        "Universe: подтвердите email",
        "Здравствуйте!\n\nПодтвердите этот email для аккаунта Universe. Откройте ссылку:\n\n"
        "{link}\n\nСсылка действует 3 дня. Если вы не создавали аккаунт, просто проигнорируйте письмо.\n",
    ),
    "en": (
        "Universe: confirm your email",
        "Hi,\n\nPlease confirm this email address for your Universe account. Open this link:\n\n"
        "{link}\n\nThe link expires in 3 days. If you didn't create an account, ignore this email.\n",
    ),
}


def email_verification_message(user: User, lang: str) -> tuple[str, str]:
    from .verification import make_token

    lang = lang if lang in VERIFY else user.language
    link = f"{settings.PUBLIC_ORIGIN.rstrip('/')}/{lang}/verify-email/{make_token(user)}"
    subject, body = VERIFY[lang]
    return subject, body.format(link=link)
