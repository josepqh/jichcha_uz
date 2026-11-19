import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ArrowUpRight, Search } from "lucide-react";
import { useDeferredValue, useRef, useState } from "react";
import { Trans, useTranslation } from "react-i18next";
import { Link } from "react-router";

import { EntryCard, entryText } from "@/components/EntryCard";
import { SmartDrop } from "@/components/SmartDrop";
import { useDisabledTools } from "@/hooks/useApi";
import { useLang } from "@/hooks/useLang";
import { FAMILY_FORMATS } from "@/lib/catalog";
import { FAMILY_TEXT, SECTION_SLUG, SECTIONS, sectionEntries } from "@/lib/sections";
import { POPULAR_CONVERSIONS, resolveConversion, type Family } from "@/lib/tools";

gsap.registerPlugin(useGSAP);

const BENEFITS = ["free", "deleted", "gps"] as const;

/** The fold's colour on each section folder. */
const FOLD: Record<Family, string> = {
  pdf: "[--fold:var(--fam-pdf)]",
  word: "[--fold:var(--fam-word)]",
  excel: "[--fold:var(--fam-excel)]",
  powerpoint: "[--fold:var(--fam-powerpoint)]",
  image: "[--fold:var(--fam-image)]",
  archive: "[--fold:var(--fam-archive)]",
};

function matches(haystack: string, query: string): boolean {
  const tokens = query.toLowerCase().split(/\s+/).filter(Boolean);
  const text = haystack.toLowerCase();
  return tokens.every((token) => text.includes(token));
}

