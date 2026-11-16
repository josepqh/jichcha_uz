import { useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";

import { AuthCard } from "@/components/AuthCard";
import { FormAlert, PasswordField, SubmitButton, focusFirstInvalid } from "@/components/forms";
import { useLang } from "@/hooks/useLang";
import { ApiError, auth } from "@/lib/api";
import { errorMessage } from "@/lib/errors";

export function ResetPage() {
  const { t } = useTranslation();
  const lang = useLang();
  const navigate = useNavigate();
  const { uid = "", token = "" } = useParams();
  const formRef = useRef<HTMLFormElement>(null);
  const [error, setError] = useState<string | undefined>();
  const [formError, setFormError] = useState<string | null>(null);
  const [linkInvalid, setLinkInvalid] = useState(false);
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const password = String(new FormData(e.currentTarget).get("password") ?? "");
    const problem = !password ? t("errors.required") : password.length < 8 ? t("errors.weak_password", { reasons: t("weak.password_too_short") }) : undefined;
    setError(problem);
    setFormError(null);
    if (problem) {
      focusFirstInvalid(formRef.current);
      return;
    }
    setBusy(true);
    try {
      await auth.confirmReset(uid, token, password);
      navigate(`/${lang}/account`, { replace: true });
    } catch (err) {
      setBusy(false);
      if (err instanceof ApiError && err.code === "weak_password") {
        setError(errorMessage(t, err));
        focusFirstInvalid(formRef.current);
      } else {
        setLinkInvalid(err instanceof ApiError && err.code === "invalid_reset_link");
        setFormError(errorMessage(t, err));
      }
    }
  };

  return (
    <AuthCard
      title={t("auth.reset.title")}
      footer={
        linkInvalid ? (
          <Link to={`/${lang}/forgot`} className="font-semibold text-primary underline-offset-4 hover:underline">
            {t("auth.reset.requestNew")}
          </Link>
        ) : null
      }
    >
      <title>{`${t("auth.reset.title")} | ${t("meta.siteName")}`}</title>
      <meta name="robots" content="noindex" />
      <form ref={formRef} noValidate onSubmit={(e) => void onSubmit(e)} className="space-y-4">
        <FormAlert message={formError} />
        <PasswordField
          label={t("fields.newPassword")}
          name="password"
          autoComplete="new-password"
          hint={t("fields.passwordHint")}
          error={error}
        />
        <SubmitButton busy={busy} label={t("auth.reset.submit")} busyLabel={t("auth.reset.submitting")} />
      </form>
    </AuthCard>
  );
}
