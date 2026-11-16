import { CircleCheck } from "lucide-react";
import { useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { AuthCard } from "@/components/AuthCard";
import { FormAlert, SubmitButton, TextField, focusFirstInvalid, validateEmail } from "@/components/forms";
import { useLang } from "@/hooks/useLang";
import { auth } from "@/lib/api";
import { errorMessage } from "@/lib/errors";

export function ForgotPage() {
  const { t } = useTranslation();
  const lang = useLang();
  const formRef = useRef<HTMLFormElement>(null);
  const [error, setError] = useState<string | undefined>();
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sentTo, setSentTo] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const email = String(new FormData(e.currentTarget).get("email") ?? "").trim();
    const problem = validateEmail(email);
    setError(problem ? t(`errors.${problem}`) : undefined);
    setFormError(null);
    if (problem) {
      focusFirstInvalid(formRef.current);
      return;
    }
    setBusy(true);
    try {
      await auth.requestReset(email, lang);
      setSentTo(email);
    } catch (err) {
      setFormError(errorMessage(t, err));
    } finally {
      setBusy(false);
    }
  };

  const back = (
    <Link to={`/${lang}/login`} className="font-semibold text-primary underline-offset-4 hover:underline">
      {t("auth.forgot.back")}
    </Link>
  );

  return (
    <AuthCard title={t("auth.forgot.title")} intro={sentTo ? undefined : t("auth.forgot.text")} footer={back}>
      <title>{`${t("auth.forgot.title")} | ${t("meta.siteName")}`}</title>
      <meta name="robots" content="noindex" />
      {sentTo ? (
        <p role="status" className="flex items-start gap-2">
          <CircleCheck className="mt-0.5 size-5 shrink-0 text-success" aria-hidden="true" />
          <span className="[overflow-wrap:anywhere]">{t("auth.forgot.sent", { email: sentTo })}</span>
        </p>
      ) : (
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
            error={error}
          />
          <SubmitButton busy={busy} label={t("auth.forgot.submit")} busyLabel={t("auth.forgot.submitting")} />
        </form>
      )}
    </AuthCard>
  );
}
