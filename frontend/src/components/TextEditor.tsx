import { useQueryClient } from "@tanstack/react-query";
import DOMPurify from "dompurify";
import { FileUp } from "lucide-react";
import { marked } from "marked";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { TaskPanel } from "@/components/TaskPanel";
import { createTask } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { btn, card } from "@/lib/ui";

const DRAFT_KEY = "uv-text-draft";
const SERVER_TARGETS = ["pdf", "docx", "epub"] as const;
type Mode = "markdown" | "plain";

interface Draft {
  text: string;
  name: string;
  mode: Mode;
}

/** The draft stays in this browser only (localStorage); nothing is sent until a server export. */
function loadDraft(): Draft {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    if (raw) return { text: "", name: "matn", mode: "markdown", ...JSON.parse(raw) };
  } catch {
    // private mode, blocked storage
  }
  return { text: "", name: "matn", mode: "markdown" };
}

function saveDraft(draft: Draft) {
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
  } catch {
    // ignore
  }
}

/** Markdown -> HTML, sanitised: the preview and the HTML export never carry scripts or event handlers. */
export function renderMarkdown(text: string): string {
  return DOMPurify.sanitize(marked.parse(text, { async: false, gfm: true, breaks: false }));
}

function escapeHtml(text: string) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export function htmlDocument(title: string, body: string): string {
  return `<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapeHtml(title)}</title>
<style>body{font:16px/1.6 system-ui,sans-serif;max-width:46rem;margin:2rem auto;padding:0 1rem}pre{white-space:pre-wrap}</style>
</head>
<body>
${body}
</body>
</html>
`;
}

