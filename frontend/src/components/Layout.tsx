import { CircleUser, LogIn, Monitor, Moon, Sun } from "lucide-react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Link, Outlet, useLocation } from "react-router";

import { useLang } from "@/hooks/useLang";
import { directionOf, setLanguage } from "@/i18n";
import { btn } from "@/lib/ui";
import { Footer } from "@/components/Footer";
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
      {/* One row on wide screens: logo, sections and controls share one centre line. Narrower, the
          sections wrap to a second scrollable row under the logo. */}
      <header className="sticky top-0 z-30 border-b border-border bg-bg/85 backdrop-blur-md supports-[backdrop-filter]:bg-bg/75">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 px-4 xl:h-16 xl:flex-nowrap">
          <Link
            to={`/${lang}`}
            className="group flex h-16 shrink-0 items-center gap-2.5 rounded-lg"
            // The visible name comes first so voice control ("click jichcha") works (WCAG 2.5.3).
            aria-label={`${t("meta.siteName")}, ${t("nav.home")}`}
          >
            <LogoMark className="size-8 transition-transform duration-300 ease-[var(--ease-out-soft)] group-hover:-translate-y-0.5" />
            {/* Below 400px the name would push the menu off-screen; the mark and aria-label remain. */}
            <span className="max-[399px]:sr-only">
              <Wordmark />
            </span>
          </Link>
          <div className="order-last -mx-4 w-[calc(100%+2rem)] border-t border-border px-4 xl:order-none xl:mx-0 xl:w-auto xl:min-w-0 xl:flex-1 xl:border-0 xl:px-0">
            <SectionBar />
          </div>
          <div className="ms-auto flex h-16 shrink-0 items-center gap-1 xl:ms-0">
            <LanguageMenu />
            <ThemeToggle />
            <AccountLink />
          </div>
        </div>
      </header>
      <main id="main" tabIndex={-1} className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 outline-none sm:py-12">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
