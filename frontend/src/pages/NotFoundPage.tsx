import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { useLang } from "@/hooks/useLang";
import { btn } from "@/lib/ui";

export function NotFoundPage() {
  const { t } = useTranslation();
  const lang = useLang();
  return (
    <div className="mx-auto max-w-md space-y-4 py-16 text-center">
      <title>{`${t("notFound.title")} | ${t("meta.siteName")}`}</title>
      <meta name="robots" content="noindex" />
      <h1 className="text-3xl font-bold">{t("notFound.title")}</h1>
      <p className="text-muted">{t("notFound.text")}</p>
      <Link to={`/${lang}`} className={btn.primary}>
        {t("notFound.back")}
      </Link>
    </div>
  );
}
