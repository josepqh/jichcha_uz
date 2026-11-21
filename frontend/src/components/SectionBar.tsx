import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ChevronDown } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation } from "react-router";

import { entryText } from "@/components/EntryCard";
import { FamilyIcon } from "@/components/FamilyIcon";
import { useDisabledTools } from "@/hooks/useApi";
import { useLang } from "@/hooks/useLang";
import { FAMILY_ICON, type CatalogEntry } from "@/lib/catalog";
import { FAMILY_TEXT, familyForPath, menuGroups, SECTIONS } from "@/lib/sections";
import type { Family } from "@/lib/tools";

gsap.registerPlugin(useGSAP);

function MenuItem({ entry, family, onPick }: { entry: CatalogEntry; family: Family; onPick: () => void }) {
  const { t } = useTranslation();
  const lang = useLang();
  const { name, href } = entryText(t, lang, entry);
  const Icon = entry.kind === "tool" ? entry.tool.icon : FAMILY_ICON[entry.family];
  return (
    <li>
      <Link
        to={href}
        onClick={onPick}
        data-menu-link
        className="group flex min-h-11 items-center gap-3 rounded-xl px-2.5 py-1.5 text-sm font-medium transition-colors duration-150 hover:bg-surface-muted"
      >
        <span
          className={`grid size-8 shrink-0 place-items-center rounded-lg border border-current/20 bg-current/[0.06] ${FAMILY_TEXT[family]}`}
          aria-hidden="true"
        >
          <Icon className="size-4" strokeWidth={1.75} />
        </span>
        <span className="flex-1">{name}</span>
      </Link>
    </li>
  );
}

