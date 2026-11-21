import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import uz from "./locales/uz.json";

/** Uzbek, Russian and English first (the audience), then the ten most used languages on the web. */
export const LANGUAGES = ["uz", "ru", "en", "zh", "es", "hi", "ar", "fr", "pt", "de", "ja", "tr", "ko"] as const;
export type Language = (typeof LANGUAGES)[number];
export const DEFAULT_LANGUAGE: Language = "uz";

/** Each language in its own words, as the picker shows it. */
export const LANGUAGE_NAMES: Record<Language, string> = {
  uz: "Oʻzbekcha",
  ru: "Русский",
  en: "English",
  zh: "中文",
  es: "Español",
  hi: "हिन्दी",
  ar: "العربية",
  fr: "Français",
  pt: "Português",
  de: "Deutsch",
  ja: "日本語",
  tr: "Türkçe",
  ko: "한국어",
};

export const RTL_LANGUAGES: ReadonlySet<Language> = new Set(["ar"]);

export function isLanguage(value: string | undefined): value is Language {
  return (LANGUAGES as readonly string[]).includes(value ?? "");
}

export function directionOf(lang: Language): "rtl" | "ltr" {
  return RTL_LANGUAGES.has(lang) ? "rtl" : "ltr";
}

// Uzbek ships in the main bundle (the default); every other language is its own chunk, fetched on use.
const loaders = import.meta.glob<Record<string, unknown>>(["./locales/*.json", "!./locales/uz.json"], { import: "default" });

/** Loads a language's strings (and English, the fallback for anything not translated yet). */
export async function loadLanguage(lang: Language): Promise<void> {
  const needed = lang === "uz" ? [] : [...new Set<Language>([lang, "en"])];
  await Promise.all(
    needed
      .filter((code) => !i18n.hasResourceBundle(code, "translation"))
      .map(async (code) => i18n.addResourceBundle(code, "translation", await loaders[`./locales/${code}.json`]!())),
  );
}

/** Switches the interface language once its strings are in. */
export async function setLanguage(lang: Language): Promise<void> {
  await loadLanguage(lang);
  if (i18n.language !== lang) await i18n.changeLanguage(lang);
}

void i18n.use(initReactI18next).init({
  resources: { uz: { translation: uz } },
  partialBundledLanguages: true,
  lng: DEFAULT_LANGUAGE,
  fallbackLng: (code) => (code === "uz" ? ["uz"] : ["en", "uz"]),
  interpolation: { escapeValue: false }, // React escapes output
  returnNull: false,
});

export default i18n;
