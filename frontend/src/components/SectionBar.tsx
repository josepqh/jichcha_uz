import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation } from "react-router";

import { useLang } from "@/hooks/useLang";
import { FAMILY_BG, familyForPath, SECTION_SLUG, SECTIONS } from "@/lib/sections";

gsap.registerPlugin(useGSAP);

/**
 * The section bar under the header: one tab per file family. The active tab carries the brand's
 * highlighter stroke, which slides to the new tab on navigation (and simply jumps under reduced motion).
 */
export function SectionBar() {
  const { t } = useTranslation();
  const lang = useLang();
  const { pathname } = useLocation();
  const active = familyForPath(pathname.replace(/^\/[a-z]{2}(?=\/|$)/, ""));
  const listRef = useRef<HTMLUListElement>(null);
  const markRef = useRef<HTMLLIElement>(null);
  const placed = useRef(false);

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

  return (
    <nav aria-label={t("sections.label")} className="border-t border-border">
      <div className="mx-auto max-w-6xl">
        <ul ref={listRef} className="edge-fade relative flex items-center gap-1 overflow-x-auto px-4 [scrollbar-width:none]">
          <li
            ref={markRef}
            aria-hidden="true"
            className="pointer-events-none invisible absolute top-[calc(50%-0.875rem)] left-0 h-7 rounded-[0.35rem_0.7rem_0.4rem_0.8rem] bg-accent"
          />
          {SECTIONS.map((family) => {
            const current = family === active;
            return (
              <li key={family} className="relative shrink-0" data-family={family}>
                <Link
                  to={`/${lang}/${SECTION_SLUG[family]}`}
                  aria-current={current ? "page" : undefined}
                  className={`group inline-flex min-h-12 items-center gap-2 px-3 text-sm font-medium transition-colors duration-150 ${
                    current ? "text-accent-fg" : "text-muted hover:text-fg"
                  }`}
                >
                  <span
                    aria-hidden="true"
                    className={`size-2 rounded-[2px] ${FAMILY_BG[family]} transition-transform duration-200 group-hover:scale-125`}
                  />
                  <span data-label className="relative">
                    {t(`home.groups.${family}`)}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </nav>
  );
}
