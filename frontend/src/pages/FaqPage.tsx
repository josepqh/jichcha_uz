import { ChevronDown } from "lucide-react";
import { useTranslation } from "react-i18next";

import { card } from "@/lib/ui";

/** Default limits (LimitPolicy seed). Staff can change them; the account page shows the live values. */
const LIMITS = {
  guestMb: 50,
  guestTasks: 20,
  guestBatch: 10,
  guestHours: 1,
  userMb: 200,
  userTasks: 100,
  userBatch: 30,
  userHours: 6,
};

const BOT = import.meta.env.VITE_TELEGRAM_BOT_USERNAME ?? "";

interface Item {
  q: string;
  a: string;
}

export function FaqPage() {
  const { t } = useTranslation();
  const items = (t("faq.items", { returnObjects: true, ...LIMITS }) as Item[]).map((item) => ({
    q: item.q,
    // returnObjects does not interpolate nested strings in every i18next version: fill them here.
    a: item.a.replace(/\{\{(\w+)\}\}/g, (_, key: keyof typeof LIMITS) => String(LIMITS[key] ?? "")),
  }));
  const structured = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: items.map((item) => ({
      "@type": "Question",
      name: item.q,
      acceptedAnswer: { "@type": "Answer", text: item.a },
    })),
  };

  return (
    <article className="mx-auto max-w-2xl space-y-8">
      <title>{`${t("faq.title")} | ${t("meta.siteName")}`}</title>
      <meta name="description" content={t("faq.description")} />
      <script type="application/ld+json">{JSON.stringify(structured)}</script>
      <header className="space-y-3">
        <h1 className="text-2xl font-bold tracking-tight sm:text-4xl">{t("faq.title")}</h1>
        <p className="text-pretty text-muted">{t("faq.intro")}</p>
      </header>
      <div className="space-y-3">
        {items.map((item) => (
          <details key={item.q} className={`${card} group`}>
            <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 px-5 py-4 font-semibold [&::-webkit-details-marker]:hidden">
              <h2 className="text-base">{item.q}</h2>
              <ChevronDown
                className="size-5 shrink-0 text-muted transition-transform duration-200 group-open:rotate-180 motion-reduce:transition-none"
                aria-hidden="true"
              />
            </summary>
            <p className="px-5 pb-5 text-pretty text-muted">{item.a}</p>
          </details>
        ))}
      </div>
      {BOT ? (
        <p>
          <a
            href={`https://t.me/${encodeURIComponent(BOT)}`}
            className="font-semibold text-primary underline-offset-4 hover:underline"
            rel="noopener"
          >
            {t("faq.botLink")}
          </a>
        </p>
      ) : null}
    </article>
  );
}
