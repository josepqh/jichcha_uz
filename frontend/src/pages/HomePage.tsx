import { ArrowRight, Gift, MapPinOff, Search, ShieldCheck } from "lucide-react";
import { useDeferredValue, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { useLang } from "@/hooks/useLang";
import { CATEGORY_COLOR, GROUPS, POPULAR_CONVERSIONS, resolveConversion, TOOL_LIST } from "@/lib/tools";
import { card } from "@/lib/ui";

const BENEFITS = [
  { key: "free", icon: Gift },
  { key: "deleted", icon: ShieldCheck },
  { key: "gps", icon: MapPinOff },
] as const;

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

  const tools = TOOL_LIST.filter((tool) =>
    matches(`${tool.slug} ${t(`tools.${tool.slug}.name`)} ${t(`tools.${tool.slug}.description`)}`, deferred),
  );
  const conversions = POPULAR_CONVERSIONS.map((pair) => resolveConversion(pair)!).filter((c) =>
    matches(`${c.from} ${c.to} ${c.pair}`, deferred),
  );
  const nothing = deferred !== "" && tools.length === 0 && conversions.length === 0;

  return (
    <div className="space-y-12">
      <title>{t("meta.homeTitle")}</title>
      <meta name="description" content={t("meta.homeDescription")} />

      <section className="mx-auto max-w-2xl space-y-4 text-center">
        <h1 className="text-3xl font-bold tracking-tight text-balance sm:text-5xl">{t("home.title")}</h1>
        <p className="text-lg text-muted text-pretty">{t("home.subtitle")}</p>
        <div className="relative mx-auto max-w-md pt-2">
          <label htmlFor="tool-search" className="sr-only">
            {t("home.searchLabel")}
          </label>
          <Search className="pointer-events-none absolute top-1/2 left-3 mt-1 size-5 -translate-y-1/2 text-muted" aria-hidden="true" />
          <input
            id="tool-search"
            type="search"
            name="q"
            spellCheck={false}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("home.searchPlaceholder")}
            autoComplete="off"
            className="min-h-12 w-full rounded-xl border border-border-strong bg-surface py-2 pr-4 pl-10 text-base placeholder:text-muted"
          />
        </div>
      </section>

      {nothing ? (
        <p role="status" className="text-center text-muted">
          {t("home.noResults", { query: deferred })}
        </p>
      ) : null}

      {GROUPS.map((group) => {
        const inGroup = tools.filter((tool) => tool.group === group);
        if (!inGroup.length) return null;
        return (
          <section key={group} aria-labelledby={`group-${group}`} className="space-y-4">
            <h2 id={`group-${group}`} className="text-xl font-semibold">
              {t(`home.groups.${group}`)}
            </h2>
            <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {inGroup.map((tool) => (
                <li key={tool.slug}>
                  <Link
                    to={`/${lang}/tools/${tool.slug}`}
                    className={`${card} group flex h-full flex-col gap-3 p-5 transition-colors duration-150 hover:border-border-strong`}
                  >
                    <tool.icon className={`size-8 ${CATEGORY_COLOR[tool.category]}`} aria-hidden="true" />
                    <span className="text-lg font-semibold">{t(`tools.${tool.slug}.name`)}</span>
                    <span className="text-sm text-muted">{t(`tools.${tool.slug}.description`)}</span>
                    <ArrowRight
                      className="mt-auto size-5 text-muted transition-transform duration-150 group-hover:translate-x-1"
                      aria-hidden="true"
                    />
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        );
      })}

      {conversions.length ? (
        <section aria-labelledby="popular-heading" className="space-y-4">
          <h2 id="popular-heading" className="text-xl font-semibold">
            {t("home.popularHeading")}
          </h2>
          <ul className="flex flex-wrap gap-2">
            {conversions.map((c) => (
              <li key={c.pair}>
                <Link
                  to={`/${lang}/convert/${c.pair}`}
                  className="inline-flex min-h-11 items-center rounded-full border border-border-strong bg-surface px-4 text-sm font-semibold transition-colors duration-150 hover:bg-surface-muted"
                >
                  {t("conversion.short", { from: c.from.toUpperCase(), to: c.to.toUpperCase() })}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section aria-labelledby="benefits-heading" className="space-y-4">
        <h2 id="benefits-heading" className="text-xl font-semibold">
          {t("home.benefitsHeading")}
        </h2>
        <ul className="grid gap-6 sm:grid-cols-3">
          {BENEFITS.map(({ key, icon: Icon }) => (
            <li key={key} className="space-y-2">
              <Icon className="size-6 text-primary" aria-hidden="true" />
              <h3 className="font-semibold">{t(`home.benefits.${key}.title`)}</h3>
              <p className="text-sm text-muted">{t(`home.benefits.${key}.text`)}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
