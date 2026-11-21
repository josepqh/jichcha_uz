import { Check, ChevronDown, Globe } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation } from "react-router";

import { useLang } from "@/hooks/useLang";
import { directionOf, LANGUAGE_NAMES, LANGUAGES } from "@/i18n";

/**
 * Globe button that opens the list of languages (13 of them no longer fit as buttons). A disclosure
 * of links: each one is the same page in that language, so it also works without JavaScript after
 * prerendering, and screen readers hear "Language, collapsed/expanded".
 */
export function LanguageMenu() {
  const { t } = useTranslation();
  const lang = useLang();
  const { pathname, search } = useLocation();
  const rest = pathname.replace(/^\/[a-z]{2}(?=\/|$)/, "");
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const listId = useId();

  // Close on choosing, outside click and Escape (focus goes back to the button).
  useEffect(() => {
    if (!open) return;
    const onPointer = (e: PointerEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    // Escape closes; arrows, Home and End move through the list.
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        buttonRef.current?.focus();
        return;
      }
      if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)) return;
      const links = [...(rootRef.current?.querySelectorAll<HTMLElement>("[data-lang-link]") ?? [])];
      const at = links.indexOf(document.activeElement as HTMLElement);
      const step = e.key === "ArrowDown" ? 1 : -1;
      const next = e.key === "Home" ? 0 : e.key === "End" ? links.length - 1 : (at + step + links.length) % links.length;
      e.preventDefault();
      links[next]?.focus();
    };
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    rootRef.current?.querySelector<HTMLElement>('[aria-current="true"]')?.focus();
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative">
      <button
        ref={buttonRef}
        type="button"
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => setOpen((v) => !v)}
        className="inline-flex min-h-11 cursor-pointer items-center gap-1.5 rounded-xl px-2.5 text-sm font-medium text-fg transition-[background-color,transform] duration-150 hover:bg-surface-muted active:scale-[0.97]"
      >
        <Globe className="size-5" aria-hidden="true" />
        <span className="sr-only">{t("nav.language")}: </span>
        <span className="font-mono text-xs uppercase" aria-hidden="true">
          {lang}
        </span>
        <span className="sr-only">{LANGUAGE_NAMES[lang]}</span>
        <ChevronDown
          className={`size-4 text-muted transition-transform duration-200 ${open ? "rotate-180" : ""}`}
          aria-hidden="true"
        />
      </button>
      <ul
        id={listId}
        hidden={!open}
        className="absolute end-0 top-full z-40 mt-2 max-h-[min(70vh,32rem)] w-56 overflow-y-auto rounded-2xl border border-border bg-surface p-1.5 shadow-lift"
      >
        {LANGUAGES.map((code) => {
          const current = code === lang;
          return (
            <li key={code}>
              <Link
                to={`/${code}${rest}${search}`}
                data-lang-link
                lang={code}
                hrefLang={code}
                aria-current={current ? "true" : undefined}
                onClick={() => setOpen(false)}
                className={`flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm transition-colors duration-150 ${
                  current ? "bg-accent font-semibold text-accent-fg" : "text-fg hover:bg-surface-muted"
                }`}
              >
                <span className="w-6 font-mono text-xs text-current/70 uppercase" aria-hidden="true">
                  {code}
                </span>
                <span className="flex-1 text-start" dir={directionOf(code)}>
                  {LANGUAGE_NAMES[code]}
                </span>
                {current ? <Check className="size-4" aria-hidden="true" /> : null}
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
