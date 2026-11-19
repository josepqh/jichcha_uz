/**
 * Build-time rendering of public pages (scripts/prerender.mjs), so search engines and link previews get
 * real HTML. The browser then renders the app over it as usual (createRoot, no hydration).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToString } from "react-dom/server";
import { StaticRouter } from "react-router";

import { App } from "./App";
import i18n, { LANGUAGES } from "./i18n";
import { buildCatalog } from "./lib/catalog";
import { SECTION_SLUG, SECTIONS } from "./lib/sections";
import { POPULAR_CONVERSIONS, TOOL_LIST } from "./lib/tools";

export { LANGUAGES };

/** Public, indexable paths (without the language prefix). Account, admin and auth pages are left out. */
export function publicPaths(): string[] {
  const conversions = new Set<string>(POPULAR_CONVERSIONS);
  for (const section of buildCatalog()) {
    for (const entry of section.entries) if (entry.kind === "conversion") conversions.add(entry.pair);
  }
  return [
    "",
    ...SECTIONS.map((family) => SECTION_SLUG[family]),
    ...TOOL_LIST.map((tool) => `tools/${tool.slug}`),
    ...[...conversions].toSorted().map((pair) => `convert/${pair}`),
    "faq",
    "privacy",
    "terms",
  ];
}

export async function render(url: string, lang: string): Promise<string> {
  await i18n.changeLanguage(lang);
  const client = new QueryClient({ defaultOptions: { queries: { enabled: false } } });
  return renderToString(
    <QueryClientProvider client={client}>
      <StaticRouter location={url}>
        <App />
      </StaticRouter>
    </QueryClientProvider>,
  );
}
