"""Plain-text transactional emails in the user's language."""

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import User

RESET = {
    "uz": (
        "jichcha: parolni tiklash",
        "Salom!\n\njichcha akkauntingiz uchun parolni tiklash soʻraldi. "
        "Yangi parol oʻrnatish uchun havolani oching:\n\n"
        "{link}\n\nHavola bir marta ishlaydi va 3 kun amal qiladi. "
        "Agar bu siz boʻlmasangiz, xatni eʼtiborsiz qoldiring: "
        "parolingiz oʻzgarmaydi.\n",
    ),
    "ru": (
        "jichcha: восстановление пароля",
        "Здравствуйте!\n\nДля вашего аккаунта jichcha запросили сброс пароля. "
        "Чтобы задать новый пароль, откройте ссылку:\n\n"
        "{link}\n\nСсылка одноразовая и действует 3 дня. Если это были не вы, просто проигнорируйте письмо: "
        "пароль не изменится.\n",
    ),
    "en": (
        "jichcha: reset your password",
        "Hi,\n\nSomeone asked to reset the password for your jichcha account. "
        "Open this link to set a new password:\n\n"
        "{link}\n\nThe link works once and expires in 3 days. If this wasn't you, ignore this email and your password "
        "stays the same.\n",
    ),
}


RESET.update(
    {
        "zh": (
            "jichcha：重置密码",
            "你好！\n\n有人为你的 jichcha 账户申请了重置密码。打开下面的链接设置新密码：\n\n"
            "{link}\n\n链接只能使用一次，3 天内有效。如果这不是你本人的操作，请忽略此邮件，你的密码不会改变。\n",
        ),
        "es": (
            "jichcha: restablece tu contraseña",
            "Hola:\n\nAlguien pidió restablecer la contraseña de tu cuenta de jichcha. "
            "Abre este enlace para crear una nueva:\n\n"
            "{link}\n\nEl enlace funciona una sola vez y caduca en 3 días. Si no fuiste tú, ignora este correo "
            "y tu contraseña seguirá igual.\n",
        ),
        "hi": (
            "jichcha: अपना पासवर्ड रीसेट करें",
            "नमस्ते,\n\nकिसी ने आपके jichcha खाते का पासवर्ड रीसेट करने का अनुरोध किया है। "
            "नया पासवर्ड बनाने के लिए यह लिंक खोलें:\n\n"
            "{link}\n\nलिंक एक बार चलता है और 3 दिन में खत्म हो जाता है। अगर यह आप नहीं थे, तो इस ईमेल को "
            "अनदेखा करें, आपका पासवर्ड नहीं बदलेगा।\n",
        ),
        "ar": (
            "jichcha: إعادة تعيين كلمة المرور",
            "مرحبًا،\n\nطلب أحدهم إعادة تعيين كلمة مرور حسابك في jichcha. افتح هذا الرابط لتعيين كلمة مرور جديدة:\n\n"
            "{link}\n\nيعمل الرابط مرة واحدة وتنتهي صلاحيته بعد 3 أيام. إذا لم تكن أنت من طلب ذلك، فتجاهل هذه "
            "الرسالة ولن تتغير كلمة مرورك.\n",
        ),
        "fr": (
            "jichcha : réinitialisez votre mot de passe",
            "Bonjour,\n\nQuelqu'un a demandé à réinitialiser le mot de passe de votre compte jichcha. "
            "Ouvrez ce lien pour en choisir un nouveau :\n\n"
            "{link}\n\nLe lien ne fonctionne qu'une fois et expire dans 3 jours. Si ce n'était pas vous, ignorez "
            "cet e-mail : votre mot de passe ne changera pas.\n",
        ),
        "pt": (
            "jichcha: redefina sua senha",
            "Olá,\n\nAlguém pediu para redefinir a senha da sua conta jichcha. Abra este link para criar uma nova:\n\n"
            "{link}\n\nO link funciona uma vez e expira em 3 dias. Se não foi você, ignore este e-mail e sua senha "
            "continua a mesma.\n",
        ),
        "de": (
            "jichcha: Passwort zurücksetzen",
            "Hallo,\n\njemand möchte das Passwort Ihres jichcha-Kontos zurücksetzen. "
            "Öffnen Sie diesen Link, um ein neues festzulegen:\n\n"
            "{link}\n\nDer Link funktioniert einmal und läuft nach 3 Tagen ab. Wenn Sie das nicht waren, ignorieren "
            "Sie diese E-Mail – Ihr Passwort bleibt unverändert.\n",
        ),
        "ja": (
            "jichcha：パスワードの再設定",
            "こんにちは。\n\njichcha アカウントのパスワード再設定が申請されました。"
            "次のリンクを開いて新しいパスワードを設定してください：\n\n"
            "{link}\n\nリンクは 1 回だけ使え、3 日で期限が切れます。心当たりがない場合はこのメールを無視してください。"
            "パスワードは変わりません。\n",
        ),
        "tr": (
            "jichcha: şifrenizi sıfırlayın",
            "Merhaba,\n\njichcha hesabınızın şifresini sıfırlama isteği geldi. Yeni şifre belirlemek için bu "
            "bağlantıyı açın:\n\n"
            "{link}\n\nBağlantı bir kez çalışır ve 3 gün içinde geçersiz olur. Bu siz değilseniz bu e-postayı "
            "görmezden gelin; şifreniz değişmez.\n",
        ),
        "ko": (
            "jichcha: 비밀번호 재설정",
            "안녕하세요.\n\njichcha 계정의 비밀번호 재설정 요청이 있었습니다. "
            "아래 링크를 열어 새 비밀번호를 설정하세요:\n\n"
            "{link}\n\n링크는 한 번만 쓸 수 있고 3일 뒤에 만료됩니다. 본인이 요청하지 않았다면 이 메일을 무시하세요. "
            "비밀번호는 바뀌지 않습니다.\n",
        ),
    }
)


