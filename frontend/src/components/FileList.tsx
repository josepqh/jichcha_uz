import { ArrowDown, ArrowUp, FileImage, X } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { formatBytes } from "@/lib/format";
import { btn } from "@/lib/ui";

export interface PickedFile {
  id: string;
  file: File;
  preview: string;
}

interface Props {
  items: PickedFile[];
  reorder: boolean;
  disabled: boolean;
  onRemove: (id: string) => void;
  onMove: (id: string, delta: -1 | 1) => void;
  labelledBy?: string;
}

function Thumb({ src }: { src: string }) {
  const [broken, setBroken] = useState(false);
  if (broken) {
    return (
      <span className="flex size-12 shrink-0 items-center justify-center rounded-lg bg-surface-muted">
        <FileImage className="size-6 text-muted" aria-hidden="true" />
      </span>
    );
  }
  return (
    <img
      src={src}
      alt=""
      width={48}
      height={48}
      loading="lazy"
      onError={() => setBroken(true)} // e.g. HEIC, which most browsers can't render
      className="size-12 shrink-0 rounded-lg bg-surface-muted object-cover"
    />
  );
}

export function FileList({ items, reorder, disabled, onRemove, onMove, labelledBy }: Props) {
  const { t, i18n } = useTranslation();
  return (
    <ol className="divide-y divide-border" aria-labelledby={labelledBy}>
      {items.map((item, index) => (
        <li key={item.id} className="flex items-center gap-3 py-2">
          <Thumb src={item.preview} />
          <div className="min-w-0 flex-1">
            <p className="line-clamp-2 font-medium [overflow-wrap:anywhere]" title={item.file.name}>
              {item.file.name}
            </p>
            <p className="text-sm text-muted tabular-nums">{formatBytes(item.file.size, i18n.language)}</p>
          </div>
          {reorder ? (
            <>
              <button
                type="button"
                className={btn.icon}
                disabled={disabled || index === 0}
                onClick={() => onMove(item.id, -1)}
                aria-label={t("upload.moveUp", { name: item.file.name })}
              >
                <ArrowUp className="size-5" aria-hidden="true" />
              </button>
              <button
                type="button"
                className={btn.icon}
                disabled={disabled || index === items.length - 1}
                onClick={() => onMove(item.id, 1)}
                aria-label={t("upload.moveDown", { name: item.file.name })}
              >
                <ArrowDown className="size-5" aria-hidden="true" />
              </button>
            </>
          ) : null}
          <button
            type="button"
            className={btn.icon}
            disabled={disabled}
            onClick={() => onRemove(item.id)}
            aria-label={t("upload.remove", { name: item.file.name })}
          >
            <X className="size-5" aria-hidden="true" />
          </button>
        </li>
      ))}
    </ol>
  );
}
