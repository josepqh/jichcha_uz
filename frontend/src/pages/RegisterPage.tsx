import { useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router";

import { AuthCard } from "@/components/AuthCard";
import { FormAlert, PasswordField, SubmitButton, TextField, focusFirstInvalid, validateEmail } from "@/components/forms";
import { GoogleButton, googleEnabled } from "@/components/GoogleButton";
import { useLang } from "@/hooks/useLang";
import { ApiError, auth } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { safeNext } from "@/lib/navigation";
import { useAuthStore } from "@/stores/auth";

export function RegisterPage() {
  const { t } = useTranslation();
  const lang = useLang();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"), lang);
  const status = useAuthStore((s) => s.status);
  const formRef = useRef<HTMLFormElement>(null);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (status === "authed" && !busy) return <Navigate to={next} replace />;

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const email = String(data.get("email") ?? "");
    const password = String(data.get("password") ?? "");
    const emailError = validateEmail(email);
    const found = {
      email: emailError ? t(`errors.${emailError}`) : undefined,
      password: !password ? t("errors.required") : password.length < 8 ? t("errors.weak_password", { reasons: t("weak.password_too_short") }) : undefined,
    };
    setErrors(found);
    setFormError(null);
    if (found.email || found.password) {
      focusFirstInvalid(formRef.current);
      return;
    }
    setBusy(true);
    try {
      await auth.register(email.trim(), password, lang);
      navigate(next, { replace: true });
    } catch (err) {
      setBusy(false);
      // Field-specific server errors go next to the field.
      if (err instanceof ApiError && err.code === "weak_password") setErrors({ password: errorMessage(t, err) });
      else if (err instanceof ApiError && err.code === "email_taken") setErrors({ email: errorMessage(t, err) });
      else setFormError(errorMessage(t, err));
      focusFirstInvalid(formRef.current);
    }
  };

  const onGoogle = (credential: string) => {
    setFormError(null);
    auth.google(credential).then(
      () => navigate(next, { replace: true }),
      (err: unknown) => setFormError(errorMessage(t, err)),
    );
  };

  return (
    <AuthCard
      title={t("auth.register.title")}
      intro={t("auth.benefits")}
      footer={
        <>
          {t("auth.register.hasAccount")}{" "}
          <Link to={`/${lang}/login${params.size ? `?${params}` : ""}`} className="font-semibold text-primary underline-offset-4 hover:underline">
            {t("auth.register.toLogin")}
          </Link>
        </>
      }
    >
      <title>{`${t("auth.register.title")} | ${t("meta.siteName")}`}</title>
      <form ref={formRef} noValidate onSubmit={(e) => void onSubmit(e)} className="space-y-4">
        <FormAlert message={formError} />
        <TextField
          label={t("fields.email")}
          name="email"
          type="email"
          inputMode="email"
          autoComplete="email"
          spellCheck={false}
          autoCapitalize="none"
          error={errors.email}
        />
        <PasswordField
          label={t("fields.password")}
          name="password"
          autoComplete="new-password"
          hint={t("fields.passwordHint")}
          error={errors.password}
        />
        <SubmitButton busy={busy} label={t("auth.register.submit")} busyLabel={t("auth.register.submitting")} />
      </form>
      {googleEnabled ? (
        <>
          <p className="text-center text-sm text-muted">{t("auth.or")}</p>
          <GoogleButton lang={lang} onCredential={onGoogle} />
        </>
      ) : null}
    </AuthCard>
  );
}
