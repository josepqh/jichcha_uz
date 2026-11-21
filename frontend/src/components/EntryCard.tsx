import { ArrowUpRight } from "lucide-react";
import type { TFunction } from "i18next";
import { Link } from "react-router";

import { FAMILY_ICON, type CatalogEntry } from "@/lib/catalog";
import { FAMILY_TEXT } from "@/lib/sections";
import type { Family } from "@/lib/tools";

export function entryText(t: TFunction, lang: string, entry: CatalogEntry) {
  const familyName = (family: string) => t(`home.groups.${family}`);
  return entry.kind === "tool"
    ? {
        name: t(`tools.${entry.tool.slug}.name`),
        description: t(`tools.${entry.tool.slug}.description`),
        href: `/${lang}/tools/${entry.tool.slug}`,
      }
    : {
        name: t("catalog.conversionName", { from: familyName(entry.family), to: entry.to.toUpperCase() }),
        description: t("catalog.conversionDescription", { from: familyName(entry.family), to: entry.to.toUpperCase() }),
        href: `/${lang}/convert/${entry.pair}`,
      };
}

/** A tool as a sheet of paper: folded corner, the family's colour on the icon and the format stamp. */
export function EntryCard({
  entry,
  family,
  t,
  lang,
  state,
}: {
  entry: CatalogEntry;
  family: Family;
  t: TFunction;
  lang: string;
  state?: unknown;
}) {
  const { name, description, href } = entryText(t, lang, entry);
  const Icon = entry.kind === "tool" ? entry.tool.icon : FAMILY_ICON[entry.family];
  const stamp = entry.kind === "conversion" ? `${entry.pair.split("-to-")[0]} → ${entry.to}` : null;
  return (
    <Link
      to={href}
      state={state}
      data-card
      className="sheet group relative flex h-full flex-col gap-4 rounded-2xl rounded-se-none border border-border bg-surface p-5 transition-[transform,box-shadow,border-color] duration-200 ease-[var(--ease-out-soft)] hover:-translate-y-0.5 hover:border-border-strong hover:shadow-lift"
    >
      <span className="flex items-center gap-3">
        <span
          className={`grid size-10 place-items-center rounded-xl border border-current/20 bg-current/[0.06] ${FAMILY_TEXT[family]}`}
          aria-hidden="true"
        >
          <Icon className="size-5" strokeWidth={1.75} />
        </span>
        {stamp ? (
          <span className={`font-mono text-xs font-medium tracking-wide uppercase ${FAMILY_TEXT[family]}`}>{stamp}</span>
        ) : null}
      </span>
      <span className="space-y-1.5">
        <span className="block text-lg leading-snug font-semibold">{name}</span>
        <span className="block text-sm text-pretty text-muted">{description}</span>
      </span>
      <ArrowUpRight
        className="mt-auto size-5 text-muted transition-transform duration-200 ease-[var(--ease-out-soft)] group-hover:translate-x-0.5 group-hover:-translate-y-0.5 rtl:-scale-x-100 rtl:group-hover:-translate-x-0.5 group-hover:text-fg"
        aria-hidden="true"
      />
    </Link>
  );
}