export function HomePage() {
  const { t } = useTranslation();
  const lang = useLang();
  const [query, setQuery] = useState("");
  const deferred = useDeferredValue(query.trim());
  const disabled = useDisabledTools();
  const hero = useRef<HTMLDivElement>(null);

  // The hero enters once: the lines rise, then the highlighter stroke is drawn under the key word.
  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(prefers-reduced-motion: no-preference)", () => {
        gsap
          .timeline({ defaults: { ease: "power3.out" } })
          .from("[data-rise]", { y: 18, autoAlpha: 0, duration: 0.6, stagger: 0.08, clearProps: "all" })
          .fromTo(".hl", { "--hl": 0 }, { "--hl": 1, duration: 0.55, ease: "expo.inOut" }, 0.35);
      });
    },
    { scope: hero },
  );

  const sections = SECTIONS.map((family) => ({
    family,
    entries: sectionEntries(family).filter((entry) => !disabled.has(entry.tool.slug)),
  }));
  const results = deferred
    ? sections.flatMap(({ family, entries }) =>
        entries
          .filter((entry) => {
            const { name, description } = entryText(t, lang, entry);
            return matches(`${entry.key} ${t(`home.groups.${family}`)} ${name} ${description}`, deferred);
          })
          .map((entry) => ({ family, entry })),
      )
    : [];
  const conversions = POPULAR_CONVERSIONS.map((pair) => resolveConversion(pair)!);

  return (
    <div className="space-y-20 sm:space-y-28">
      <title>{t("meta.homeTitle")}</title>
      <meta name="description" content={t("meta.homeDescription")} />

      <section ref={hero} className="grid items-start gap-10 lg:grid-cols-[1.15fr_1fr] lg:gap-14">
        <div className="space-y-7 lg:pt-6">
          <h1
            data-rise
            className="font-display text-[2.15rem] leading-[1.08] font-medium tracking-[-0.05em] sm:text-5xl lg:text-[3.6rem]"
          >
            <Trans i18nKey="home.title" components={{ hl: <span className="hl" /> }} />
          </h1>
          <p data-rise className="max-w-lg text-lg text-pretty text-muted">
            {t("home.subtitle")}
          </p>
          <div data-rise className="relative max-w-lg">
            <label htmlFor="tool-search" className="sr-only">
              {t("home.searchLabel")}
            </label>
            <Search className="pointer-events-none absolute top-1/2 left-4 size-5 -translate-y-1/2 text-muted" aria-hidden="true" />
            <input
              id="tool-search"
              type="search"
              name="q"
              spellCheck={false}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t("home.searchPlaceholder")}
              autoComplete="off"
              className="min-h-14 w-full rounded-2xl border border-border-strong bg-surface py-2 pr-4 pl-12 text-base transition-[border-color,box-shadow] duration-150 placeholder:text-muted focus:border-fg focus:shadow-lift"
            />
          </div>
        </div>
        <div data-rise>
          <SmartDrop />
        </div>
      </section>

      {deferred ? (
        <section aria-labelledby="results-heading" className="space-y-5">
          <h2 id="results-heading" className="font-display text-2xl font-medium tracking-[-0.04em]">
            {t("home.toolsHeading")}
          </h2>
          {results.length ? (
            <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {results.map(({ family, entry }) => (
                <li key={`${family}-${entry.key}`}>
                  <EntryCard entry={entry} family={family} t={t} lang={lang} />
                </li>
              ))}
            </ul>
          ) : (
            <p role="status" className="text-muted">
              {t("home.noResults", { query: deferred })}
            </p>
          )}
        </section>
      ) : (
        <section aria-labelledby="sections-heading" className="space-y-6">
          <h2 id="sections-heading" className="font-display text-2xl font-medium tracking-[-0.04em] sm:text-3xl">
            {t("home.sectionsHeading")}
          </h2>
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {sections.map(({ family, entries }) => {
              const name = t(`home.groups.${family}`);
              return (
                <li key={family}>
                  <Link
                    to={`/${lang}/${SECTION_SLUG[family]}`}
                    className={`sheet group relative flex h-full flex-col gap-6 rounded-2xl rounded-tr-none border border-border bg-surface p-6 transition-[transform,box-shadow,border-color] duration-200 ease-[var(--ease-out-soft)] hover:-translate-y-0.5 hover:border-border-strong hover:shadow-lift ${FOLD[family]}`}
                  >
                    <span className={`font-mono text-xs font-medium tracking-wide uppercase ${FAMILY_TEXT[family]}`}>
                      {FAMILY_FORMATS[family].slice(0, 5).map((f) => `.${f}`).join("  ")}
                    </span>
                    <span className="space-y-1">
                      <span className="block font-display text-2xl font-medium tracking-[-0.04em]">{name}</span>
                      <span className="block text-sm text-muted tabular-nums">{t("home.toolCount", { count: entries.length })}</span>
                    </span>
                    <span className="mt-auto flex items-end justify-between gap-4">
                      <span className="text-sm text-pretty text-muted">
                        {entries
                          .slice(0, 3)
                          .map((entry) => entryText(t, lang, entry).name)
                          .join(" · ")}
                      </span>
                      <ArrowUpRight
                        className="size-5 shrink-0 text-muted transition-transform duration-200 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-fg"
                        aria-hidden="true"
                      />
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      <section aria-labelledby="popular-heading" className="space-y-5">
        <h2 id="popular-heading" className="font-display text-2xl font-medium tracking-[-0.04em]">
          {t("home.popularHeading")}
        </h2>
        <ul className="flex flex-wrap gap-2">
          {conversions.map((c) => (
            <li key={c.pair}>
              <Link
                to={`/${lang}/convert/${c.pair}`}
                aria-label={t("conversion.short", { from: c.from.toUpperCase(), to: c.to.toUpperCase() })}
                className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-border bg-surface px-3.5 font-mono text-sm font-medium tracking-wide uppercase transition-[border-color,background-color,transform] duration-150 hover:border-fg hover:bg-accent hover:text-accent-fg active:scale-[0.97]"
              >
                {c.from}
                <span aria-hidden="true" className="text-muted">
                  →
                </span>
                {c.to}
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="benefits-heading" className="grid gap-10 border-t border-border pt-12 lg:grid-cols-[1fr_2fr]">
        <h2 id="benefits-heading" className="font-display text-2xl font-medium tracking-[-0.04em] sm:text-3xl">
          {t("home.benefitsHeading")}
        </h2>
        <ol className="divide-y divide-border">
          {BENEFITS.map((key, i) => (
            <li key={key} className="grid gap-2 py-5 first:pt-0 sm:grid-cols-[3rem_1fr]">
              <span className="font-mono text-sm text-muted tabular-nums" aria-hidden="true">
                0{i + 1}
              </span>
              <span className="space-y-1">
                <span className="block font-semibold">{t(`home.benefits.${key}.title`)}</span>
                <span className="block text-pretty text-muted">{t(`home.benefits.${key}.text`)}</span>
              </span>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
