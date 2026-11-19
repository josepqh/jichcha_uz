import { Upload } from "lucide-react";
import { useRef, useState, type DragEvent } from "react";
import { useTranslation } from "react-i18next";

import { btn } from "@/lib/ui";

interface Props {
  accept: string;
  multiple?: boolean;
  disabled?: boolean;
  compact?: boolean;
  hint?: string;
  onFiles: (files: File[]) => void;
}

export function Dropzone({ accept, multiple = true, disabled = false, compact = false, hint, onFiles }: Props) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    if (disabled) return;
    const files = Array.from(e.dataTransfer.files);
    if (files.length) onFiles(multiple ? files : files.slice(0, 1));
  };

  const picker = (
    <>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        hidden
        data-testid="file-input"
        onChange={(e) => {
          const files = Array.from(e.target.files ?? []);
          e.target.value = ""; // allow picking the same file again
          if (files.length) onFiles(files);
        }}
      />
      <button
        type="button"
        className={compact ? btn.secondary : btn.primary}
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
      >
        <Upload className="size-4" aria-hidden="true" />
        {compact ? t("upload.addMore") : t("upload.choose")}
      </button>
    </>
  );

  if (compact) return picker;

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`paper-grid flex flex-col items-center justify-center gap-3 rounded-3xl border-2 border-dashed px-6 py-12 text-center transition-[border-color,background-color] duration-200 sm:py-16 ${
        dragging ? "border-fg bg-accent/25" : "border-border-strong bg-surface"
      }`}
    >
      <Upload className="size-10 text-muted" aria-hidden="true" />
      <p className="font-display text-xl font-medium tracking-[-0.03em]">{t("upload.drop")}</p>
      <p className="text-sm text-muted">{t("upload.or")}</p>
      {picker}
      {hint ? <p className="max-w-sm text-sm text-muted">{hint}</p> : null}
    </div>
  );
}
