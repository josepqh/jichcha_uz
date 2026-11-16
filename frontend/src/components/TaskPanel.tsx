import { CircleCheck, CircleExclamationPoint, Download, FileArchive, LoaderCircle, RotateCcw, Trash } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { useDeleteTask, useDisabledTools, useTask } from "@/hooks/useApi";
import { useLang } from "@/hooks/useLang";
import { buildCatalog, familyOf } from "@/lib/catalog";
import type { Task } from "@/lib/api";
import { errorMessage, taskErrorMessage } from "@/lib/errors";
import { formatBytes, formatTime, savedPercent } from "@/lib/format";
import { btn, card } from "@/lib/ui";

interface Props {
  taskId: string | null;
  uploadProgress: number | null;
  inputBytes: number;
  onReset: () => void;
}

function Progress({ value, label }: { value: number | null; label: string }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 font-semibold">
        <LoaderCircle className="size-5 animate-spin text-primary" aria-hidden="true" />
        <span>{label}</span>
      </div>
      <div
        className="h-2 overflow-hidden rounded-full bg-surface-muted"
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value === null ? undefined : Math.round(value * 100)}
      >
        <div
          className={`h-full rounded-full bg-primary ${value === null ? "w-1/3 animate-pulse" : "w-full origin-left transition-transform duration-200"}`}
          style={value === null ? undefined : { transform: `scaleX(${Math.max(0.04, value)})` }}
        />
      </div>
    </div>
  );
}

function Savings({ task, inputBytes }: { task: Task; inputBytes: number }) {
  const { t, i18n } = useTranslation();
  if (!["image-compress", "pdf-compress"].includes(task.tool) || inputBytes === 0) return null;
  const outputBytes = task.outputs.reduce((sum, f) => sum + f.size, 0);
  const percent = savedPercent(inputBytes, outputBytes);
  const params = {
    percent,
    before: formatBytes(inputBytes, i18n.language),
    after: formatBytes(outputBytes, i18n.language),
  };
  return <p className="tabular-nums">{percent > 0 ? t("status.saved", params) : t("status.notSaved", params)}</p>;
}

const CATALOG = buildCatalog();

