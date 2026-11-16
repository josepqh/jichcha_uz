import { useQueryClient } from "@tanstack/react-query";
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useParams } from "react-router";

import { Dropzone } from "@/components/Dropzone";
import { FileList, type PickedFile } from "@/components/FileList";
import { editOptions, ImageEditor, initialEdit, type EditState } from "@/components/ImageEditor";
import type { PageItem } from "@/components/PdfOrganizer";
import { TaskPanel } from "@/components/TaskPanel";
import { TextWorkspace } from "@/components/TextEditor";
import { ToolOptions } from "@/components/ToolOptions";
import { useDisabledTools, useUsage } from "@/hooks/useApi";
import { useLang } from "@/hooks/useLang";
import { createTask } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { isToolSlug, resolveConversion, toApiOptions, TOOLS, type Conversion, type OptionValues, type ToolDef } from "@/lib/tools";
import { btn, card } from "@/lib/ui";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { useAuthStore } from "@/stores/auth";

const PdfOrganizer = lazy(() => import("@/components/PdfOrganizer").then((m) => ({ default: m.PdfOrganizer })));

const MB = 1024 * 1024;
const RANGES = /^\s*\d+\s*(-\s*\d*\s*)?(,\s*\d+\s*(-\s*\d*\s*)?)*,?\s*$/;

