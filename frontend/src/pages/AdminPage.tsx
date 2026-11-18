import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleCheck, CircleExclamationPoint, LoaderCircle } from "lucide-react";
import { useId, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useLocation, useParams } from "react-router";

import { FormAlert } from "@/components/forms";
import { useLang } from "@/hooks/useLang";
import { adminApi, ApiError, type DashboardStats, type LimitPolicy } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { formatBytes, formatDate } from "@/lib/format";
import { isToolSlug } from "@/lib/tools";
import { btn, card } from "@/lib/ui";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { useAuthStore } from "@/stores/auth";

const TABS = ["dashboard", "users", "failures", "load", "limits", "tools"] as const;
type Tab = (typeof TABS)[number];

function useNumber() {
  const { i18n } = useTranslation();
  return (value: number, options?: Intl.NumberFormatOptions) => new Intl.NumberFormat(i18n.language, options).format(value);
}

function toolName(t: (key: string) => string, slug: string) {
  return isToolSlug(slug) ? t(`tools.${slug}.name`) : slug;
}

/** Panel errors; staff without two-step sign-in get a way to turn it on instead of a dead end. */
function AdminError({ error }: { error: unknown }) {
  const { t } = useTranslation();
  const lang = useLang();
  if (error instanceof ApiError && error.code === "staff_2fa_required") {
    return (
      <div role="alert" className={`${card} space-y-3 p-5`}>
        <p>{t("admin.need2fa")}</p>
        <Link to={`/${lang}/account#security`} className={btn.primary}>
          {t("admin.to2fa")}
        </Link>
      </div>
    );
  }
  return <FormAlert message={errorMessage(t, error)} />;
}

function Loading() {
  const { t } = useTranslation();
  return (
    <p className="flex items-center gap-2 text-muted" role="status">
      <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
      {t("status.processing")}
    </p>
  );
}

function Pager({ page, count, hasNext, onPage }: { page: number; count: number; hasNext: boolean; onPage: (p: number) => void }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-wrap items-center gap-2 pt-2">
      <button type="button" className={btn.secondary} disabled={page <= 1} onClick={() => onPage(page - 1)}>
        {t("admin.pager.prev")}
      </button>
      <button type="button" className={btn.secondary} disabled={!hasNext} onClick={() => onPage(page + 1)}>
        {t("admin.pager.next")}
      </button>
      <span className="text-sm text-muted tabular-nums">{t("admin.pager.page", { page, count })}</span>
    </div>
  );
}

// --- Dashboard ------------------------------------------------------------------------------------

function Tile({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className={`${card} space-y-1 p-4`}>
      <p className="text-sm text-muted">{label}</p>
      <p className="text-2xl font-bold tabular-nums">{value}</p>
      {note ? <p className="text-sm text-muted tabular-nums">{note}</p> : null}
    </div>
  );
}

