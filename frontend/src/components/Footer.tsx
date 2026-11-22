import { Bot, Mail, Send } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { FamilyIcon } from "@/components/FamilyIcon";
import { LogoMark, Wordmark } from "@/components/Logo";
import { useLang } from "@/hooks/useLang";
import { CONTACT_EMAIL, TELEGRAM_URL, TELEGRAM_USERNAME } from "@/lib/contacts";
import { SECTION_SLUG, SECTIONS } from "@/lib/sections";
import { useAuthStore } from "@/stores/auth";

const BOT = import.meta.env.VITE_TELEGRAM_BOT_USERNAME ?? "";
// Read once per page load: a footer year does not need to tick over at midnight.
const YEAR = new Date().getFullYear();
const linkClass = "inline-flex min-h-10 items-center gap-2 text-muted underline-offset-4 transition-colors duration-150 hover:text-fg hover:underline";
const headingClass = "font-mono text-xs font-medium tracking-wide text-fg uppercase";

/** Site footer: the brand, every section and the help pages. */
export function Footer() {
  const { t } = useTranslation();
  const lang = useLang();
  const signedIn = useAuthStore((s) => s.status === "authed");

  return (
    <footer className="mt-16 border-t border-border bg-surface/60">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 text-sm sm:grid-cols-2 lg:grid-cols-[1.6fr_1fr_1fr]">
        <div className="space-y-4">
          <Link to={`/${lang}`} className="inline-flex min-h-11 items-center gap-2.5" aria-label={`${t("meta.siteName")}, ${t("nav.home")}`}>
            <LogoMark className="size-7" />
            <Wordmark />
          </Link>
          <p className="max-w-xs text-pretty text-muted">{t("footer.privacy")}</p>
          <ul>
            <li>
              <a href={TELEGRAM_URL} className={linkClass} rel="noopener">
                <Send className="size-4" aria-hidden="true" />@{TELEGRAM_USERNAME}
              </a>
            </li>
            <li>
              <a href={`mailto:${CONTACT_EMAIL}`} className={linkClass}>
                <Mail className="size-4" aria-hidden="true" />
                {CONTACT_EMAIL}
              </a>
            </li>
            {BOT ? (
              <li>
                <a href={`https://t.me/${encodeURIComponent(BOT)}`} className={linkClass} rel="noopener">
                  <Bot className="size-4" aria-hidden="true" />
                  {t("faq.botLink")}
                </a>
              </li>
            ) : null}
          </ul>
        </div>

        <div className="space-y-3">
          <h2 className={headingClass}>
            {t("sections.label")}
          </h2>
          <ul>
            {SECTIONS.map((family) => (
              <li key={family}>
                <Link to={`/${lang}/${SECTION_SLUG[family]}`} className={linkClass}>
                  <FamilyIcon family={family} className="size-4" />
                  {t(`home.groups.${family}`)}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div className="space-y-3">
          <h2 className={headingClass}>
            {t("footer.help")}
          </h2>
          <ul>
            <li>
              <Link to={`/${lang}/faq`} className={linkClass}>
                {t("footer.faqLink")}
              </Link>
            </li>
            <li>
              <Link to={`/${lang}/feedback`} className={linkClass}>
                {t("feedback.title")}
              </Link>
            </li>
            <li>
              <Link to={`/${lang}/privacy`} className={linkClass}>
                {t("footer.privacyLink")}
              </Link>
            </li>
            <li>
              <Link to={`/${lang}/terms`} className={linkClass}>
                {t("footer.termsLink")}
              </Link>
            </li>
            <li>
              <Link to={`/${lang}/${signedIn ? "account" : "login"}`} className={linkClass}>
                {signedIn ? t("nav.account") : t("nav.login")}
              </Link>
            </li>
          </ul>
        </div>
      </div>
      <div className="border-t border-border">
        <p className="mx-auto max-w-6xl px-4 py-5 text-xs text-muted">
          {t("footer.rights", { year: YEAR })}
        </p>
      </div>
    </footer>
  );
}