def password_reset_message(user: User, lang: str) -> tuple[str, str]:
    lang = next(code for code in (lang, user.language, "en") if code in RESET)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link = f"{settings.PUBLIC_ORIGIN.rstrip('/')}/{lang}/reset/{uid}/{token}"
    subject, body = RESET[lang]
    return subject, body.format(link=link)


VERIFY = {
    "uz": (
        "jichcha: emailingizni tasdiqlang",
        "Salom!\n\njichcha akkauntingiz uchun shu emailni tasdiqlang. Havolani oching:\n\n"
        "{link}\n\nHavola 3 kun amal qiladi. Agar akkauntni siz ochmagan boʻlsangiz, xatni eʼtiborsiz qoldiring.\n",
    ),
    "ru": (
        "jichcha: подтвердите email",
        "Здравствуйте!\n\nПодтвердите этот email для аккаунта jichcha. Откройте ссылку:\n\n"
        "{link}\n\nСсылка действует 3 дня. Если вы не создавали аккаунт, просто проигнорируйте письмо.\n",
    ),
    "en": (
        "jichcha: confirm your email",
        "Hi,\n\nPlease confirm this email address for your jichcha account. Open this link:\n\n"
        "{link}\n\nThe link expires in 3 days. If you didn't create an account, ignore this email.\n",
    ),
}


VERIFY.update(
    {
        "zh": (
            "jichcha：验证你的邮箱",
            "你好！\n\n请为你的 jichcha 账户验证这个邮箱。打开链接：\n\n"
            "{link}\n\n链接 3 天内有效。如果你没有创建账户，请忽略此邮件。\n",
        ),
        "es": (
            "jichcha: confirma tu correo",
            "Hola:\n\nConfirma esta dirección de correo para tu cuenta de jichcha. Abre este enlace:\n\n"
            "{link}\n\nEl enlace caduca en 3 días. Si no creaste una cuenta, ignora este correo.\n",
        ),
        "hi": (
            "jichcha: अपना ईमेल कन्फ़र्म करें",
            "नमस्ते,\n\nकृपया अपने jichcha खाते के लिए यह ईमेल पता कन्फ़र्म करें। यह लिंक खोलें:\n\n"
            "{link}\n\nलिंक 3 दिन में खत्म हो जाता है। अगर आपने खाता नहीं बनाया, तो इस ईमेल को अनदेखा करें।\n",
        ),
        "ar": (
            "jichcha: أكّد بريدك الإلكتروني",
            "مرحبًا،\n\nيرجى تأكيد عنوان البريد هذا لحسابك في jichcha. افتح هذا الرابط:\n\n"
            "{link}\n\nتنتهي صلاحية الرابط بعد 3 أيام. إذا لم تنشئ حسابًا، فتجاهل هذه الرسالة.\n",
        ),
        "fr": (
            "jichcha : confirmez votre e-mail",
            "Bonjour,\n\nMerci de confirmer cette adresse e-mail pour votre compte jichcha. Ouvrez ce lien :\n\n"
            "{link}\n\nLe lien expire dans 3 jours. Si vous n'avez pas créé de compte, ignorez cet e-mail.\n",
        ),
        "pt": (
            "jichcha: confirme seu e-mail",
            "Olá,\n\nConfirme este endereço de e-mail para sua conta jichcha. Abra este link:\n\n"
            "{link}\n\nO link expira em 3 dias. Se você não criou uma conta, ignore este e-mail.\n",
        ),
        "de": (
            "jichcha: E-Mail bestätigen",
            "Hallo,\n\nbitte bestätigen Sie diese E-Mail-Adresse für Ihr jichcha-Konto. Öffnen Sie diesen Link:\n\n"
            "{link}\n\nDer Link läuft nach 3 Tagen ab. "
            "Wenn Sie kein Konto erstellt haben, ignorieren Sie diese E-Mail.\n",
        ),
        "ja": (
            "jichcha：メールアドレスの確認",
            "こんにちは。\n\njichcha アカウントのために、このメールアドレスを確認してください。"
            "次のリンクを開いてください：\n\n"
            "{link}\n\nリンクは 3 日で期限が切れます。"
            "アカウントを作成していない場合は、このメールを無視してください。\n",
        ),
        "tr": (
            "jichcha: e-postanızı onaylayın",
            "Merhaba,\n\nLütfen jichcha hesabınız için bu e-posta adresini onaylayın. Bu bağlantıyı açın:\n\n"
            "{link}\n\nBağlantı 3 gün içinde geçersiz olur. Hesap oluşturmadıysanız bu e-postayı görmezden gelin.\n",
        ),
        "ko": (
            "jichcha: 이메일 인증",
            "안녕하세요.\n\njichcha 계정을 위해 이 이메일 주소를 인증해 주세요. 아래 링크를 여세요:\n\n"
            "{link}\n\n링크는 3일 뒤에 만료됩니다. 계정을 만들지 않았다면 이 메일을 무시하세요.\n",
        ),
    }
)


def email_verification_message(user: User, lang: str) -> tuple[str, str]:
    from .verification import make_token

    lang = next(code for code in (lang, user.language, "en") if code in VERIFY)
    link = f"{settings.PUBLIC_ORIGIN.rstrip('/')}/{lang}/verify-email/{make_token(user)}"
    subject, body = VERIFY[lang]
    return subject, body.format(link=link)