function DayChart({ data }: { data: DashboardStats }) {
  const { t, i18n } = useTranslation();
  const n = useNumber();
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(1, ...data.per_day.map((d) => d.tasks));
  const label = (d: DashboardStats["per_day"][number]) =>
    t("admin.dashboard.barLabel", { date: formatDate(`${d.date}T12:00:00`, i18n.language), tasks: d.tasks, failed: d.failed });
  const shown = hover === null ? null : data.per_day[hover];

  return (
    <section className={`${card} space-y-3 p-5`} aria-labelledby="chart-title">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="chart-title" className="font-semibold">
          {t("admin.dashboard.chartTitle")}
        </h2>
        <ul className="flex gap-4 text-sm text-muted" aria-label={t("admin.dashboard.chartTitle")}>
          <li className="flex items-center gap-1.5">
            <span className="size-3 rounded-sm bg-chart-ok" aria-hidden="true" />
            {t("admin.dashboard.ok")}
          </li>
          <li className="flex items-center gap-1.5">
            <span className="size-3 rounded-sm bg-chart-failed" aria-hidden="true" />
            {t("admin.dashboard.failed")}
          </li>
        </ul>
      </div>
      {data.per_day.every((d) => d.tasks === 0) ? (
        <p className="text-muted">{t("admin.dashboard.empty")}</p>
      ) : (
        <>
          <p className="min-h-6 text-sm tabular-nums" aria-live="polite">
            {shown ? label(shown) : ""}
          </p>
          <div className="flex h-48 items-end gap-0.5 border-b border-border" onMouseLeave={() => setHover(null)}>
            {data.per_day.map((d, i) => (
              // Each day is focusable, so the tooltip line also works from the keyboard.
              // oxlint-disable-next-line jsx-a11y/no-noninteractive-element-interactions
              <div
                key={d.date}
                // oxlint-disable-next-line jsx-a11y/no-noninteractive-tabindex
                tabIndex={0}
                role="img"
                aria-label={label(d)}
                onMouseEnter={() => setHover(i)}
                onFocus={() => setHover(i)}
                onBlur={() => setHover(null)}
                className="flex h-full min-w-0 flex-1 cursor-default flex-col justify-end rounded-t outline-offset-2 hover:bg-surface-muted"
              >
                {d.tasks - d.failed > 0 ? (
                  <div className="rounded-t bg-chart-ok" style={{ height: `${((d.tasks - d.failed) / max) * 100}%` }} />
                ) : null}
                {d.failed > 0 ? (
                  <div
                    className={`bg-chart-failed ${d.tasks - d.failed > 0 ? "mt-0.5" : "rounded-t"}`}
                    style={{ height: `${(d.failed / max) * 100}%` }}
                  />
                ) : null}
              </div>
            ))}
          </div>
          <div className="flex justify-between text-xs text-muted tabular-nums" aria-hidden="true">
            <span>{formatDate(`${data.per_day[0]!.date}T12:00:00`, i18n.language)}</span>
            <span>{formatDate(`${data.per_day.at(-1)!.date}T12:00:00`, i18n.language)}</span>
          </div>
          <details>
            <summary className="cursor-pointer text-sm font-semibold">{t("admin.dashboard.tableView")}</summary>
            <table className="mt-2 w-full text-sm tabular-nums">
              <thead className="text-left text-muted">
                <tr>
                  <th className="py-1 font-normal">{t("admin.dashboard.date")}</th>
                  <th className="py-1 font-normal">{t("admin.dashboard.tasks")}</th>
                  <th className="py-1 font-normal">{t("admin.dashboard.failed")}</th>
                  <th className="py-1 font-normal">{t("admin.dashboard.active")}</th>
                </tr>
              </thead>
              <tbody>
                {data.per_day.map((d) => (
                  <tr key={d.date} className="border-t border-border">
                    <td className="py-1">{formatDate(`${d.date}T12:00:00`, i18n.language)}</td>
                    <td className="py-1">{n(d.tasks)}</td>
                    <td className="py-1">{n(d.failed)}</td>
                    <td className="py-1">{n(d.active)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </>
      )}
    </section>
  );
}

function Dashboard() {
  const { t } = useTranslation();
  const n = useNumber();
  const [days, setDays] = useState<7 | 30>(7);
  const query = useQuery({ queryKey: ["admin", "dashboard", days], queryFn: () => adminApi.dashboard(days) });

  return (
    <div className="space-y-5">
      <div role="group" aria-label={t("admin.dashboard.period")} className="flex gap-2">
        {([7, 30] as const).map((d) => (
          <button
            key={d}
            type="button"
            aria-pressed={days === d}
            className={days === d ? btn.primary : btn.secondary}
            onClick={() => setDays(d)}
          >
            {t(`admin.dashboard.period${d}`)}
          </button>
        ))}
      </div>
      {query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <AdminError error={query.error} />
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <Tile
              label={t("admin.dashboard.tasks")}
              value={n(query.data.totals.tasks)}
              note={t("admin.dashboard.sourceSplit", {
                web: n(query.data.totals.web_tasks),
                tg: n(query.data.totals.telegram_tasks),
              })}
            />
            <Tile
              label={t("admin.dashboard.errorRate")}
              value={n(query.data.totals.error_rate, { style: "percent", maximumFractionDigits: 1 })}
              note={t("admin.dashboard.failedOf", { failed: n(query.data.totals.failed) })}
            />
            <Tile label={t("admin.dashboard.active")} value={n(query.data.totals.active)} />
            <Tile label={t("admin.dashboard.telegram")} value={n(query.data.totals.telegram_users)} />
            <Tile
              label={t("admin.dashboard.newUsers")}
              value={n(query.data.totals.new_users)}
              note={t("admin.dashboard.newUsersOf", { total: n(query.data.totals.registered_users) })}
            />
          </div>
          <DayChart data={query.data} />
          <section className={`${card} space-y-3 p-5`} aria-labelledby="top-tools">
            <h2 id="top-tools" className="font-semibold">
              {t("admin.dashboard.topTools")}
            </h2>
            {query.data.top_tools.length === 0 ? (
              <p className="text-muted">{t("admin.dashboard.empty")}</p>
            ) : (
              <table className="w-full text-sm tabular-nums">
                <thead className="text-left text-muted">
                  <tr>
                    <th className="py-1 font-normal">{t("admin.dashboard.tool")}</th>
                    <th className="py-1 text-right font-normal">{t("admin.dashboard.count")}</th>
                    <th className="py-1 text-right font-normal">{t("admin.dashboard.failed")}</th>
                  </tr>
                </thead>
                <tbody>
                  {query.data.top_tools.map((row) => (
                    <tr key={row.tool} className="border-t border-border">
                      <td className="py-1.5">{toolName(t, row.tool)}</td>
                      <td className="py-1.5 text-right">{n(row.count)}</td>
                      <td className="py-1.5 text-right">{n(row.failed)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}
    </div>
  );
}

// --- Users ----------------------------------------------------------------------------------------

function Users() {
  const { t, i18n } = useTranslation();
  const client = useQueryClient();
  const searchId = useId();
  const [q, setQ] = useState("");
  const [blocked, setBlocked] = useState(false);
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: ["admin", "users", q, blocked, page],
    queryFn: () => adminApi.users({ q, blocked, page }),
    placeholderData: keepPreviousData,
  });
  const toggle = useMutation({
    mutationFn: ({ id, block }: { id: string; block: boolean }) => (block ? adminApi.block(id) : adminApi.unblock(id)),
    onSuccess: () => client.invalidateQueries({ queryKey: ["admin", "users"] }),
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-4">
        <div className="space-y-1.5">
          <label htmlFor={searchId} className="block text-sm font-semibold">
            {t("admin.users.search")}
          </label>
          <input
            id={searchId}
            type="search"
            value={q}
            spellCheck={false}
            autoComplete="off"
            onChange={(e) => {
              setQ(e.target.value);
              setPage(1);
            }}
            className="min-h-11 w-72 max-w-full rounded-xl border border-border-strong bg-surface px-3 text-base"
          />
        </div>
        <label className="flex min-h-11 items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={blocked}
            onChange={(e) => {
              setBlocked(e.target.checked);
              setPage(1);
            }}
            className="size-5 accent-primary"
          />
          {t("admin.users.blockedOnly")}
        </label>
      </div>
      <FormAlert message={toggle.isError ? errorMessage(t, toggle.error) : null} />
      {query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <AdminError error={query.error} />
      ) : query.data.results.length === 0 ? (
        <p className="text-muted">{t("admin.users.none")}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead className="text-left text-muted">
              <tr>
                <th className="py-2 font-normal">{t("admin.users.email")}</th>
                <th className="py-2 font-normal">{t("admin.users.joined")}</th>
                <th className="py-2 font-normal">{t("admin.users.lastLogin")}</th>
                <th className="py-2 text-right font-normal">{t("admin.users.tasks30")}</th>
                <th className="py-2 font-normal">{t("admin.users.status")}</th>
                <th className="py-2">
                  <span className="sr-only">{t("admin.users.actions")}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {query.data.results.map((u) => (
                <tr key={u.id} className="border-t border-border">
                  <td className="py-2 [overflow-wrap:anywhere]">{u.email}</td>
                  <td className="py-2 tabular-nums">{formatDate(u.date_joined, i18n.language)}</td>
                  <td className="py-2 tabular-nums">
                    {u.last_login ? formatDate(u.last_login, i18n.language) : t("admin.users.never")}
                  </td>
                  <td className="py-2 text-right tabular-nums">{u.tasks_30d}</td>
                  <td className="py-2">
                    {u.is_staff ? t("admin.users.staff") : u.is_active ? t("admin.users.active") : t("admin.users.blocked")}
                  </td>
                  <td className="py-2 text-right">
                    {u.is_staff ? null : (
                      <button
                        type="button"
                        className={u.is_active ? btn.danger : btn.secondary}
                        disabled={toggle.isPending}
                        onClick={() => {
                          if (u.is_active && !window.confirm(t("admin.users.blockConfirm", { email: u.email }))) return;
                          toggle.mutate({ id: u.id, block: u.is_active });
                        }}
                      >
                        {u.is_active ? t("admin.users.block") : t("admin.users.unblock")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pager page={page} count={query.data.count} hasNext={Boolean(query.data.next)} onPage={setPage} />
        </div>
      )}
    </div>
  );
}

// --- Failures -------------------------------------------------------------------------------------

function Failures() {
  const { t, i18n } = useTranslation();
  const n = useNumber();
  const [filter, setFilter] = useState({ tool: "", code: "" });
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: ["admin", "failures", filter, page],
    queryFn: () => adminApi.failures({ ...filter, page }),
    placeholderData: keepPreviousData,
  });
  const codeLabel = (code: string) => t(`errors.${code}`, { defaultValue: code });

  if (query.isPending) return <Loading />;
  if (query.isError) return <AdminError error={query.error} />;
  const data = query.data;

  return (
    <div className="space-y-5">
      <section className="space-y-2" aria-labelledby="fail-summary">
        <h2 id="fail-summary" className="font-semibold">
          {t("admin.failures.summary")}
        </h2>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            aria-pressed={!filter.tool && !filter.code}
            className={!filter.tool && !filter.code ? btn.primary : btn.secondary}
            onClick={() => {
              setFilter({ tool: "", code: "" });
              setPage(1);
            }}
          >
            {t("admin.failures.all")}
          </button>
          {data.summary.map((s) => {
            const active = filter.tool === s.tool && filter.code === s.error_code;
            return (
              <button
                key={`${s.tool}:${s.error_code}`}
                type="button"
                aria-pressed={active}
                className={active ? btn.primary : btn.secondary}
                onClick={() => {
                  setFilter({ tool: s.tool, code: s.error_code });
                  setPage(1);
                }}
              >
                {toolName(t, s.tool)} · <code className="font-mono">{s.error_code}</code> · {n(s.count)}
              </button>
            );
          })}
        </div>
      </section>
      {data.results.length === 0 ? (
        <p className="text-muted">{t("admin.failures.none")}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="text-left text-muted">
              <tr>
                <th className="py-2 font-normal">{t("admin.failures.when")}</th>
                <th className="py-2 font-normal">{t("admin.failures.tool")}</th>
                <th className="py-2 font-normal">{t("admin.failures.source")}</th>
                <th className="py-2 font-normal">{t("admin.failures.code")}</th>
                <th className="py-2 font-normal">{t("admin.failures.inputs")}</th>
                <th className="py-2 text-right font-normal">{t("admin.failures.duration")}</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((task) => (
                <tr key={task.id} className="border-t border-border align-top">
                  <td className="py-2 tabular-nums">{formatDate(task.created_at, i18n.language, true)}</td>
                  <td className="py-2">{toolName(t, task.tool)}</td>
                  <td className="py-2">{t(`admin.failures.${task.source}`)}</td>
                  <td className="py-2">
                    <code className="font-mono">{task.error_code}</code>
                    <span className="block text-muted">{codeLabel(task.error_code)}</span>
                  </td>
                  <td className="py-2 tabular-nums">
                    {task.input_meta.map((f, i) => (
                      <span key={i} className="block">
                        {f.format.toUpperCase()} · {formatBytes(f.size, i18n.language)}
                      </span>
                    ))}
                  </td>
                  <td className="py-2 text-right tabular-nums">
                    {task.duration_ms === null ? "—" : `${n(task.duration_ms / 1000, { maximumFractionDigits: 1 })} s`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pager page={page} count={data.count} hasNext={Boolean(data.next)} onPage={setPage} />
        </div>
      )}
    </div>
  );
}

// --- Load -----------------------------------------------------------------------------------------

function Load() {
  const { t, i18n } = useTranslation();
  const n = useNumber();
  const query = useQuery({ queryKey: ["admin", "load"], queryFn: adminApi.load, refetchInterval: 10_000 });
  if (query.isPending) return <Loading />;
  if (query.isError) return <AdminError error={query.error} />;
  const { queues, workers, tasks, storage } = query.data;
  const used = storage.disk_total && storage.disk_free !== null ? 1 - storage.disk_free / storage.disk_total : null;

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <section className={`${card} space-y-3 p-5`} aria-labelledby="queues-h">
        <h2 id="queues-h" className="font-semibold">
          {t("admin.load.queues")}
        </h2>
        <table className="w-full text-sm tabular-nums">
          <thead className="text-left text-muted">
            <tr>
              <th className="py-1 font-normal">{t("admin.load.queue")}</th>
              <th className="py-1 text-right font-normal">{t("admin.load.waiting")}</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(queues).map(([name, length]) => (
              <tr key={name} className="border-t border-border">
                <td className="py-1.5 font-mono">{name}</td>
                <td className="py-1.5 text-right">{length === null ? t("admin.load.unknown") : n(length)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="text-sm text-muted">
          {t("admin.load.tasksNow")}: {t("admin.load.queued")} {n(tasks.queued)} · {t("admin.load.processing")}{" "}
          {n(tasks.processing)}
        </p>
      </section>
      <section className={`${card} space-y-3 p-5`} aria-labelledby="workers-h">
        <h2 id="workers-h" className="font-semibold">
          {t("admin.load.workers")}
        </h2>
        {workers.length === 0 ? (
          <p className="flex items-center gap-2 text-danger">
            <CircleExclamationPoint className="size-4" aria-hidden="true" />
            {t("admin.load.noWorkers")}
          </p>
        ) : (
          <ul className="space-y-1.5 text-sm">
            {workers.map((w) => (
              <li key={w.name} className="flex items-center gap-2">
                {w.ok ? (
                  <CircleCheck className="size-4 text-success" aria-hidden="true" />
                ) : (
                  <CircleExclamationPoint className="size-4 text-danger" aria-hidden="true" />
                )}
                <span className="font-mono [overflow-wrap:anywhere]">{w.name}</span>
                <span className="text-muted">{w.ok ? t("admin.load.workerOk") : t("admin.load.workerBad")}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section className={`${card} space-y-3 p-5 md:col-span-2`} aria-labelledby="storage-h">
        <h2 id="storage-h" className="font-semibold">
          {t("admin.load.storage")}
        </h2>
        <p className="text-sm tabular-nums">
          {t("admin.load.files")}: {formatBytes(storage.files_bytes, i18n.language)}
        </p>
        {used !== null && storage.disk_total && storage.disk_free !== null ? (
          <>
            <div
              className="h-2 overflow-hidden rounded-full bg-surface-muted"
              role="progressbar"
              aria-label={t("admin.load.storage")}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(used * 100)}
            >
              <div
                className={`h-full w-full origin-left rounded-full ${used > 0.9 ? "bg-danger" : "bg-primary"}`}
                style={{ transform: `scaleX(${used})` }}
              />
            </div>
            <p className="text-sm text-muted tabular-nums">
              {t("admin.load.diskFree", {
                free: formatBytes(storage.disk_free, i18n.language),
                total: formatBytes(storage.disk_total, i18n.language),
              })}
            </p>
          </>
        ) : null}
      </section>
      <p className="text-sm text-muted md:col-span-2">{t("admin.load.refreshed")}</p>
    </div>
  );
}

// --- Limits ---------------------------------------------------------------------------------------

const LIMIT_FIELDS = ["max_file_mb", "max_total_mb", "daily_tasks", "max_batch", "retention_hours"] as const;

function LimitForm({ policy }: { policy: LimitPolicy }) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const formId = useId();
  const save = useMutation({
    mutationFn: (values: Partial<LimitPolicy>) => adminApi.saveLimits(policy.role, values),
    onSuccess: () => client.invalidateQueries({ queryKey: ["admin", "limits"] }),
  });
  const fieldErrors = save.error instanceof ApiError ? (save.error.details as Record<string, string[]>) : {};

  const onSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    save.mutate(Object.fromEntries(LIMIT_FIELDS.map((f) => [f, Number(form.get(f))])) as Partial<LimitPolicy>);
  };

  return (
    <form onSubmit={onSubmit} className={`${card} space-y-4 p-5`} aria-labelledby={`${formId}-h`} noValidate>
      <h2 id={`${formId}-h`} className="font-semibold">
        {t(`admin.limits.${policy.role}`)}
      </h2>
      <div className="grid gap-3 sm:grid-cols-2">
        {LIMIT_FIELDS.map((field) => (
          <div key={field} className="space-y-1">
            <label htmlFor={`${formId}-${field}`} className="block text-sm font-semibold">
              {t(`admin.limits.${field}`)}
            </label>
            <input
              id={`${formId}-${field}`}
              name={field}
              type="number"
              inputMode="numeric"
              min={1}
              defaultValue={policy[field]}
              aria-invalid={Boolean(fieldErrors[field])}
              aria-describedby={fieldErrors[field] ? `${formId}-${field}-err` : undefined}
              className="min-h-11 w-full rounded-xl border border-border-strong bg-surface px-3 text-base tabular-nums"
            />
            {fieldErrors[field] ? (
              <p id={`${formId}-${field}-err`} className="text-sm text-danger">
                {fieldErrors[field]?.join(" ")}
              </p>
            ) : null}
          </div>
        ))}
      </div>
      <div className="flex items-center gap-3">
        <button type="submit" className={btn.primary} disabled={save.isPending}>
          {t("admin.limits.save")}
        </button>
        <p className="text-sm text-success" role="status">
          {save.isSuccess ? t("admin.limits.saved") : ""}
        </p>
      </div>
    </form>
  );
}

function Limits() {
  const query = useQuery({ queryKey: ["admin", "limits"], queryFn: adminApi.limits });
  if (query.isPending) return <Loading />;
  if (query.isError) return <AdminError error={query.error} />;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {query.data.map((policy) => (
        <LimitForm key={policy.role} policy={policy} />
      ))}
    </div>
  );
}

// --- Tools ----------------------------------------------------------------------------------------

function Tools() {
  const { t } = useTranslation();
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["admin", "tools"], queryFn: adminApi.tools });
  type Switches = { slug: string; enabled: boolean }[];
  const key = ["admin", "tools"];
  const toggle = useMutation({
    mutationFn: ({ slug, enabled }: { slug: string; enabled: boolean }) => adminApi.setTool(slug, enabled),
    // Flip the switch at once; roll back if the server says no.
    onMutate: ({ slug, enabled }) => {
      const previous = client.getQueryData<Switches>(key);
      client.setQueryData<Switches>(key, (list) => list?.map((x) => (x.slug === slug ? { ...x, enabled } : x)));
      return { previous };
    },
    onError: (_err, _vars, context) => client.setQueryData(key, context?.previous),
    onSettled: () => {
      void client.invalidateQueries({ queryKey: key });
      void client.invalidateQueries({ queryKey: ["tools"] });
    },
  });
  if (query.isPending) return <Loading />;
  if (query.isError) return <AdminError error={query.error} />;

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted">{t("admin.tools.hint")}</p>
      <FormAlert message={toggle.isError ? errorMessage(t, toggle.error) : null} />
      <ul className={`${card} divide-y divide-border`}>
        {query.data.map((tool) => (
          <li key={tool.slug}>
            <label className="flex min-h-12 cursor-pointer items-center justify-between gap-3 px-4">
              <span>{toolName(t, tool.slug)}</span>
              <input
                type="checkbox"
                role="switch"
                checked={tool.enabled}
                aria-checked={tool.enabled}
                aria-label={t("admin.tools.toggle", { name: toolName(t, tool.slug) })}
                onChange={(e) => toggle.mutate({ slug: tool.slug, enabled: e.target.checked })}
                className="size-5 accent-primary"
              />
            </label>
          </li>
        ))}
      </ul>
    </div>
  );
}

// --- Page -----------------------------------------------------------------------------------------

const PANELS: Record<Tab, () => React.ReactNode> = {
  dashboard: Dashboard,
  users: Users,
  failures: Failures,
  load: Load,
  limits: Limits,
  tools: Tools,
};

export function AdminPage() {
  const { t } = useTranslation();
  const lang = useLang();
  const location = useLocation();
  const { tab = "dashboard" } = useParams();
  const status = useAuthStore((s) => s.status);
  const user = useAuthStore((s) => s.user);

  if (status === "loading") return <Loading />;
  if (status === "anon" || !user) {
    return <Navigate to={`/${lang}/login?next=${encodeURIComponent(location.pathname)}`} replace />;
  }
  // Non-staff see the ordinary 404: the panel's existence is not advertised.
  if (!user.is_staff || !(TABS as readonly string[]).includes(tab)) return <NotFoundPage />;
  const Panel = PANELS[tab as Tab];

  return (
    <div className="space-y-6">
      <title>{`${t("admin.title")} | ${t("meta.siteName")}`}</title>
      <meta name="robots" content="noindex" />
      <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{t("admin.title")}</h1>
      <nav aria-label={t("admin.title")} className="-mx-4 overflow-x-auto px-4">
        <ul className="flex gap-2">
          {TABS.map((name) => (
            <li key={name} className="shrink-0">
              <Link
                to={`/${lang}/admin${name === "dashboard" ? "" : `/${name}`}`}
                aria-current={name === tab ? "page" : undefined}
                className={`inline-flex min-h-11 items-center rounded-full border px-4 text-sm font-semibold transition-colors duration-150 ${
                  name === tab ? "border-primary bg-primary text-primary-fg" : "border-border-strong bg-surface hover:bg-surface-muted"
                }`}
              >
                {t(`admin.tabs.${name}`)}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <Panel />
    </div>
  );
}