/** Tools that take the result as input ("PDF made -> compress it"). One result only. */
function NextSteps({ task }: { task: Task }) {
  const { t } = useTranslation();
  const lang = useLang();
  const disabled = useDisabledTools();
  const [output] = task.outputs;
  if (task.outputs.length !== 1 || !output?.download_url) return null;
  const ext = output.name.split(".").pop()?.toLowerCase() ?? "";
  const family = familyOf(ext === "jpeg" ? "jpg" : ext);
  const tools = (CATALOG.find((s) => s.family === family)?.entries ?? [])
    .filter((e) => e.kind === "tool" && e.tool.slug !== task.tool && !disabled.has(e.tool.slug))
    .slice(0, 4);
  if (!tools.length) return null;
  return (
    <section aria-labelledby="next-steps" className="space-y-2">
      <h3 id="next-steps" className="text-sm font-semibold">
        {t("next.title")}
      </h3>
      <ul className="flex flex-wrap gap-2">
        {tools.map(({ tool }) => (
          <li key={tool.slug}>
            <Link
              to={`/${lang}/tools/${tool.slug}`}
              state={{ from: { url: output.download_url, name: output.name } }}
              className="inline-flex min-h-11 items-center gap-2 rounded-full border border-border-strong bg-surface px-4 text-sm font-semibold transition-colors duration-150 hover:bg-surface-muted"
            >
              <tool.icon className="size-4" aria-hidden="true" />
              {t(`tools.${tool.slug}.name`)}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** An extracted archive can hold up to 1000 files; the rest stay one click away. */
const VISIBLE_OUTPUTS = 20;

function Done({ task, inputBytes, onReset }: { task: Task; inputBytes: number; onReset: () => void }) {
  const { t, i18n } = useTranslation();
  const del = useDeleteTask();
  const [showAll, setShowAll] = useState(false);

  if (task.files_deleted) {
    return (
      <div className="space-y-4">
        <p>{t("status.deleted")}</p>
        <button type="button" className={btn.primary} onClick={onReset}>
          <RotateCcw className="size-4" aria-hidden="true" />
          {t("actions.again")}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2 text-lg font-semibold">
        <CircleCheck className="size-6 text-success" aria-hidden="true" />
        <span>{t("status.done")}</span>
      </div>
      <Savings task={task} inputBytes={inputBytes} />

      {task.bundle?.download_url ? (
        <a href={task.bundle.download_url} download className={`${btn.primary} w-full sm:w-auto`}>
          <FileArchive className="size-4" aria-hidden="true" />
          {t("actions.downloadAll")} ({formatBytes(task.bundle.size, i18n.language)})
        </a>
      ) : null}

      <ul className="divide-y divide-border">
        {(showAll ? task.outputs : task.outputs.slice(0, VISIBLE_OUTPUTS)).map((file) => (
          <li key={file.id} className="flex items-center gap-3 py-2">
            <div className="min-w-0 flex-1">
              <p className="line-clamp-2 font-medium [overflow-wrap:anywhere]" title={file.name}>
                {file.name}
              </p>
              <p className="text-sm text-muted tabular-nums">{formatBytes(file.size, i18n.language)}</p>
            </div>
            {file.download_url ? (
              <a
                href={file.download_url}
                download
                className={task.bundle ? btn.secondary : btn.primary}
                aria-label={t("actions.downloadFile", { name: file.name })}
              >
                <Download className="size-4" aria-hidden="true" />
                <span className="hidden sm:inline">{t("actions.download")}</span>
              </a>
            ) : null}
          </li>
        ))}
      </ul>
      {!showAll && task.outputs.length > VISIBLE_OUTPUTS ? (
        <button type="button" className={btn.ghost} onClick={() => setShowAll(true)}>
          {t("status.showAll", { count: task.outputs.length })}
        </button>
      ) : null}

      <NextSteps task={task} />

      <p className="text-sm text-muted">{t("status.expires", { time: formatTime(task.expires_at, i18n.language) })}</p>
      {del.isError ? (
        <p role="alert" className="text-sm text-danger">
          {errorMessage(t, del.error)}
        </p>
      ) : null}
      <div className="flex flex-col gap-2 sm:flex-row">
        <button type="button" className={btn.secondary} onClick={onReset}>
          <RotateCcw className="size-4" aria-hidden="true" />
          {t("actions.again")}
        </button>
        <button
          type="button"
          className={btn.danger}
          disabled={del.isPending}
          onClick={() => {
            if (window.confirm(t("actions.deleteConfirm"))) del.mutate(task.id);
          }}
        >
          <Trash className="size-4" aria-hidden="true" />
          {t("actions.deleteNow")}
        </button>
      </div>
    </div>
  );
}

function Failed({ message, onReset }: { message: string; onReset: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="space-y-4">
      <div className="flex items-start gap-2">
        <CircleExclamationPoint className="mt-0.5 size-5 shrink-0 text-danger" aria-hidden="true" />
        <div>
          <p className="font-semibold">{t("status.failed")}</p>
          <p role="alert">{message}</p>
        </div>
      </div>
      <button type="button" className={btn.primary} onClick={onReset}>
        <RotateCcw className="size-4" aria-hidden="true" />
        {t("actions.retry")}
      </button>
    </div>
  );
}

export function TaskPanel({ taskId, uploadProgress, inputBytes, onReset }: Props) {
  const { t } = useTranslation();
  const query = useTask(taskId);
  const task = query.data;

  let body;
  if (!taskId && uploadProgress !== null) {
    body = <Progress value={uploadProgress} label={t("status.uploading", { percent: Math.round(uploadProgress * 100) })} />;
  } else if (query.isError) {
    body = <Failed message={errorMessage(t, query.error)} onReset={onReset} />;
  } else if (!task || task.status === "queued" || task.status === "processing") {
    body = <Progress value={null} label={t(`status.${task?.status ?? "queued"}`)} />;
  } else if (task.status === "failed") {
    body = <Failed message={taskErrorMessage(t, task.error_code)} onReset={onReset} />;
  } else {
    body = <Done task={task} inputBytes={inputBytes} onReset={onReset} />;
  }

  return (
    <section className={`${card} p-5 sm:p-6`} aria-live="polite" aria-busy={!task || task.status === "queued" || task.status === "processing"}>
      {body}
    </section>
  );
}