function MenuPanel({ family, id, onPick }: { family: Family; id: string; onPick: () => void }) {
  const { t } = useTranslation();
  const hidden = useDisabledTools();
  const groups = menuGroups(family, hidden);
  // Converting first (into this format, then out of it), then the kinds of work on it.
  const columns = [
    { key: "into", label: t("menu.into"), items: groups.into },
    { key: "from", label: t("menu.from"), items: groups.from.map((entry) => ({ entry, family })) },
    ...groups.work.map((g) => ({
      key: g.group,
      label: t(`menu.${g.group}`),
      items: g.entries.map((entry) => ({ entry, family })),
    })),
  ].filter((column) => column.items.length);

  return (
    <div id={id} className="absolute inset-x-0 top-full z-30 border-y border-border bg-bg shadow-lift">
      <div className="mx-auto grid max-h-[min(70vh,36rem)] max-w-6xl gap-x-6 gap-y-8 overflow-y-auto px-4 py-6 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-6">
        {columns.map((column) => (
          // Group titles are labels, not headings: the panel sits before the page's h1.
          <div key={column.key} className="space-y-2">
            <p id={`${id}-${column.key}`} className="px-2.5 font-mono text-xs font-medium tracking-wide text-muted uppercase">
              {column.label}
            </p>
            <ul aria-labelledby={`${id}-${column.key}`} className="space-y-0.5">
              {column.items.map(({ entry, family: from }) => (
                <MenuItem key={`${from}-${entry.key}`} entry={entry} family={from} onPick={onPick} />
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * The section bar under the header: one tab per file family. A tab opens a panel with that
 * section's tools in groups (work on it, convert from it, convert into it). The tab of the page's
 * own section carries the brand's highlighter stroke, which slides there on navigation.
 */
export function SectionBar() {
  const { t } = useTranslation();
  const lang = useLang();
  const { pathname } = useLocation();
  const active = familyForPath(pathname.replace(/^\/[a-z]{2}(?=\/|$)/, ""));
  const navRef = useRef<HTMLElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const markRef = useRef<HTMLLIElement>(null);
  const placed = useRef(false);
  const panelId = useId();
  // The panel belongs to the page it was opened on: navigating anywhere closes it.
  const [menu, setMenu] = useState<{ family: Family; path: string } | null>(null);
  const open = menu && menu.path === pathname ? menu.family : null;
  const close = () => setMenu(null);

  // Where the mark goes: behind the label text, a little wider, like a stroke of a highlighter.
  const markVars = (target: HTMLElement) => {
    const label = target.querySelector<HTMLElement>("[data-label]") ?? target;
    return { x: target.offsetLeft + label.offsetLeft - 6, width: label.offsetWidth + 12, autoAlpha: 1 };
  };
  const targetFor = () =>
    active ? (listRef.current?.querySelector<HTMLElement>(`[data-family="${active}"]`) ?? null) : null;

  useGSAP(
    () => {
      const mark = markRef.current;
      const target = targetFor();
      if (!mark) return;
      if (!target) {
        gsap.to(mark, { autoAlpha: 0, duration: 0.15, overwrite: true });
        placed.current = false;
        return;
      }
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (placed.current && !reduce) gsap.to(mark, { ...markVars(target), duration: 0.45, ease: "expo.out", overwrite: true });
      else gsap.set(mark, { ...markVars(target), overwrite: true });
      placed.current = true;
      target.scrollIntoView({ block: "nearest", inline: "nearest" });
    },
    { dependencies: [active, lang], scope: listRef },
  );

  // Web fonts and window resizes change label widths: keep the mark on its label.
  useEffect(() => {
    const target = targetFor();
    if (!target) return;
    let first = true; // the observer fires once on observe; that would cut the slide short
    const observer = new ResizeObserver(() => {
      if (first) {
        first = false;
        return;
      }
      if (markRef.current) gsap.set(markRef.current, { ...markVars(target), overwrite: true });
    });
    observer.observe(target);
    return () => observer.disconnect();
    // oxlint-disable-next-line react/exhaustive-deps
  }, [active, lang]);

  // An open panel: focus its first link, close on Escape (back to its tab) or a click elsewhere.
  useEffect(() => {
    if (!open) return;
    const nav = navRef.current;
    nav?.querySelector<HTMLElement>(`[id="${panelId}"] [data-menu-link]`)?.focus({ preventScroll: true });
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      setMenu(null);
      nav?.querySelector<HTMLElement>(`[data-family="${open}"] button`)?.focus();
    };
    const onPointer = (e: PointerEvent) => {
      if (!nav?.contains(e.target as Node)) setMenu(null);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, [open, panelId]);

  return (
    <nav ref={navRef} aria-label={t("sections.label")} className="min-w-0">
      <div>
        <ul ref={listRef} className="edge-fade relative flex items-center gap-0.5 overflow-x-auto [scrollbar-width:none]">
          <li
            ref={markRef}
            aria-hidden="true"
            className="pointer-events-none invisible absolute top-[calc(50%-0.875rem)] left-0 h-7 rounded-[0.35rem_0.7rem_0.4rem_0.8rem] bg-accent"
          />
          {SECTIONS.map((family) => {
            const current = family === active;
            const expanded = family === open;
            return (
              <li key={family} className="relative shrink-0" data-family={family}>
                <button
                  type="button"
                  aria-expanded={expanded}
                  aria-controls={expanded ? panelId : undefined}
                  aria-current={current ? "page" : undefined}
                  onClick={() => setMenu(expanded ? null : { family, path: pathname })}
                  className={`group inline-flex min-h-11 cursor-pointer items-center gap-1.5 px-2.5 text-sm font-medium transition-colors duration-150 ${
                    current ? "text-accent-fg" : expanded ? "text-fg" : "text-muted hover:text-fg"
                  }`}
                >
                  <FamilyIcon family={family} className="size-5 transition-transform duration-200 group-hover:-translate-y-0.5" />
                  <span data-label className="relative">
                    {t(`home.groups.${family}`)}
                  </span>
                  <ChevronDown
                    className={`size-3.5 opacity-60 transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}
                    aria-hidden="true"
                  />
                </button>
              </li>
            );
          })}
        </ul>
      </div>
      {open ? <MenuPanel family={open} id={panelId} onPick={close} /> : null}
    </nav>
  );
}
