import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ChevronRight } from "lucide-react";
import { useRef } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { EntryCard } from "@/components/EntryCard";
import { useDisabledTools } from "@/hooks/useApi";
import { useLang } from "@/hooks/useLang";
import { FAMILY_FORMATS } from "@/lib/catalog";
import { FAMILY_TEXT, sectionEntries } from "@/lib/sections";
import type { Family } from "@/lib/tools";

gsap.registerPlugin(useGSAP);

/** One file family: only its own tools, nothing from other sections. */
export function SectionPage({ family }: { family: Family }) {
  const { t } = useTranslation();
  const lang = useLang();
  const disabled = useDisabledTools();
  const scope = useRef<HTMLDivElement>(null);
  const entries = sectionEntries(family).filter((entry) => !disabled.has(entry.tool.slug));
  const name = t(`home.groups.${family}`);

  // Cards deal in when the section changes (navigation, not scroll); at rest under reduced motion.
  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(prefers-reduced-motion: no-preference)", () => {
        gsap.from("[data-card]", { y: 14, autoAlpha: 0, duration: 0.45, ease: "power3.out", stagger: 0.045, clearProps: "all" });
        gsap.from("[data-title]", { y: 10, autoAlpha: 0, duration: 0.4, ease: "power3.out", clearProps: "all" });
      });
    },
    { dependencies: [family], scope, revertOnUpdate: true },
  );

  return (
    <div ref={scope} className="space-y-10">
      <title>{`${name} | ${t("meta.siteName")}`}</title>
      <meta name="description" content={t(`sections.${family}.lead`)} />
      <nav aria-label={t("sections.breadcrumb")} className="-mt-4 text-sm text-muted">
        <ol className="flex items-center gap-1">
          <li>
            <Link to={`/${lang}`} className="inline-flex min-h-11 items-center underline-offset-4 hover:text-fg hover:underline">
              {t("sections.home")}
            </Link>
          </li>
          <li aria-hidden="true">
            <ChevronRight className="size-4 rtl:-scale-x-100" />
          </li>
          <li aria-current="page" className="font-medium text-fg">
            {name}
          </li>
        </ol>
      </nav>

      <header data-title className="grid gap-6 border-b border-border pb-10 md:grid-cols-[1fr_auto] md:items-end">
        <div className="space-y-4">
          <h1 className="font-display text-4xl font-medium tracking-[-0.045em] sm:text-6xl">{name}</h1>
          <p className="max-w-xl text-lg text-pretty text-muted">{t(`sections.${family}.lead`)}</p>
        </div>
        <div className="space-y-2">
          <p className="font-mono text-xs tracking-wide text-muted uppercase">{t("sections.formats")}</p>
          <ul className={`flex max-w-xs flex-wrap gap-1.5 ${FAMILY_TEXT[family]}`}>
            {FAMILY_FORMATS[family].map((format) => (
              <li
                key={format}
                className="rounded-md border border-current/30 px-1.5 py-0.5 font-mono text-xs font-medium tracking-wide uppercase"
              >
                .{format}
              </li>
            ))}
          </ul>
        </div>
      </header>

      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {entries.map((entry) => (
          <li key={entry.key}>
            <EntryCard entry={entry} family={family} t={t} lang={lang} />
          </li>
        ))}
      </ul>
    </div>
  );
}
