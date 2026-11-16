import { useInfiniteQuery, useQueryClient } from "@tanstack/react-query";
import { BadgeCheck, CircleExclamationPoint, Download, LoaderCircle, LogOut, Trash } from "lucide-react";
import { useId, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useLocation, useNavigate } from "react-router";

import { FormAlert, PasswordField, focusFirstInvalid } from "@/components/forms";
import { GoogleButton, googleEnabled } from "@/components/GoogleButton";
import { useUsage } from "@/hooks/useApi";
import { useLang } from "@/hooks/useLang";
import { LANGUAGE_NAMES, LANGUAGES, type Language } from "@/i18n";
import { api, auth, type Me, type Task } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { formatBytes, formatDate } from "@/lib/format";
import { isToolSlug } from "@/lib/tools";
import { btn, card } from "@/lib/ui";
import { useAuthStore } from "@/stores/auth";

function Section({ title, children, id }: { title: string; children: React.ReactNode; id: string }) {
  return (
    <section aria-labelledby={id} className={`${card} space-y-4 p-5 sm:p-6`}>
      <h2 id={id} className="text-lg font-semibold">
        {title}
      </h2>
      {children}
    </section>
  );
}

function Profile({ user }: { user: Me }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const selectId = useId();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const changeLanguage = async (language: Language) => {
    setSaving(true);
    setError(null);
    try {
      await api.updateMe({ language });
      navigate(`/${language}/account`, { replace: true });
    } catch (err) {
      setError(errorMessage(t, err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Section title={t("account.profile")} id="profile-heading">
      <div className="space-y-1">
        <p className="font-semibold [overflow-wrap:anywhere]">{user.email}</p>
        <p className="flex items-center gap-1.5 text-sm text-muted">
          {user.email_verified ? (
            <BadgeCheck className="size-4 text-success" aria-hidden="true" />
          ) : (
            <CircleExclamationPoint className="size-4" aria-hidden="true" />
          )}
          {user.email_verified ? t("account.verified") : t("account.unverified")}
        </p>
      </div>
      <div className="space-y-1.5">
        <label htmlFor={selectId} className="block text-sm font-semibold">
          {t("account.language")}
        </label>
        <select
          id={selectId}
          value={user.language}
          disabled={saving}
          onChange={(e) => void changeLanguage(e.target.value as Language)}
          className="min-h-12 w-full rounded-xl border border-border-strong bg-surface px-3 text-base text-fg sm:w-64"
        >
          {LANGUAGES.map((code) => (
            <option key={code} value={code} className="bg-surface text-fg">
              {LANGUAGE_NAMES[code]}
            </option>
          ))}
        </select>
      </div>
      <FormAlert message={error} />
    </Section>
  );
}

function Usage() {
  const { t } = useTranslation();
  const usage = useUsage();
  if (!usage.data) return null;
  const { today, limits } = usage.data;
  return (
    <Section title={t("account.usage")} id="usage-heading">
      <p className="tabular-nums">
        {t("account.usageText", { used: today.tasks_used, total: limits.daily_tasks, maxFile: limits.max_file_mb })}
      </p>
      <div
        className="h-2 overflow-hidden rounded-full bg-surface-muted"
        role="progressbar"
        aria-label={t("account.usage")}
        aria-valuemin={0}
        aria-valuemax={limits.daily_tasks}
        aria-valuenow={today.tasks_used}
      >
        <div
          className="h-full w-full origin-left rounded-full bg-primary"
          style={{ transform: `scaleX(${Math.min(1, today.tasks_used / limits.daily_tasks)})` }}
        />
      </div>
    </Section>
  );
}

function HistoryItem({ task }: { task: Task }) {
  const { t, i18n } = useTranslation();
  const toolName = isToolSlug(task.tool) ? t(`tools.${task.tool}.name`) : task.tool;
  const when = formatDate(task.created_at, i18n.language, true);
  const expired = task.files_deleted || new Date(task.expires_at) <= new Date();
  const files = task.bundle ? [task.bundle] : task.outputs;

  return (
    <li className="space-y-2 py-3">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3">
        <p className="font-semibold">{toolName}</p>
        <p className="text-sm text-muted tabular-nums">{when}</p>
      </div>
      {task.status === "done" ? (
        expired ? (
          <p className="text-sm text-muted">{t("account.filesDeleted")}</p>
        ) : (
          <ul className="space-y-1">
            {files.map((file) => (
              <li key={file.id} className="flex items-center gap-2">
                <span className="min-w-0 flex-1 text-sm [overflow-wrap:anywhere]">
                  {file.name} <span className="text-muted tabular-nums">({formatBytes(file.size, i18n.language)})</span>
                </span>
                {file.download_url ? (
                  <a
                    href={file.download_url}
                    download
                    className={btn.icon}
                    aria-label={t("actions.downloadFile", { name: file.name })}
                  >
                    <Download className="size-5" aria-hidden="true" />
                  </a>
                ) : null}
              </li>
            ))}
          </ul>
        )
      ) : task.status === "failed" ? (
        <p className="flex items-center gap-1.5 text-sm text-danger">
          <CircleExclamationPoint className="size-4" aria-hidden="true" />
          {t(`errors.${task.error_code}`, { defaultValue: t("status.failed") })}
        </p>
      ) : (
        <p className="flex items-center gap-1.5 text-sm text-muted">
          <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
          {t(`status.${task.status}`)}
        </p>
      )}
    </li>
  );
}

function History() {
  const { t } = useTranslation();
  const lang = useLang();
  const userId = useAuthStore((s) => s.user?.id);
  const history = useInfiniteQuery({
    queryKey: ["history", userId],
    queryFn: ({ pageParam }) => api.history(pageParam),
    initialPageParam: 1,
    getNextPageParam: (last, pages) => (last.next ? pages.length + 1 : undefined),
  });
  const tasks = history.data?.pages.flatMap((p) => p.results) ?? [];

  return (
    <Section title={t("account.history")} id="history-heading">
      {history.isPending ? (
        <p className="flex items-center gap-2 text-muted">
          <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
          {t("status.queued")}
        </p>
      ) : history.isError ? (
        <FormAlert message={errorMessage(t, history.error)} />
      ) : tasks.length === 0 ? (
        <div className="space-y-3">
          <p className="text-muted">{t("account.empty")}</p>
          <Link to={`/${lang}`} className={btn.secondary}>
            {t("account.toTools")}
          </Link>
        </div>
      ) : (
        <>
          <ul className="divide-y divide-border">
            {tasks.map((task) => (
              <HistoryItem key={task.id} task={task} />
            ))}
          </ul>
          {history.hasNextPage ? (
            <button
              type="button"
              className={btn.secondary}
              disabled={history.isFetchingNextPage}
              onClick={() => void history.fetchNextPage()}
            >
              {t("account.more")}
            </button>
          ) : null}
        </>
      )}
    </Section>
  );
}

function DangerZone({ user }: { user: Me }) {
  const { t } = useTranslation();
  const lang = useLang();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const formRef = useRef<HTMLFormElement>(null);
  const [error, setError] = useState<string | undefined>();
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const remove = async (proof: { password: string } | { google_credential: string }) => {
    if (!window.confirm(t("account.deleteConfirm"))) return;
    setBusy(true);
    setFormError(null);
    try {
      await api.deleteAccount(proof);
      queryClient.clear();
      navigate(`/${lang}`, { replace: true });
    } catch (err) {
      setBusy(false);
      setFormError(errorMessage(t, err));
    }
  };

  const onSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const password = String(new FormData(e.currentTarget).get("password") ?? "");
    if (!password) {
      setError(t("errors.required"));
      focusFirstInvalid(formRef.current);
      return;
    }
    setError(undefined);
    void remove({ password });
  };

  return (
    <section aria-labelledby="delete-heading" className={`${card} space-y-4 border-danger/40 p-5 sm:p-6`}>
      <h2 id="delete-heading" className="text-lg font-semibold text-danger">
        {t("account.deleteTitle")}
      </h2>
      <p className="text-sm text-muted">{t("account.deleteText")}</p>
      {user.has_password ? (
        <form ref={formRef} noValidate onSubmit={onSubmit} className="space-y-4">
          <FormAlert message={formError} />
          <PasswordField label={t("account.deletePassword")} name="password" autoComplete="current-password" error={error} />
          <button type="submit" className={btn.danger} disabled={busy}>
            <Trash className="size-4" aria-hidden="true" />
            {t("account.deleteSubmit")}
          </button>
        </form>
      ) : googleEnabled ? (
        <div className="space-y-4">
          <FormAlert message={formError} />
          <p className="text-sm">{t("account.deleteGoogle")}</p>
          {busy ? (
            <p className="flex items-center gap-2 text-muted" role="status">
              <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
              {t("status.processing")}
            </p>
          ) : (
            <div className="max-w-sm">
              <GoogleButton lang={lang} onCredential={(credential) => void remove({ google_credential: credential })} />
            </div>
          )}
        </div>
      ) : (
        <p className="text-sm">
          {t("account.deleteNoGoogle")}{" "}
          <Link to={`/${lang}/forgot`} className="font-semibold text-primary underline-offset-4 hover:underline">
            {t("auth.login.forgot")}
          </Link>
        </p>
      )}
    </section>
  );
}

export function AccountPage() {
  const { t } = useTranslation();
  const lang = useLang();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const status = useAuthStore((s) => s.status);
  const user = useAuthStore((s) => s.user);

  if (status === "loading") {
    return (
      <p className="flex items-center justify-center gap-2 py-16 text-muted" role="status">
        <LoaderCircle className="size-5 animate-spin" aria-hidden="true" />
        {t("status.processing")}
      </p>
    );
  }
  if (status === "anon" || !user) {
    return <Navigate to={`/${lang}/login?next=${encodeURIComponent(location.pathname)}`} replace />;
  }

  const logout = async () => {
    await auth.logout();
    queryClient.clear();
    navigate(`/${lang}`, { replace: true });
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <title>{`${t("account.title")} | ${t("meta.siteName")}`}</title>
      <meta name="robots" content="noindex" />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{t("account.title")}</h1>
        <div className="flex flex-wrap gap-2">
          {user.is_staff ? (
            <Link to={`/${lang}/admin`} className={btn.secondary}>
              {t("account.adminLink")}
            </Link>
          ) : null}
          <button type="button" className={btn.secondary} onClick={() => void logout()}>
            <LogOut className="size-4" aria-hidden="true" />
            {t("account.logout")}
          </button>
        </div>
      </div>
      <Profile user={user} />
      <Usage />
      <History />
      <DangerZone user={user} />
    </div>
  );
}
