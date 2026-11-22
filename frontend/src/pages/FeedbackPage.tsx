import { CheckCircle, Mail, Send } from "lucide-react";
import { useId, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { FormAlert, SubmitButton, TextField, focusFirstInvalid, validateEmail } from "@/components/forms";
import { Turnstile } from "@/components/Turnstile";
import { useLang } from "@/hooks/useLang";
import { ApiError, api } from "@/lib/api";
import { CONTACT_EMAIL, TELEGRAM_URL, TELEGRAM_USERNAME } from "@/lib/contacts";
import { errorMessage } from "@/lib/errors";
import { btn, card } from "@/lib/ui";
import { useAuthStore } from "@/stores/auth";

const MIN_LENGTH = 10;

/** Suggestions and complaints, emailed to the team; the direct contacts sit beside the form. */
export function FeedbackPage() {
  const { t } = useTranslation();
  const lang = useLang();
  const userEmail = useAuthStore((s) => s.user?.email ?? "");
  const formRef = useRef<HTMLFormElement>(null);
  const messageId = useId();
  const [errors, setErrors] = useState<{ message?: string; email?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [captcha, setCaptcha] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const message = String(data.get("message") ?? "").trim();
    const email = String(data.get("email") ?? "").trim();
    const problems = {
      message: !message ? t("errors.required") : message.length < MIN_LENGTH ? t("feedback.tooShort", { count: MIN_LENGTH }) : undefined,
      email: email && validateEmail(email) ? t("errors.invalid_email") : undefined,
    };
    setErrors(problems);
    setFormError(null);
    if (problems.message || problems.email) {
      focusFirstInvalid(formRef.current);
      return;
    }
    setBusy(true);
    try {
      await api.sendFeedback({
        message,
        email,
        page: document.referrer.startsWith(window.location.origin) ? document.referrer : "",
        language: lang,
        website: String(data.get("website") ?? ""),
        captcha,
      });
      setSent(true);
    } catch (err) {
      setFormError(err instanceof ApiError && err.code === "throttled" ? t("feedback.throttled") : errorMessage(t, err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto grid max-w-5xl gap-10 lg:grid-cols-[1.3fr_1fr]">
      <title>{`${t("feedback.title")} | ${t("meta.siteName")}`}</title>
      <meta name="description" content={t("feedback.intro")} />
      <div className="space-y-6">
        <header className="space-y-3">
          <h1 className="font-display text-3xl leading-[1.1] font-medium tracking-[-0.045em] sm:text-4xl">{t("feedback.title")}</h1>
          <p className="text-lg text-pretty text-muted">{t("feedback.intro")}</p>
        </header>

        {sent ? (
          <div role="status" className={`${card} space-y-4 p-6`}>
            <p className="flex items-center gap-2 text-lg font-semibold">
              <CheckCircle className="size-6 text-success" aria-hidden="true" />
              {t("feedback.sent")}
            </p>
            <p className="text-muted">{t("feedback.sentText")}</p>
            <button type="button" className={btn.secondary} onClick={() => setSent(false)}>
              {t("feedback.another")}
            </button>
          </div>
        ) : (
          <form ref={formRef} noValidate onSubmit={(e) => void onSubmit(e)} className={`${card} space-y-5 p-5 sm:p-6`}>
            <FormAlert message={formError} />
            <div className="space-y-1.5">
              <label htmlFor={messageId} className="block text-sm font-semibold">
                {t("feedback.message")}
              </label>
              <textarea
                id={messageId}
                name="message"
                rows={6}
                maxLength={4000}
                aria-invalid={errors.message ? true : undefined}
                aria-describedby={errors.message ? `${messageId}-error` : undefined}
                placeholder={t("feedback.placeholder")}
                className={`w-full rounded-xl border bg-surface px-4 py-3 text-base placeholder:text-muted ${errors.message ? "border-danger" : "border-border-strong"}`}
              />
              {errors.message ? (
                <p id={`${messageId}-error`} className="text-sm text-danger">
                  {errors.message}
                </p>
              ) : null}
            </div>

            <TextField
              label={t("feedback.email")}
              hint={t("feedback.emailHint")}
              name="email"
              type="email"
              inputMode="email"
              autoComplete="email"
              defaultValue={userEmail}
              error={errors.email}
            />
            {/* Honeypot: hidden from people and screen readers; bots fill it in. */}
            <input type="text" name="website" tabIndex={-1} autoComplete="off" aria-hidden="true" className="hidden" />
            <Turnstile lang={lang} onToken={setCaptcha} />
            <SubmitButton busy={busy} label={t("feedback.submit")} busyLabel={t("feedback.submitting")} />
          </form>
        )}
      </div>

      <aside aria-labelledby="contacts-heading" className="space-y-4 lg:pt-24">
        <h2 id="contacts-heading" className="font-display text-xl font-medium tracking-[-0.03em]">
          {t("feedback.direct")}
        </h2>
        <a href={TELEGRAM_URL} rel="noopener" className={`${card} group flex items-center gap-4 p-4 transition-colors duration-150 hover:border-border-strong`}>
          <span className="grid size-11 place-items-center rounded-xl bg-surface-muted" aria-hidden="true">
            <Send className="size-5" />
          </span>
          <span>
            <span className="block text-sm text-muted">Telegram</span>
            <span className="block font-semibold">@{TELEGRAM_USERNAME}</span>
          </span>
        </a>
        <a href={`mailto:${CONTACT_EMAIL}`} className={`${card} group flex items-center gap-4 p-4 transition-colors duration-150 hover:border-border-strong`}>
          <span className="grid size-11 place-items-center rounded-xl bg-surface-muted" aria-hidden="true">
            <Mail className="size-5" />
          </span>
          <span className="min-w-0">
            <span className="block text-sm text-muted">{t("fields.email")}</span>
            <span className="block font-semibold [overflow-wrap:anywhere]">{CONTACT_EMAIL}</span>
          </span>
        </a>
      </aside>
    </div>
  );
}
