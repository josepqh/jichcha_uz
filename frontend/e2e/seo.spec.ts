import { expect, test } from "./test";

// The dev server doesn't prerender; run against the built site (E2E_BASE_URL=http://localhost:8080).
test.skip(!process.env.E2E_BASE_URL, "Prerendered HTML exists only in the production build");

test("conversion pages arrive as real HTML, without JavaScript", async ({ request }) => {
  const html = await (await request.get("/ru/convert/docx-to-pdf")).text();
  expect(html).toContain('<html lang="ru" dir="ltr">');
  expect(html).toContain("<title>Конвертировать DOCX в PDF | jichcha</title>");
  expect(html).toMatch(/<h1[^>]*>Конвертировать DOCX в PDF<\/h1>/);
  expect(html).toMatch(/<link rel="canonical" href="[^"]+\/ru\/convert\/docx-to-pdf" \/>/);
  expect(html).toContain('hreflang="uz"');
});

test("sitemap and robots", async ({ request }) => {
  const sitemap = await (await request.get("/sitemap.xml")).text();
  expect(sitemap).toContain("/uz/tools/pdf-merge</loc>");
  const robots = await (await request.get("/robots.txt")).text();
  expect(robots).toContain("Disallow: /api/");
  expect(robots).toMatch(/Sitemap: .+\/sitemap\.xml/);
});

test("the app still takes over the prerendered page", async ({ page }) => {
  await page.goto("/en/tools/pdf-merge");
  await page.getByTestId("file-input").setInputFiles([]);
  await expect(page.getByRole("button", { name: "Choose files" })).toBeEnabled();
});
