import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "@playwright/test";

const fixture = (name: string) => path.join(path.dirname(fileURLToPath(import.meta.url)), "fixtures", name);

test("each section under the header shows only its own tools", async ({ page }) => {
  await page.goto("/en");
  const bar = page.getByRole("navigation", { name: "Sections" });
  await bar.getByRole("link", { name: "PDF" }).click();
  await expect(page).toHaveURL(/\/en\/pdf$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("PDF");
  await expect(bar.getByRole("link", { name: "PDF" })).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("main").getByRole("link", { name: /Merge PDF/ })).toBeVisible();
  await expect(page.getByRole("main").getByRole("link", { name: /Word to PDF/ })).toHaveCount(0); // Word files live under Word

  await bar.getByRole("link", { name: "Word" }).click();
  await expect(page).toHaveURL(/\/en\/word$/);
  await expect(page.getByRole("main").getByRole("link", { name: /Merge PDF/ })).toHaveCount(0);
  await page.getByRole("main").getByRole("link", { name: /Word to PDF/ }).click();
  await expect(page).toHaveURL(/\/en\/convert\/docx-to-pdf$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Convert DOCX to PDF");
  // The tool page still says which section it belongs to.
  await expect(bar.getByRole("link", { name: "Word" })).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("navigation", { name: "You are here" }).getByRole("link", { name: "Word" })).toBeVisible();
});

test("search lists matching tools from every section", async ({ page }) => {
  await page.goto("/en");
  await page.getByRole("searchbox", { name: "Search tools" }).fill("excel");
  const results = page.getByRole("region", { name: "Tools" });
  await expect(results.getByRole("link", { name: /Excel to PDF/ })).toBeVisible();
  await expect(results.getByRole("link", { name: /Extract archive/ })).toHaveCount(0);
  await page.getByRole("searchbox", { name: "Search tools" }).fill("zzzz");
  await expect(page.getByRole("status")).toContainText("No tool matches");
});

test("a dropped file is recognised and handed to the chosen tool", async ({ page }) => {
  await page.goto("/en");
  await page.getByLabel("Choose a file").setInputFiles(fixture("photo.png"));
  await expect(page.getByText("is a Photos file. What should we do?")).toBeVisible();
  await page.getByRole("link", { name: "Shrink file size" }).click();
  await expect(page).toHaveURL(/\/en\/tools\/image-compress$/);
  await expect(page.getByRole("heading", { name: "1 file selected" })).toBeVisible();
  await expect(page.getByText("photo.png")).toBeVisible();
});
