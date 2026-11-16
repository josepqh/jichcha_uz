import { useParams } from "react-router";

import { DEFAULT_LANGUAGE, isLanguage, type Language } from "@/i18n";

export function useLang(): Language {
  const { lang } = useParams();
  return isLanguage(lang) ? lang : DEFAULT_LANGUAGE;
}
