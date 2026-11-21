import { BadgeCheck, LoaderCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import { AuthCard } from "@/components/AuthCard";
import { FormAlert } from "@/components/forms";
import { useLang } from "@/hooks/useLang";
import { api, auth } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { btn } from "@/lib/ui";
import { useAuthStore } from "@/stores/auth";

/** Landing page of the confirmation email: confirms on open, no button to press. */
export function VerifyEmailPage() {
  const { t } = useTranslation();
  const lang = useLang();
  const { token = "" } = useParams();
  const signedIn = useAuthStore((s) => s.status === "authed");
  // The error object, not its text: the message is translated at render time.
  const [state, setState] = useState<{ done: boolean; error: unknown }>({ done: false, error: null });

  useEffect(() => {
    let cancelled = false; // StrictMode runs effects twice in development
    auth.verifyEmail(token).then(
      () => {
        if (cancelled) return;
        const { user, status, setUser } = useAuthStore.getState();
        if (user) setUser({ ...user, email_verified: true });
        // The page-load session restore may answer after this, with the profile from before the
        // confirmation: read the profile again once the session has settled.
        if (status !== "anon") void api.me().then(setUser, () => undefined);
        setState({ done: true, error: null });
      },
      (err: unknown) => {
        if (!cancelled) setState({ done: false, error: err });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <AuthCard title={t("auth.verify.title")}>
      <title>{`${t("auth.verify.title")} | ${t("meta.siteName")}`}</title>
      <meta name="robots" content="noindex" />
      {state.done ? (
        <p role="status" className="flex items-center gap-2 font-semibold">
          <BadgeCheck className="size-5 text-success" aria-hidden="true" />
          {t("auth.verify.done")}
        </p>
      ) : state.error ? (
        <FormAlert message={errorMessage(t, state.error)} />
      ) : (
        <p role="status" className="flex items-center gap-2 text-muted">
          <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
          {t("auth.verify.checking")}
        </p>
      )}
      {state.done || state.error ? (
        <Link to={signedIn ? `/${lang}/account` : `/${lang}`} className={`${btn.secondary} w-full`}>
          {signedIn ? t("auth.verify.toAccount") : t("auth.verify.toHome")}
        </Link>
      ) : null}
    </AuthCard>
  );
}
