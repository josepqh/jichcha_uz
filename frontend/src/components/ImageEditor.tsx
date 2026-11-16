import { FlipHorizontal2, FlipVertical2, RotateCcw, RotateCw } from "lucide-react";
import { useEffect, useId, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { useTranslation } from "react-i18next";

import { btn } from "@/lib/ui";

export const ASPECTS = ["free", "1:1", "4:5", "16:9", "3:4"] as const;
export type Aspect = (typeof ASPECTS)[number];
// i18next reads ":" as a namespace separator, so translation keys can't be "1:1".
const ASPECT_KEY: Record<Aspect, string> = { free: "free", "1:1": "square", "4:5": "portrait", "16:9": "wide", "3:4": "id" };

export interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface EditState {
  aspect: Aspect;
  crop: Box;
  rotate: 0 | 90 | 180 | 270;
  flip: "none" | "horizontal" | "vertical";
  resize: "none" | "percent" | "pixels";
  percent: number;
  width: string;
  height: string;
  format: "keep" | "jpg" | "png" | "webp";
}

const FULL: Box = { x: 0, y: 0, w: 1, h: 1 };
const MIN = 0.05;

export const initialEdit: EditState = {
  aspect: "free",
  crop: FULL,
  rotate: 0,
  flip: "none",
  resize: "none",
  percent: 50,
  width: "",
  height: "",
  format: "keep",
};

const ratioOf = (aspect: Aspect) => (aspect === "free" ? null : Number(aspect.split(":")[0]) / Number(aspect.split(":")[1]));
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

/** Largest centred box with the aspect ratio, in image fractions. */
export function fitBox(aspect: Aspect, imgW: number, imgH: number): Box {
  const ratio = ratioOf(aspect);
  if (!ratio) return FULL;
  const w = Math.min(1, (imgH * ratio) / imgW);
  const h = Math.min(1, (imgW / ratio) / imgH);
  return { x: (1 - w) / 2, y: (1 - h) / 2, w, h };
}

/** API options. A crop box is sent only for a single file; batches use the centred aspect crop. */
export function editOptions(state: EditState, single: boolean): Record<string, unknown> {
  const options: Record<string, unknown> = {
    aspect: state.aspect,
    rotate: state.rotate,
    flip: state.flip,
    resize: state.resize,
    format: state.format,
  };
  const { x, y, w, h } = state.crop;
  if (single && (w < 0.999 || h < 0.999)) {
    options.crop = { x: +x.toFixed(4), y: +y.toFixed(4), w: +w.toFixed(4), h: +h.toFixed(4) };
  }
  if (state.resize === "percent") options.percent = state.percent;
  if (state.resize === "pixels") {
    if (state.width) options.width = Number(state.width);
    if (state.height) options.height = Number(state.height);
  }
  return options;
}

function Radio<T extends string | number>({
  legend,
  name,
  value,
  choices,
  label,
  onChange,
}: {
  legend: string;
  name: string;
  value: T;
  choices: readonly T[];
  label: (v: T) => string;
  onChange: (v: T) => void;
}) {
  return (
    <fieldset>
      <legend className="mb-2 text-sm font-semibold">{legend}</legend>
      <div className="flex flex-wrap gap-2">
        {choices.map((choice) => (
          <label
            key={String(choice)}
            className={`inline-flex min-h-11 cursor-pointer items-center rounded-xl border px-3 text-sm font-semibold has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-ring ${
              value === choice ? "border-primary bg-primary text-primary-fg" : "border-border-strong bg-surface"
            }`}
          >
            <input
              type="radio"
              name={name}
              className="sr-only"
              checked={value === choice}
              onChange={() => onChange(choice)}
            />
            {label(choice)}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function CropArea({ src, state, onBox, onSize }: {
  src: string;
  state: EditState;
  onBox: (box: Box) => void;
  onSize: (w: number, h: number) => void;
}) {
  const { t } = useTranslation();
  const frame = useRef<HTMLDivElement>(null);
  const drag = useRef<{ mode: "move" | "resize"; px: number; py: number; box: Box } | null>(null);
  const ratio = ratioOf(state.aspect);
  const [natural, setNatural] = useState<{ w: number; h: number } | null>(null);
  const { x, y, w, h } = state.crop;

  // Keep the box's aspect ratio (in pixels) when resizing with a fixed aspect.
  const sized = (box: Box, newW: number): Box => {
    let width = clamp(newW, MIN, 1 - box.x);
    let height = box.h;
    if (ratio && natural) {
      height = (width * natural.w) / ratio / natural.h;
      if (box.y + height > 1) {
        height = 1 - box.y;
        width = (height * natural.h * ratio) / natural.w;
      }
    }
    return { ...box, w: width, h: clamp(height, MIN, 1 - box.y) };
  };

  const onPointerDown = (e: PointerEvent<HTMLDivElement>, mode: "move" | "resize") => {
    e.preventDefault();
    e.stopPropagation();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    drag.current = { mode, px: e.clientX, py: e.clientY, box: state.crop };
  };
  const onPointerMove = (e: PointerEvent<HTMLDivElement>) => {
    const d = drag.current;
    const rect = frame.current?.getBoundingClientRect();
    if (!d || !rect) return;
    const dx = (e.clientX - d.px) / rect.width;
    const dy = (e.clientY - d.py) / rect.height;
    if (d.mode === "move") {
      onBox({ ...d.box, x: clamp(d.box.x + dx, 0, 1 - d.box.w), y: clamp(d.box.y + dy, 0, 1 - d.box.h) });
    } else if (ratio) {
      onBox(sized(d.box, d.box.w + dx));
    } else {
      onBox({ ...d.box, w: clamp(d.box.w + dx, MIN, 1 - d.box.x), h: clamp(d.box.h + dy, MIN, 1 - d.box.y) });
    }
  };
  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    const step = 0.02;
    const keys: Record<string, [number, number]> = {
      ArrowLeft: [-step, 0],
      ArrowRight: [step, 0],
      ArrowUp: [0, -step],
      ArrowDown: [0, step],
    };
    const move = keys[e.key];
    if (!move) return;
    e.preventDefault();
    if (e.shiftKey) {
      // Shift + arrows resize from the bottom-right corner.
      const box = ratio ? sized(state.crop, w + move[0] + move[1]) : {
        ...state.crop,
        w: clamp(w + move[0], MIN, 1 - x),
        h: clamp(h + move[1], MIN, 1 - y),
      };
      onBox(box);
    } else {
      onBox({ ...state.crop, x: clamp(x + move[0], 0, 1 - w), y: clamp(y + move[1], 0, 1 - h) });
    }
  };

  return (
    <div
      ref={frame}
      className="relative mx-auto w-fit touch-none select-none"
      onPointerMove={onPointerMove}
      onPointerUp={() => (drag.current = null)}
      onPointerCancel={() => (drag.current = null)}
    >
      <img
        src={src}
        alt=""
        draggable={false}
        className="block max-h-80 max-w-full"
        onLoad={(e) => {
          const img = e.currentTarget;
          setNatural({ w: img.naturalWidth, h: img.naturalHeight });
          onSize(img.naturalWidth, img.naturalHeight);
        }}
      />
      {/* Dim outside the crop, clipped to the photo (the handle above stays unclipped). */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
        <div
          className="absolute shadow-[0_0_0_9999px_rgb(0_0_0/0.5)]"
          style={{ left: `${x * 100}%`, top: `${y * 100}%`, width: `${w * 100}%`, height: `${h * 100}%` }}
        />
      </div>
      <div
        role="slider"
        tabIndex={0}
        aria-label={t("edit.cropArea")}
        aria-valuetext={t("edit.cropValue", {
          x: Math.round(x * 100),
          y: Math.round(y * 100),
          w: Math.round(w * 100),
          h: Math.round(h * 100),
        })}
        aria-valuenow={Math.round(w * 100)}
        aria-valuemin={Math.round(MIN * 100)}
        aria-valuemax={100}
        onKeyDown={onKeyDown}
        onPointerDown={(e) => onPointerDown(e, "move")}
        className="absolute cursor-move border-2 border-white outline-offset-2"
        style={{ left: `${x * 100}%`, top: `${y * 100}%`, width: `${w * 100}%`, height: `${h * 100}%` }}
      >
        <div
          aria-hidden="true"
          onPointerDown={(e) => onPointerDown(e, "resize")}
          className="absolute -right-3 -bottom-3 size-6 cursor-nwse-resize rounded-full border-2 border-white bg-primary"
        />
      </div>
    </div>
  );
}

function ResultPreview({ src, state }: { src: string; state: EditState }) {
  const { t } = useTranslation();
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const img = new Image();
    img.onload = () => {
      const c = canvas.current;
      if (!c) return;
      const { x, y, w, h } = state.crop;
      const sw = img.naturalWidth * w;
      const sh = img.naturalHeight * h;
      const turned = state.rotate % 180 !== 0;
      const scale = Math.min(1, 220 / Math.max(sw, sh));
      c.width = Math.round((turned ? sh : sw) * scale);
      c.height = Math.round((turned ? sw : sh) * scale);
      const ctx = c.getContext("2d");
      if (!ctx) return;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, c.width, c.height);
      ctx.translate(c.width / 2, c.height / 2);
      ctx.rotate((state.rotate * Math.PI) / 180);
      ctx.scale(state.flip === "horizontal" ? -1 : 1, state.flip === "vertical" ? -1 : 1);
      ctx.drawImage(img, img.naturalWidth * x, img.naturalHeight * y, sw, sh, (-sw * scale) / 2, (-sh * scale) / 2, sw * scale, sh * scale);
    };
    img.src = src;
  }, [src, state.crop, state.rotate, state.flip]);
  return (
    <figure className="space-y-1">
      <canvas ref={canvas} className="max-w-full rounded-lg border border-border bg-surface-muted" aria-hidden="true" />
      <figcaption className="text-sm text-muted">{t("edit.preview")}</figcaption>
    </figure>
  );
}

interface Props {
  file: File;
  multiple: boolean;
  state: EditState;
  onChange: (state: EditState) => void;
}

export function ImageEditor({ file, multiple, state, onChange }: Props) {
  const { t } = useTranslation();
  const id = useId();
  const [src, setSrc] = useState<string | null>(null);
  const [previewable, setPreviewable] = useState(true);
  const [natural, setNatural] = useState<{ w: number; h: number } | null>(null);

  useEffect(() => {
    let cancelled = false;
    const url = URL.createObjectURL(file);
    setSrc(url);
    setPreviewable(true);
    const probe = new Image();
    // e.g. HEIC outside Safari. Ignore errors from a run that was already cleaned up (revoked URL).
    probe.onerror = () => !cancelled && setPreviewable(false);
    probe.src = url;
    return () => {
      cancelled = true;
      URL.revokeObjectURL(url);
    };
  }, [file]);

  const set = (patch: Partial<EditState>) => onChange({ ...state, ...patch });
  const setAspect = (aspect: Aspect) =>
    set({ aspect, crop: natural && !multiple ? fitBox(aspect, natural.w, natural.h) : FULL });
  const interactive = !multiple && previewable && src;

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <Radio
          legend={t("edit.crop")}
          name={`${id}-aspect`}
          value={state.aspect}
          choices={ASPECTS}
          label={(a) => t(`edit.aspects.${ASPECT_KEY[a]}`)}
          onChange={setAspect}
        />
        {interactive ? (
          <>
            <CropArea
              src={src}
              state={state}
              onBox={(crop) => set({ crop })}
              onSize={(w, h) => setNatural({ w, h })}
            />
            <p className="text-sm text-muted">{t("edit.cropHint")}</p>
          </>
        ) : (
          <p className="text-sm text-muted">{multiple ? t("edit.batchCrop") : t("edit.noPreview")}</p>
        )}
      </div>

      <div className="space-y-2">
        <p className="text-sm font-semibold">{t("edit.turn")}</p>
        <div className="flex flex-wrap gap-2">
          <button type="button" className={btn.secondary} onClick={() => set({ rotate: (((state.rotate + 270) % 360) as EditState["rotate"]) })}>
            <RotateCcw className="size-4" aria-hidden="true" />
            {t("edit.rotateLeft")}
          </button>
          <button type="button" className={btn.secondary} onClick={() => set({ rotate: (((state.rotate + 90) % 360) as EditState["rotate"]) })}>
            <RotateCw className="size-4" aria-hidden="true" />
            {t("edit.rotateRight")}
          </button>
          <button
            type="button"
            aria-pressed={state.flip === "horizontal"}
            className={state.flip === "horizontal" ? btn.primary : btn.secondary}
            onClick={() => set({ flip: state.flip === "horizontal" ? "none" : "horizontal" })}
          >
            <FlipHorizontal2 className="size-4" aria-hidden="true" />
            {t("edit.flipH")}
          </button>
          <button
            type="button"
            aria-pressed={state.flip === "vertical"}
            className={state.flip === "vertical" ? btn.primary : btn.secondary}
            onClick={() => set({ flip: state.flip === "vertical" ? "none" : "vertical" })}
          >
            <FlipVertical2 className="size-4" aria-hidden="true" />
            {t("edit.flipV")}
          </button>
        </div>
        <p className="text-sm text-muted tabular-nums" aria-live="polite">
          {t("edit.rotation", { deg: state.rotate })}
        </p>
      </div>

      {interactive ? <ResultPreview src={src} state={state} /> : null}

      <div className="space-y-3">
        <Radio
          legend={t("edit.resize")}
          name={`${id}-resize`}
          value={state.resize}
          choices={["none", "percent", "pixels"] as const}
          label={(m) => t(`edit.resizeModes.${m}`)}
          onChange={(resize) => set({ resize })}
        />
        {state.resize === "percent" ? (
          <div className="space-y-1">
            <label htmlFor={`${id}-pct`} className="block text-sm font-semibold">
              {t("edit.percent")}
            </label>
            <input
              id={`${id}-pct`}
              type="number"
              inputMode="numeric"
              min={1}
              max={400}
              value={state.percent}
              onChange={(e) => set({ percent: Number(e.target.value) })}
              className="min-h-11 w-32 rounded-xl border border-border-strong bg-surface px-3 text-base tabular-nums"
            />
          </div>
        ) : null}
        {state.resize === "pixels" ? (
          <div className="flex flex-wrap gap-4">
            {(["width", "height"] as const).map((dim) => (
              <div key={dim} className="space-y-1">
                <label htmlFor={`${id}-${dim}`} className="block text-sm font-semibold">
                  {t(`edit.${dim}`)}
                </label>
                <input
                  id={`${id}-${dim}`}
                  type="number"
                  inputMode="numeric"
                  min={1}
                  max={10000}
                  value={state[dim]}
                  onChange={(e) => set({ [dim]: e.target.value } as Partial<EditState>)}
                  className="min-h-11 w-36 rounded-xl border border-border-strong bg-surface px-3 text-base tabular-nums"
                />
              </div>
            ))}
            <p className="w-full text-sm text-muted">{t("edit.pixelsHint")}</p>
          </div>
        ) : null}
      </div>

      <Radio
        legend={t("edit.format")}
        name={`${id}-format`}
        value={state.format}
        choices={["keep", "jpg", "png", "webp"] as const}
        label={(f) => (f === "keep" ? t("edit.keepFormat") : f.toUpperCase())}
        onChange={(format) => set({ format })}
      />
    </div>
  );
}
