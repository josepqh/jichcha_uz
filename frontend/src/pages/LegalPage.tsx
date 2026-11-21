import { useTranslation } from "react-i18next";

import { formatDate } from "@/lib/format";
import { card } from "@/lib/ui";

/** Set these before launch: they name who runs the service and how to reach them (.env, VITE_*). */
const OPERATOR = import.meta.env.VITE_LEGAL_NAME ?? "";
const CONTACT = import.meta.env.VITE_CONTACT_EMAIL ?? "";
const UPDATED = "2026-11-21";

interface Section {
  h: string;
  p: string[];
}

export function LegalPage({ doc }: { doc: "privacy" | "terms" }) {
  const { t, i18n } = useTranslation();
  const sections = t(`legal.${doc}.sections`, { returnObjects: true }) as Section[];
  const updated = formatDate(`${UPDATED}T12:00:00`, i18n.language);

  return (
    <article className="mx-auto max-w-2xl space-y-8">
      <title>{`${t(`legal.${doc}.title`)} | ${t("meta.siteName")}`}</title>
      <header className="space-y-3">
        <h1 className="font-display text-3xl leading-[1.1] font-medium tracking-[-0.045em] sm:text-4xl">{t(`legal.${doc}.title`)}</h1>
        <p className="text-sm text-muted">{t("legal.updated", { date: updated })}</p>
        <p className="text-pretty">{t(`legal.${doc}.intro`)}</p>
      </header>
      {sections.map((section) => (
        <section key={section.h} className="space-y-3">
          <h2 className="text-lg font-semibold">{section.h}</h2>
          {section.p.map((para) => (
            <p key={para} className="text-pretty text-muted">
              {para}
            </p>
          ))}
        </section>
      ))}
      <footer className={`${card} space-y-1 p-5 text-sm`}>
        {OPERATOR ? <p>{t("legal.operator", { name: OPERATOR })}</p> : null}
        {CONTACT ? (
          <p>
            {t("legal.contact", { email: "" })}
            <a href={`mailto:${CONTACT}`} className="font-semibold text-primary underline-offset-4 hover:underline">
              {CONTACT}
            </a>
          </p>
        ) : (
          <p className="text-muted">{t("legal.noContact")}</p>
        )}
      </footer>
    </article>
  );
}
