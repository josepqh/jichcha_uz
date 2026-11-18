import { useEffect, useId, useState } from "react";
import { useTranslation } from "react-i18next";

/** Browsers can show these; HEIC, TIFF and BMP originals get no preview. */
export const PREVIEWABLE = new Set(["image/jpeg", "image/png", "image/webp", "image/gif", "image/avif"]);

/**
 * Before/after view for compression (F-33). The range input drives the split, so it works with
 * the keyboard (arrow keys) and screen readers; dragging anywhere on the image moves it too.
 */
export function CompareSlider({ before, afterUrl }: { before: File; afterUrl: string }) {
  const { t } = useTranslation();
  const id = useId();
  const [position, setPosition] = useState(50);
  const [beforeUrl, setBeforeUrl] = useState<string | null>(null);

  useEffect(() => {
    const url = URL.createObjectURL(before);
    setBeforeUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [before]);

  if (!beforeUrl) return null;
  const badge = "absolute top-2 rounded-full bg-black/65 px-2.5 py-1 text-xs font-semibold text-white";

  return (
    <figure className="space-y-2">
      <div className="relative overflow-hidden rounded-xl border border-border bg-surface-muted select-none">
        <img src={afterUrl} alt={t("compare.after")} className="block max-h-[28rem] w-full object-contain" draggable={false} />
        <img
          src={beforeUrl}
          alt={t("compare.before")}
          className="absolute inset-0 block size-full object-contain"
          style={{ clipPath: `inset(0 ${100 - position}% 0 0)` }}
          draggable={false}
        />
        <div className="pointer-events-none absolute inset-y-0 w-0.5 bg-white shadow-[0_0_0_1px_rgb(0_0_0/0.35)]" style={{ left: `${position}%` }} aria-hidden="true" />
        <span className={`${badge} left-2`} aria-hidden="true">
          {t("compare.before")}
        </span>
        <span className={`${badge} right-2`} aria-hidden="true">
          {t("compare.after")}
        </span>
        <input
          id={id}
          type="range"
          min={0}
          max={100}
          value={position}
          onChange={(e) => setPosition(Number(e.target.value))}
          aria-label={t("compare.label")}
          aria-valuetext={t("compare.value", { percent: position })}
          className="absolute inset-0 size-full cursor-ew-resize opacity-0"
        />
      </div>
      <figcaption className="text-sm text-muted">{t("compare.hint")}</figcaption>
    </figure>
  );
}
