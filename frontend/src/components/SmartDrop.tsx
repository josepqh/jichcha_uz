import { ArrowRight, FileUp, RotateCcw } from "lucide-react";
import { useId, useRef, useState, type DragEvent } from "react";
import { Trans, useTranslation } from "react-i18next";
import { Link } from "react-router";

import { entryText } from "@/components/EntryCard";
import { useDisabledTools } from "@/hooks/useApi";
import { useLang } from "@/hooks/useLang";
import { familyOf } from "@/lib/catalog";
import { FAMILY_BG, FAMILY_TEXT, formatOf, sectionEntries } from "@/lib/sections";
import type { Family } from "@/lib/tools";
import { btn } from "@/lib/ui";

interface Picked {
  file: File;
  format: string;
  family: Family | undefined;
}

/**
 * "Drop any file": works out the family from the name and offers that family's actions, without
 * uploading anything. The chosen tool page receives the File itself through router state (history
 * state is structured-cloned, so a File survives), so nothing is picked twice.
 */
export function SmartDrop() {
  const { t } = useTranslation();
  const lang = useLang();
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const disabled = useDisabledTools();
  const [over, setOver] = useState(false);
  const [picked, setPicked] = useState<Picked | null>(null);

  const take = (file: File | undefined) => {
    if (!file) return;
    const format = formatOf(file.name);
    setPicked({ file, format, family: familyOf(format) });
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setOver(false);
    take(e.dataTransfer.files[0]);
  };

  const actions = picked?.family
    ? sectionEntries(picked.family).filter(
        (entry) =>
          !disabled.has(entry.tool.slug) &&
          (entry.tool.inputs.length === 0 || entry.tool.inputs.includes(picked.format)) &&
          (entry.kind === "tool" || entry.to !== picked.format),
      )
    : [];

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={onDrop}
      className={`paper-grid relative flex min-h-72 flex-col justify-between gap-5 rounded-3xl border-2 border-dashed p-5 transition-[border-color,background-color] duration-200 sm:p-6 ${
        over ? "border-fg bg-accent/25" : "border-border-strong bg-surface"
      }`}
    >
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        className="sr-only"
        tabIndex={-1}
        aria-label={t("drop.choose")}
        onChange={(e) => {
          take(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
      {picked ? (
        <div className="space-y-4" aria-live="polite">
          <p className="text-pretty">
            {picked.family ? (
              <Trans
                i18nKey="drop.detected"
                values={{ name: picked.file.name, family: t(`home.groups.${picked.family}`) }}
                components={{ name: <span className="font-semibold [overflow-wrap:anywhere]" /> }}
              />
            ) : (
              t("drop.unknown", { name: picked.file.name })
            )}
          </p>
          {actions.length ? (
            <ul className="grid gap-2">
              {actions.map((entry) => {
                const { name, href } = entryText(t, lang, entry);
                return (
                  <li key={entry.key}>
                    <Link
                      to={href}
                      state={{ from: { file: picked.file, name: picked.file.name } }}
                      className="group flex min-h-12 items-center gap-3 rounded-xl border border-border bg-bg px-4 font-medium transition-[border-color,transform] duration-150 hover:border-fg active:scale-[0.99]"
                    >
                      <span aria-hidden="true" className={`size-2 rounded-[2px] ${FAMILY_BG[picked.family!]}`} />
                      <span className="flex-1">{name}</span>
                      <ArrowRight
                        className="size-4 text-muted transition-transform duration-200 group-hover:translate-x-1 group-hover:text-fg"
                        aria-hidden="true"
                      />
                    </Link>
                  </li>
                );
              })}
            </ul>
          ) : null}
          <button type="button" className={btn.ghost} onClick={() => inputRef.current?.click()}>
            <RotateCcw className="size-4" aria-hidden="true" />
            {t("drop.another")}
          </button>
        </div>
      ) : (
        <>
          <div className="space-y-2">
            <p className="font-display text-xl font-medium tracking-[-0.03em]">{t("drop.title")}</p>
            <p className="text-sm text-pretty text-muted">{t("drop.text")}</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button type="button" className={`${btn.primary} min-h-12 px-5`} onClick={() => inputRef.current?.click()}>
              <FileUp className="size-4" aria-hidden="true" />
              {t("drop.choose")}
            </button>
            <span className="font-mono text-xs tracking-wide text-muted uppercase" aria-hidden="true">
              <span className={FAMILY_TEXT.pdf}>pdf</span> · <span className={FAMILY_TEXT.word}>docx</span> ·{" "}
              <span className={FAMILY_TEXT.excel}>xlsx</span> · <span className={FAMILY_TEXT.image}>heic</span> ·{" "}
              <span className={FAMILY_TEXT.archive}>rar</span>
            </span>
          </div>
        </>
      )}
    </div>
  );
}