function download(name: string, content: string, type: string) {
  const url = URL.createObjectURL(new Blob([content], { type: `${type};charset=utf-8` }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

const safeBase = (name: string) => name.trim().replace(/[\\/:*?"<>|\x00-\x1f]+/g, "_").slice(0, 80) || "matn";

export function TextWorkspace() {
  const { t } = useTranslation();
  const id = useId();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<Draft>(loadDraft);
  const [view, setView] = useState<"edit" | "preview">("edit");
  const [error, setError] = useState<string | null>(null);
  const [task, setTask] = useState<{ id: string | null; progress: number | null; bytes: number } | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => saveDraft(draft), 400);
    return () => clearTimeout(timer);
  }, [draft]);

  const preview = useMemo(
    () => (draft.mode === "markdown" ? renderMarkdown(draft.text) : `<pre>${escapeHtml(draft.text)}</pre>`),
    [draft.text, draft.mode],
  );
  const words = draft.text.trim() ? draft.text.trim().split(/\s+/).length : 0;
  const ext = draft.mode === "markdown" ? "md" : "txt";
  const base = safeBase(draft.name);

  const openFile = async (file: File) => {
    setError(null);
    if (file.size > 5 * 1024 * 1024) {
      setError(t("text.tooBig"));
      return;
    }
    const text = await file.text();
    const markdown = /\.(md|markdown)$/i.test(file.name);
    setDraft({ text, name: file.name.replace(/\.[^.]+$/, ""), mode: markdown ? "markdown" : "plain" });
  };

  const exportOnServer = async (target: (typeof SERVER_TARGETS)[number]) => {
    setError(null);
    if (!draft.text.trim()) {
      setError(t("text.empty"));
      return;
    }
    const file = new File([draft.text], `${base}.${ext}`, { type: draft.mode === "markdown" ? "text/markdown" : "text/plain" });
    setTask({ id: null, progress: 0, bytes: file.size });
    try {
      const created = await createTask({
        tool: "text-convert",
        options: { target },
        files: [file],
        onProgress: (progress) => setTask((prev) => (prev ? { ...prev, progress } : prev)),
      });
      queryClient.setQueryData(["task", created.id], created);
      void queryClient.invalidateQueries({ queryKey: ["usage"] });
      setTask({ id: created.id, progress: null, bytes: file.size });
    } catch (err) {
      setTask(null);
      setError(errorMessage(t, err));
    }
  };

  if (task) {
    return <TaskPanel taskId={task.id} uploadProgress={task.progress} inputBytes={task.bytes} onReset={() => setTask(null)} />;
  }

  return (
    <div className="space-y-4">
      <section className={`${card} space-y-4 p-5 sm:p-6`} aria-labelledby={`${id}-h`}>
        <h2 id={`${id}-h`} className="sr-only">
          {t("text.editor")}
        </h2>
        <div className="flex flex-wrap items-end gap-3">
          <input
            ref={fileInput}
            type="file"
            accept=".txt,.md,.markdown,text/plain,text/markdown"
            hidden
            data-testid="text-file-input"
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (file) void openFile(file);
            }}
          />
          <button type="button" className={btn.secondary} onClick={() => fileInput.current?.click()}>
            <FileUp className="size-4" aria-hidden="true" />
            {t("text.open")}
          </button>
          <div className="space-y-1">
            <label htmlFor={`${id}-name`} className="block text-sm font-semibold">
              {t("text.name")}
            </label>
            <input
              id={`${id}-name`}
              value={draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
              autoComplete="off"
              spellCheck={false}
              className="min-h-11 w-56 max-w-full rounded-xl border border-border-strong bg-surface px-3 text-base"
            />
          </div>
          <fieldset className="flex gap-2">
            <legend className="sr-only">{t("text.mode")}</legend>
            {(["markdown", "plain"] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                aria-pressed={draft.mode === mode}
                className={draft.mode === mode ? btn.primary : btn.secondary}
                onClick={() => setDraft({ ...draft, mode })}
              >
                {t(`text.modes.${mode}`)}
              </button>
            ))}
          </fieldset>
        </div>

        <div role="tablist" aria-label={t("text.editor")} className="flex gap-2 lg:hidden">
          {(["edit", "preview"] as const).map((v) => (
            <button
              key={v}
              type="button"
              role="tab"
              aria-selected={view === v}
              className={view === v ? btn.primary : btn.secondary}
              onClick={() => setView(v)}
            >
              {t(`text.views.${v}`)}
            </button>
          ))}
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <div className={view === "edit" ? "block" : "hidden lg:block"}>
            <label htmlFor={`${id}-text`} className="mb-1.5 block text-sm font-semibold">
              {t("text.textLabel")}
            </label>
            <textarea
              id={`${id}-text`}
              value={draft.text}
              onChange={(e) => setDraft({ ...draft, text: e.target.value })}
              placeholder={t("text.placeholder")}
              spellCheck
              className="min-h-80 w-full rounded-xl border border-border-strong bg-surface p-3 font-mono text-base leading-relaxed"
            />
          </div>
          <div className={view === "preview" ? "block" : "hidden lg:block"}>
            <p className="mb-1.5 text-sm font-semibold">{t("text.views.preview")}</p>
            <div
              className="prose-uv min-h-80 overflow-auto rounded-xl border border-border bg-surface-muted p-4 [overflow-wrap:anywhere]"
              // Sanitised by DOMPurify (renderMarkdown) or escaped (plain text).
              dangerouslySetInnerHTML={{ __html: preview }}
            />
          </div>
        </div>
        <p className="text-sm text-muted tabular-nums" aria-live="polite">
          {t("text.stats", { words, chars: draft.text.length })} · {t("text.draftNote")}
        </p>
      </section>

      {error ? (
        <p role="alert" className="rounded-lg border border-danger px-4 py-3 text-danger">
          {error}
        </p>
      ) : null}

      <section className={`${card} space-y-3 p-5 sm:p-6`} aria-labelledby={`${id}-save`}>
        <h2 id={`${id}-save`} className="font-semibold">
          {t("text.save")}
        </h2>
        <div className="flex flex-wrap gap-2">
          <button type="button" className={btn.secondary} onClick={() => download(`${base}.${ext}`, draft.text, draft.mode === "markdown" ? "text/markdown" : "text/plain")}>
            {ext.toUpperCase()}
          </button>
          <button type="button" className={btn.secondary} onClick={() => download(`${base}.html`, htmlDocument(base, preview), "text/html")}>
            HTML
          </button>
          {SERVER_TARGETS.map((target) => (
            <button key={target} type="button" className={btn.primary} onClick={() => void exportOnServer(target)}>
              {target.toUpperCase()}
            </button>
          ))}
        </div>
        <p className="text-sm text-muted">{t("text.saveNote")}</p>
      </section>
    </div>
  );
}
