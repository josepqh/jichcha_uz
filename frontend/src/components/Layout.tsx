import { CircleUser, LogIn, Monitor, Moon, Sun } from "lucide-react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Link, Outlet, useLocation } from "react-router";

import { useLang } from "@/hooks/useLang";
import { LANGUAGE_NAMES, LANGUAGES } from "@/i18n";
import { btn } from "@/lib/ui";
import { useAuthStore } from "@/stores/auth";
import { applyTheme, useThemeStore } from "@/stores/theme";

const THEME_ICON = { system: Monitor, light: Sun, dark: Moon } as const;

function ThemeToggle() {
  const { t } = useTranslation();
  const theme = useThemeStore((s) => s.theme);
  const cycle = useThemeStore((s) => s.cycle);
  const Icon = THEME_ICON[theme];

  useEffect(() => {
    applyTheme(theme);
    if (theme !== "system") return;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => applyTheme("system");
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, [theme]);

  const label = t("nav.theme", { mode: t(`nav.themeModes.${theme}`) });
  return (
    <button type="button" className={btn.icon} onClick={cycle} aria-label={label} title={label}>
      <Icon className="size-5" aria-hidden="true" />
    </button>
  );
}

function LanguageSwitcher() {
  const { t } = useTranslation();
  const lang = useLang();
  const { pathname } = useLocation();
  const rest = pathname.replace(/^\/[a-z]{2}(?=\/|$)/, "");

  return (
    <nav aria-label={t("nav.language")}>
      <ul className="flex items-center gap-1">
        {LANGUAGES.map((code) => (
          <li key={code}>
            <Link
              to={`/${code}${rest}`}
              lang={code}
              hrefLang={code}
              aria-current={code === lang ? "true" : undefined}
              title={LANGUAGE_NAMES[code]}
              className={`inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg px-2 text-sm font-semibold uppercase transition-colors duration-150 ${
                code === lang ? "bg-surface-muted text-fg" : "text-muted hover:text-fg"
              }`}
            >
              {code}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function AccountLink() {
  const { t } = useTranslation();
  const lang = useLang();
  const status = useAuthStore((s) => s.status);
  if (status === "loading") return <span className="size-11" aria-hidden="true" />;
  const authed = status === "authed";
  const Icon = authed ? CircleUser : LogIn;
  const label = authed ? t("nav.account") : t("nav.login");
  return (
    <Link
      to={`/${lang}/${authed ? "account" : "login"}`}
      className="inline-flex min-h-11 min-w-11 items-center justify-center gap-2 rounded-lg px-2 text-sm font-semibold text-fg transition-colors duration-150 hover:bg-surface-muted sm:px-3"
      aria-label={label}
    >
      <Icon className="size-5" aria-hidden="true" />
      <span className="hidden sm:inline">{label}</span>
    </Link>
  );
}

export function Layout() {
  const { t, i18n } = useTranslation();
  const lang = useLang();
  const { pathname } = useLocation();

  useEffect(() => {
    if (i18n.language !== lang) void i18n.changeLanguage(lang);
    document.documentElement.lang = lang;
  }, [i18n, lang]);

  // Move focus to the page content after client-side navigation (screen readers).
  useEffect(() => {
    document.getElementById("main")?.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }, [pathname]);

  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-4 focus:py-2"
      >
        {t("nav.skip")}
      </a>
      <header className="border-b border-border bg-surface/80 backdrop-blur supports-[backdrop-filter]:bg-surface/70">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between gap-2 px-4">
          <Link to={`/${lang}`} className="flex min-h-11 items-center gap-2 rounded-lg font-bold"
            // The visible name comes first so voice control ("click Universe") works (WCAG 2.5.3).
            aria-label={`${t("meta.siteName")}, ${t("nav.home")}`}
          >
            <img src="/favicon.svg" alt="" width={28} height={28} />
            {/* Below 400px the name would push the menu off-screen; the logo and aria-label remain. */}
            <span className="text-lg max-[399px]:sr-only" translate="no">
              {t("meta.siteName")}
            </span>
          </Link>
          <div className="flex items-center gap-1">
            <LanguageSwitcher />
            <ThemeToggle />
            <AccountLink />
          </div>
        </div>
      </header>
      <main id="main" tabIndex={-1} className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 outline-none sm:py-12">
        <Outlet />
      </main>
      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-5xl flex-col gap-3 px-4 py-6 text-sm text-muted sm:flex-row sm:items-center sm:justify-between">
          <p>{t("footer.privacy")}</p>
          <nav aria-label={t("footer.legalNav")} className="flex flex-wrap gap-x-4">
            <Link to={`/${lang}/faq`} className="inline-flex min-h-11 items-center underline-offset-4 hover:text-fg hover:underline">
              {t("footer.faqLink")}
            </Link>
            <Link to={`/${lang}/privacy`} className="inline-flex min-h-11 items-center underline-offset-4 hover:text-fg hover:underline">
              {t("footer.privacyLink")}
            </Link>
            <Link to={`/${lang}/terms`} className="inline-flex min-h-11 items-center underline-offset-4 hover:text-fg hover:underline">
              {t("footer.termsLink")}
            </Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
