import { useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router";

import { AuthCard } from "@/components/AuthCard";
import { FormAlert, PasswordField, SubmitButton, TextField, focusFirstInvalid, validateEmail } from "@/components/forms";
import { GoogleButton, googleEnabled } from "@/components/GoogleButton";
import { useLang } from "@/hooks/useLang";
import { auth } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { safeNext } from "@/lib/navigation";
import { useAuthStore } from "@/stores/auth";

export function LoginPage() {
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
    const next_errors = {
      email: emailError ? t(`errors.${emailError}`) : undefined,
      password: password ? undefined : t("errors.required"),
    };
    setErrors(next_errors);
    setFormError(null);
    if (next_errors.email || next_errors.password) {
      focusFirstInvalid(formRef.current);
      return;
    }
    setBusy(true);
    try {
      await auth.login(email.trim(), password);
      navigate(next, { replace: true });
    } catch (err) {
      setFormError(errorMessage(t, err));
      setBusy(false);
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
      title={t("auth.login.title")}
      intro={t("auth.benefits")}
      footer={
        <>
          {t("auth.login.noAccount")}{" "}
          <Link to={`/${lang}/register${params.size ? `?${params}` : ""}`} className="font-semibold text-primary underline-offset-4 hover:underline">
            {t("auth.login.toRegister")}
          </Link>
        </>
      }
    >
      <title>{`${t("auth.login.title")} | ${t("meta.siteName")}`}</title>
      <meta name="robots" content="noindex" />
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
        <PasswordField label={t("fields.password")} name="password" autoComplete="current-password" error={errors.password} />
        <div className="text-right text-sm">
          <Link to={`/${lang}/forgot`} className="inline-flex min-h-11 items-center font-semibold text-primary underline-offset-4 hover:underline">
            {t("auth.login.forgot")}
          </Link>
        </div>
        <SubmitButton busy={busy} label={t("auth.login.submit")} busyLabel={t("auth.login.submitting")} />
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
