// Writes dist/<lang>/<path>/index.html for every public page, plus sitemap.xml and robots.txt.
// Run after `vite build` and `vite build --ssr src/entry-server.tsx --outDir dist-ssr`.
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dist = path.join(root, "dist");
const site = (process.env.SITE_URL || process.env.PUBLIC_ORIGIN || "http://localhost:8080").replace(/\/$/, "");
const { render, publicPaths, LANGUAGES, directionOf } = await import(pathToFileURL(path.join(root, "dist-ssr/entry-server.js")).href);

const template = readFileSync(path.join(dist, "index.html"), "utf8");
const escapeAttr = (s) => s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
const url = (lang, p) => `${site}/${lang}${p ? `/${p}` : ""}`;

// React renders <title> and <meta> where the page declares them; they belong in <head>.
function takeHead(html) {
  const head = [];
  const body = html.replace(/<title>[\s\S]*?<\/title>|<meta name="(?:description|robots)"[^>]*\/?>/g, (tag) => {
    head.push(tag);
    return "";
  });
  return { head, body };
}

function page(lang, p, html) {
  const { head, body } = takeHead(html);
  const alternates = LANGUAGES.map((l) => `<link rel="alternate" hreflang="${l}" href="${escapeAttr(url(l, p))}" />`);
  alternates.push(`<link rel="alternate" hreflang="x-default" href="${escapeAttr(url("uz", p))}" />`);
  const tags = [...head, `<link rel="canonical" href="${escapeAttr(url(lang, p))}" />`, ...alternates].join("\n    ");
  return template
    .replace(/<html lang="[^"]*">/, `<html lang="${lang}" dir="${directionOf(lang)}">`)
    .replace(/<title>[\s\S]*?<\/title>\s*<meta\s+name="description"[\s\S]*?\/>/, tags)
    .replace('<div id="root"></div>', `<div id="root">${body}</div>`);
}

const paths = publicPaths();
for (const lang of LANGUAGES) {
  for (const p of paths) {
    const html = await render(`/${lang}${p ? `/${p}` : ""}`, lang);
    const dir = path.join(dist, lang, p);
    mkdirSync(dir, { recursive: true });
    writeFileSync(path.join(dir, "index.html"), page(lang, p, html));
  }
}

const sitemap = [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
  ...LANGUAGES.flatMap((lang) =>
    paths.map((p) =>
      [
        `  <url><loc>${escapeAttr(url(lang, p))}</loc>`,
        ...LANGUAGES.map((l) => `    <xhtml:link rel="alternate" hreflang="${l}" href="${escapeAttr(url(l, p))}"/>`),
        `    <xhtml:link rel="alternate" hreflang="x-default" href="${escapeAttr(url("uz", p))}"/>`,
        "  </url>",
      ].join("\n"),
    ),
  ),
  "</urlset>",
].join("\n");
writeFileSync(path.join(dist, "sitemap.xml"), `${sitemap}\n`);

writeFileSync(
  path.join(dist, "robots.txt"),
  [
    "User-agent: *",
    "Disallow: /api/",
    "Disallow: /admin/",
    ...LANGUAGES.flatMap((l) => [`Disallow: /${l}/account`, `Disallow: /${l}/admin`, `Disallow: /${l}/reset/`]),
    "",
    `Sitemap: ${site}/sitemap.xml`,
    "",
  ].join("\n"),
);

rmSync(path.join(root, "dist-ssr"), { recursive: true, force: true });
console.log(`prerendered ${paths.length * LANGUAGES.length} pages for ${site}`);
