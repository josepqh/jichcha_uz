import { ArrowLeft, ArrowRight, LoaderCircle, RotateCw, Trash, Undo2 } from "lucide-react";
import type { PDFDocumentProxy } from "pdfjs-dist";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { btn } from "@/lib/ui";

export interface PageItem {
  key: string;
  page: number;
  rotate: 0 | 90 | 180 | 270;
}

const MAX_PAGES = 500;
const THUMB_WIDTH = 132;

/** pdf.js is large, so it is loaded only when someone opens the organizer. */
async function loadPdfJs() {
  const [pdfjs, worker] = await Promise.all([import("pdfjs-dist"), import("pdfjs-dist/build/pdf.worker.min.mjs?url")]);
  pdfjs.GlobalWorkerOptions.workerSrc = worker.default;
  return pdfjs;
}

export function initialPages(count: number): PageItem[] {
  return Array.from({ length: count }, (_, i) => ({ key: `p${i + 1}`, page: i + 1, rotate: 0 }));
}

function Thumb({ doc, page, rotate }: { doc: PDFDocumentProxy; page: number; rotate: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [visible, setVisible] = useState(false);

  // Render only thumbnails that scroll into view.
  useEffect(() => {
    const el = canvasRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(([entry]) => entry?.isIntersecting && setVisible(true), {
      rootMargin: "200px",
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!visible) return;
    let cancelled = false;
    let task: { cancel: () => void } | null = null;
    void (async () => {
      const pdfPage = await doc.getPage(page);
      if (cancelled || !canvasRef.current) return;
      const rotation = (pdfPage.rotate + rotate) % 360;
      const base = pdfPage.getViewport({ scale: 1, rotation });
      const viewport = pdfPage.getViewport({ scale: (THUMB_WIDTH * window.devicePixelRatio) / base.width, rotation });
      const canvas = canvasRef.current;
      canvas.width = Math.floor(viewport.width);
      canvas.height = Math.floor(viewport.height);
      const render = pdfPage.render({ canvas, viewport });
      task = render;
      await render.promise.catch(() => undefined);
    })();
    return () => {
      cancelled = true;
      task?.cancel();
    };
  }, [doc, page, rotate, visible]);

  return <canvas ref={canvasRef} className="max-h-full max-w-full bg-white shadow-sm" style={{ width: THUMB_WIDTH }} aria-hidden="true" />;
}

interface Props {
  file: File;
  pages: PageItem[];
  disabled: boolean;
  onChange: (pages: PageItem[]) => void;
  onError: (code: "pdf_encrypted" | "corrupt_file" | "too_many_pages") => void;
}

export function PdfOrganizer({ file, pages, disabled, onChange, onError }: Props) {
  const { t } = useTranslation();
  const [doc, setDoc] = useState<PDFDocumentProxy | null>(null);
  const [total, setTotal] = useState(0);
  const onChangeRef = useRef(onChange);
  const onErrorRef = useRef(onError);
  useEffect(() => {
    onChangeRef.current = onChange;
    onErrorRef.current = onError;
  });

  useEffect(() => {
    let cancelled = false;
    const opened: { task: { destroy: () => Promise<void> } | null } = { task: null };
    void (async () => {
      try {
        const pdfjs = await loadPdfJs();
        const task = pdfjs.getDocument({ data: new Uint8Array(await file.arrayBuffer()) });
        opened.task = task;
        const loaded = await task.promise;
        if (cancelled) return;
        if (loaded.numPages > MAX_PAGES) {
          onErrorRef.current("too_many_pages");
          return;
        }
        setDoc(loaded);
        setTotal(loaded.numPages);
        onChangeRef.current(initialPages(loaded.numPages));
      } catch (err) {
        if (!cancelled) onErrorRef.current((err as Error)?.name === "PasswordException" ? "pdf_encrypted" : "corrupt_file");
      }
    })();
    return () => {
      cancelled = true;
      void opened.task?.destroy(); // also frees the worker-side document
    };
  }, [file]);

  if (!doc) {
    return (
      <p className="flex items-center gap-2 text-muted" role="status">
        <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
        {t("organize.loading")}
      </p>
    );
  }

  const move = (index: number, delta: -1 | 1) => {
    const next = [...pages];
    const [item] = next.splice(index, 1);
    if (item) next.splice(index + delta, 0, item);
    onChange(next);
  };
  const rotate = (index: number) =>
    onChange(pages.map((p, i) => (i === index ? { ...p, rotate: (((p.rotate + 90) % 360) as PageItem["rotate"]) } : p)));
  const remove = (index: number) => onChange(pages.filter((_, i) => i !== index));

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted" aria-live="polite">
          {t("organize.count", { count: pages.length, total })}
        </p>
        <button type="button" className={btn.ghost} disabled={disabled} onClick={() => onChange(initialPages(total))}>
          <Undo2 className="size-4" aria-hidden="true" />
          {t("organize.reset")}
        </button>
      </div>
      <ol className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4" aria-label={t("organize.listLabel")}>
        {pages.map((item, index) => {
          const name = t("organize.page", { n: item.page });
          return (
            <li key={item.key} className="flex flex-col items-center gap-2 rounded-xl border border-border p-2">
              <div className="flex h-44 w-full items-center justify-center overflow-hidden">
                <Thumb doc={doc} page={item.page} rotate={item.rotate} />
              </div>
              <p className="text-sm font-semibold tabular-nums">
                {index + 1}. {name}
                {item.rotate ? <span className="font-normal text-muted"> · {item.rotate}°</span> : null}
              </p>
              <div className="grid grid-cols-2 gap-1">
                <button
                  type="button"
                  className={btn.icon}
                  disabled={disabled || index === 0}
                  onClick={() => move(index, -1)}
                  aria-label={t("organize.moveBack", { page: name })}
                >
                  <ArrowLeft className="size-5" aria-hidden="true" />
                </button>
                <button
                  type="button"
                  className={btn.icon}
                  disabled={disabled || index === pages.length - 1}
                  onClick={() => move(index, 1)}
                  aria-label={t("organize.moveForward", { page: name })}
                >
                  <ArrowRight className="size-5" aria-hidden="true" />
                </button>
                <button
                  type="button"
                  className={btn.icon}
                  disabled={disabled}
                  onClick={() => rotate(index)}
                  aria-label={t("organize.rotate", { page: name })}
                >
                  <RotateCw className="size-5" aria-hidden="true" />
                </button>
                <button
                  type="button"
                  className={btn.icon}
                  disabled={disabled || pages.length === 1}
                  onClick={() => remove(index)}
                  aria-label={t("organize.remove", { page: name })}
                >
                  <Trash className="size-5" aria-hidden="true" />
                </button>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