function Workspace({ tool, conversion }: { tool: ToolDef; conversion: Conversion | null }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const usage = useUsage();
  const limits = usage.data?.limits;
  const lang = useLang();
  const { pathname } = useLocation();
  const isGuest = useAuthStore((s) => s.status === "anon");
  const disabled = useDisabledTools().has(tool.slug);

  const [items, setItems] = useState<PickedFile[]>([]);
  const [options, setOptions] = useState<OptionValues>(() => ({ ...tool.defaults, ...conversion?.options }));
  const [pages, setPages] = useState<PageItem[]>([]);
  const [edit, setEdit] = useState<EditState>(initialEdit);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string | undefined>>({});
  const [working, setWorking] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [inputBytes, setInputBytes] = useState(0);

  const itemsRef = useRef(items);
  itemsRef.current = items;
  const abortRef = useRef<AbortController | null>(null);

  // Arrived from a previous result ("next step"): fetch that file and start with it, no re-upload by hand.
  const handedOver = (useLocation().state as { from?: { url: string; name: string } } | null)?.from;
  const tookOver = useRef(false);
  useEffect(() => {
    if (!handedOver || tookOver.current) return;
    tookOver.current = true;
    void fetch(handedOver.url, { credentials: "same-origin" })
      .then((res) => (res.ok ? res.blob() : Promise.reject(new Error(String(res.status)))))
      .then((blob) => addFiles([new File([blob], handedOver.name, { type: blob.type })]))
      .catch(() => setError(t("errors.file_expired")));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- once per arrival
  }, [handedOver]);

  useEffect(
    () => () => {
      abortRef.current?.abort();
      for (const item of itemsRef.current) URL.revokeObjectURL(item.preview);
    },
    [],
  );

  const maxFiles = Math.min(tool.maxFiles ?? Infinity, limits?.max_batch ?? Infinity);

  const addFiles = (files: File[]) => {
    setError(null);
    const maxBytes = (limits?.max_file_mb ?? Infinity) * MB;
    const tooBig = files.find((f) => f.size > maxBytes);
    if (tooBig) setError(t("errors.file_too_large", { name: tooBig.name, max_file_mb: limits?.max_file_mb }));
    const accepted = files.filter((f) => f.size <= maxBytes);
    const room = maxFiles - items.length;
    if (accepted.length > room) setError(t("errors.too_many_files", { max_files: maxFiles }));
    const next = accepted.slice(0, Math.max(room, 0)).map((file) => ({
      id: crypto.randomUUID(),
      file,
      preview: URL.createObjectURL(file),
    }));
    setItems((prev) => [...prev, ...next]);
  };

  const remove = (id: string) => {
    setPages([]);
    setEdit((prev) => ({ ...prev, crop: initialEdit.crop }));
    setItems((prev) => {
      const gone = prev.find((i) => i.id === id);
      if (gone) URL.revokeObjectURL(gone.preview);
      return prev.filter((i) => i.id !== id);
    });
  };

  const move = (id: string, delta: -1 | 1) =>
    setItems((prev) => {
      const from = prev.findIndex((i) => i.id === id);
      const to = from + delta;
      if (from < 0 || to < 0 || to >= prev.length) return prev;
      const next = [...prev];
      const [moved] = next.splice(from, 1);
      if (moved) next.splice(to, 0, moved);
      return next;
    });

  const reset = () => {
    abortRef.current?.abort();
    for (const item of items) URL.revokeObjectURL(item.preview);
    setItems([]);
    setPages([]);
    setEdit(initialEdit);
    setError(null);
    setFieldErrors({});
    setWorking(false);
    setUploadProgress(null);
    setTaskId(null);
  };

  const validate = (): boolean => {
    if (!items.length) {
      setError(t("errors.no_files"));
      return false;
    }
    if (items.length < tool.minFiles) {
      setError(t("errors.too_few_files", { min_files: tool.minFiles }));
      return false;
    }
    if (tool.slug === "pdf-split" && options.mode === "ranges" && !RANGES.test(options.ranges ?? "")) {
      setFieldErrors({ ranges: t("errors.invalid_page_range") });
      return false;
    }
    if (tool.editor === "image" && edit.resize === "pixels" && !edit.width && !edit.height) {
      setError(t("edit.needSize"));
      return false;
    }
    if (tool.editor === "organize" && pages.length === 0) {
      setError(t("organize.empty"));
      return false;
    }
    return true;
  };

  const submit = async () => {
    setError(null);
    setFieldErrors({});
    if (!validate()) return;
    const controller = new AbortController();
    abortRef.current = controller;
    setWorking(true);
    setUploadProgress(0);
    setInputBytes(items.reduce((sum, i) => sum + i.file.size, 0));
    const apiOptions =
      tool.editor === "organize"
        ? { pages: pages.map(({ page, rotate }) => ({ page, rotate })) }
        : tool.editor === "image"
          ? editOptions(edit, items.length === 1)
          : toApiOptions(tool, options);
    try {
      const task = await createTask({
        tool: tool.slug,
        options: apiOptions,
        files: items.map((i) => i.file),
        onProgress: setUploadProgress,
        signal: controller.signal,
      });
      queryClient.setQueryData(["task", task.id], task);
      void queryClient.invalidateQueries({ queryKey: ["usage"] });
      setTaskId(task.id);
      setUploadProgress(null);
    } catch (err) {
      if (controller.signal.aborted) return;
      setWorking(false);
      setUploadProgress(null);
      setError(errorMessage(t, err));
    }
  };

  const upper = (s: string) => s.toUpperCase();
  const title = conversion
    ? t("conversion.title", { from: upper(conversion.from), to: upper(conversion.to) })
    : t(`tools.${tool.slug}.title`);
  const description = conversion
    ? t("conversion.description", { from: upper(conversion.from), to: upper(conversion.to) })
    : t(`tools.${tool.slug}.description`);
  const hint = [
    tool.formats ? t("upload.formats", { formats: tool.formats }) : t("upload.anyFormat"),
    limits ? t("upload.limits", { maxFile: limits.max_file_mb, maxBatch: maxFiles }) : null,
  ]
    .filter(Boolean)
    .join(" ");
  const actionLabel = t(`actions.${tool.slug}`, {
    target: upper(options.target ?? options.archiveFormat ?? options.format ?? ""),
  });
  const organizing = tool.editor === "organize" && items[0];

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <title>{`${title} | ${t("meta.siteName")}`}</title>
      <meta name="description" content={description} />

      <header className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight text-balance sm:text-4xl">{title}</h1>
        <p className="text-muted text-pretty">{description}</p>
      </header>

      {disabled ? (
        <p role="status" className="rounded-lg border border-border-strong px-4 py-3">
          {t("errors.tool_disabled")}
        </p>
      ) : tool.editor === "text" ? (
        <TextWorkspace />
      ) : working ? (
        <TaskPanel taskId={taskId} uploadProgress={uploadProgress} inputBytes={inputBytes} onReset={reset} />
      ) : (
        <>
          {items.length === 0 ? (
            <Dropzone accept={tool.accept} multiple={maxFiles > 1} hint={hint} onFiles={addFiles} />
          ) : (
            <section className={`${card} space-y-4 p-5 sm:p-6`} aria-labelledby="selected-heading">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 id="selected-heading" className="font-semibold">
                  {t("upload.selected", { count: items.length })}
                </h2>
                {items.length < maxFiles ? (
                  <Dropzone accept={tool.accept} multiple={maxFiles > 1} compact onFiles={addFiles} />
                ) : null}
              </div>
              {tool.reorder && items.length > 1 ? <p className="text-sm text-muted">{t(`upload.orderHint.${tool.slug}`)}</p> : null}
              <FileList
                items={items}
                reorder={tool.reorder}
                disabled={false}
                onRemove={remove}
                onMove={move}
                labelledBy="selected-heading"
              />
            </section>
          )}

          {organizing ? (
            <section className={`${card} p-5 sm:p-6`} aria-label={t("organize.listLabel")}>
              <Suspense fallback={<p className="text-muted">{t("organize.loading")}</p>}>
                <PdfOrganizer
                  file={items[0]!.file}
                  pages={pages}
                  disabled={false}
                  onChange={setPages}
                  onError={(code) => setError(t(`errors.${code}`))}
                />
              </Suspense>
            </section>
          ) : null}

          {tool.editor === "image" && items[0] ? (
            <section className={`${card} p-5 sm:p-6`} aria-label={t("edit.title")}>
              <ImageEditor file={items[0].file} multiple={items.length > 1} state={edit} onChange={setEdit} />
            </section>
          ) : null}

          {error ? (
            <div role="alert" className="space-y-2 rounded-lg border border-danger px-4 py-3">
              <p className="text-danger">{error}</p>
              {isGuest ? (
                <p className="text-sm">
                  <Link
                    to={`/${lang}/register?next=${encodeURIComponent(pathname)}`}
                    className="font-semibold text-primary underline-offset-4 hover:underline"
                  >
                    {t("auth.register.submit")}
                  </Link>{" "}
                  <span className="text-muted">{t("auth.benefits")}</span>
                </p>
              ) : null}
            </div>
          ) : null}

          <section className={`${card} space-y-6 p-5 sm:p-6`}>
            <ToolOptions
              fields={tool.fields}
              values={options}
              disabled={false}
              errors={fieldErrors}
              onChange={(name, value) => {
                setFieldErrors({});
                setOptions((prev) => ({ ...prev, [name]: value }));
              }}
            />
            <button type="button" className={`${btn.primary} w-full text-base sm:w-auto`} onClick={() => void submit()}>
              {actionLabel}
            </button>
          </section>
        </>
      )}
    </div>
  );
}

export function ToolPage() {
  const { slug, pair } = useParams();
  const { pathname } = useLocation();
  const conversion = resolveConversion(pair);
  const toolSlug = conversion?.tool ?? (isToolSlug(slug) ? slug : null);
  if (!toolSlug) return <NotFoundPage />;
  // Remount on navigation so state from another tool never leaks in.
  return <Workspace key={pathname} tool={TOOLS[toolSlug]} conversion={conversion} />;
}
