import path from "node:path";
import { fileURLToPath } from "node:url";

import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "./test";

const fixture = (name: string) => path.join(path.dirname(fileURLToPath(import.meta.url)), "fixtures", name);

// WCAG 2.2 A/AA. Serious and critical findings fail the build; minor/moderate are printed.
async function audit(page: Page, label: string) {
  // Audit from the top: scrolled, whatever sits under the sticky header reads as "obscured"
  // to target-size, which says where the page happens to be, not what is wrong with it.
  await page.evaluate("window.scrollTo(0, 0)");
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  const blocking = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  for (const v of results.violations) {
    console.log(`[${label}] ${v.impact} ${v.id}: ${v.nodes.map((n) => n.target.join(" ")).slice(0, 3).join(" | ")}`);
  }
  expect(blocking.map((v) => `${v.id} (${v.nodes.length})`), label).toEqual([]);
}

const PAGES = [
  "/uz",
  "/ru/convert/docx-to-pdf",
  "/en/tools/pdf-merge",
  "/en/tools/image-edit",
  "/uz/login",
  "/uz/register",
  "/en/privacy",
  "/en/does-not-exist",
];

for (const scheme of ["light", "dark"] as const) {
  test.describe(`${scheme} theme`, () => {
    // Axe judges the page at rest: entrance animations would be caught mid-fade.
    test.use({ colorScheme: scheme, reducedMotion: "reduce" });

    for (const url of PAGES) {
      test(`no serious accessibility problems on ${url}`, async ({ page }) => {
        await page.goto(url);
        await expect(page.locator("main")).toBeVisible();
        await audit(page, `${scheme} ${url}`);
      });
    }

    test("a tool with a file selected and a finished result", async ({ page }) => {
      await page.goto("/en/tools/image-edit");
      await page.getByTestId("file-input").setInputFiles(fixture("photo.png"));
      await expect(page.getByRole("slider", { name: "Crop area" })).toBeVisible();
      await audit(page, `${scheme} editor`);
      await page.getByRole("button", { name: "Apply" }).click();
      await expect(page.getByText("Done")).toBeVisible({ timeout: 20_000 });
      await audit(page, `${scheme} result`);
    });
  });
}
