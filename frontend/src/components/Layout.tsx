import { CircleUser, LogIn, Monitor, Moon, Sun } from "lucide-react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Link, Outlet, useLocation } from "react-router";

import { useLang } from "@/hooks/useLang";
import { directionOf, setLanguage } from "@/i18n";
import { btn } from "@/lib/ui";
import { LanguageMenu } from "@/components/LanguageMenu";
import { LogoMark, Wordmark } from "@/components/Logo";
import { SectionBar } from "@/components/SectionBar";
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
  const { t } = useTranslation();
  const lang = useLang();
  const { pathname } = useLocation();

  useEffect(() => {
    void setLanguage(lang);
    document.documentElement.lang = lang;
    document.documentElement.dir = directionOf(lang);
  }, [lang]);

  // Move focus to the page content after client-side navigation (screen readers).
  // Runs on purpose on every path change, though the body doesn't read pathname.
  useEffect(() => {
    document.getElementById("main")?.focus({ preventScroll: true });
    window.scrollTo(0, 0);
    // oxlint-disable-next-line react/exhaustive-effect-dependencies
  }, [pathname]);

  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:start-4 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-4 focus:py-2"
      >
        {t("nav.skip")}
      </a>
      <header className="sticky top-0 z-30 border-b border-border bg-bg/85 backdrop-blur-md supports-[backdrop-filter]:bg-bg/75">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-2 px-4">
          <Link
            to={`/${lang}`}
            className="group flex min-h-11 items-center gap-2.5 rounded-lg"
            // The visible name comes first so voice control ("click jichcha") works (WCAG 2.5.3).
            aria-label={`${t("meta.siteName")}, ${t("nav.home")}`}
          >
            <LogoMark className="size-8 transition-transform duration-300 ease-[var(--ease-out-soft)] group-hover:-translate-y-0.5" />
            {/* Below 400px the name would push the menu off-screen; the mark and aria-label remain. */}
            <span className="max-[399px]:sr-only">
              <Wordmark />
            </span>
          </Link>
          <div className="flex items-center gap-1">
            <LanguageMenu />
            <ThemeToggle />
            <AccountLink />
          </div>
        </div>
        <SectionBar />
      </header>
      <main id="main" tabIndex={-1} className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 outline-none sm:py-12">
        <Outlet />
      </main>
      <footer className="mt-12 border-t border-border">
        <div className="mx-auto grid max-w-6xl gap-6 px-4 py-10 text-sm text-muted sm:grid-cols-[1fr_auto] sm:items-end">
          <div className="space-y-3">
            <Link to={`/${lang}`} className="inline-flex min-h-11 items-center gap-2.5 text-fg" aria-label={`${t("meta.siteName")}, ${t("nav.home")}`}>
              <LogoMark className="size-7" />
              <Wordmark />
            </Link>
            <p className="max-w-sm text-pretty">{t("footer.privacy")}</p>
          </div>
          <nav aria-label={t("footer.legalNav")} className="flex flex-wrap gap-x-5">
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
