import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "./test";

const fixture = (name: string) => path.join(path.dirname(fileURLToPath(import.meta.url)), "fixtures", name);
const hasLibreOffice =
  process.env.E2E_OFFICE === "1" || existsSync("/Applications/LibreOffice.app/Contents/MacOS/soffice");

test.describe("PDF tools", () => {
  test("merges two PDFs in the chosen order", async ({ page }) => {
    await page.goto("/en/tools/pdf-merge");
    await page.getByTestId("file-input").setInputFiles([fixture("two.pdf"), fixture("three.pdf")]);
    await page.getByRole("button", { name: "Move three.pdf up" }).click();
    await page.getByRole("button", { name: "Merge" }).click();
    await expect(page.getByText("Done")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("three-merged.pdf")).toBeVisible();
  });

  test("asks for a second file before merging", async ({ page }) => {
    await page.goto("/en/tools/pdf-merge");
    await page.getByTestId("file-input").setInputFiles(fixture("two.pdf"));
    await page.getByRole("button", { name: "Merge" }).click();
    await expect(page.getByRole("alert")).toContainText("Choose at least 2 files.");
  });

  test("splits selected page ranges and validates the input", async ({ page }) => {
    await page.goto("/en/tools/pdf-split");
    await page.getByTestId("file-input").setInputFiles(fixture("three.pdf"));
    await page.getByText("Selected pages", { exact: true }).click();
    const pages = page.getByRole("textbox", { name: "Pages" });
    await pages.fill("1-x");
    await page.getByRole("button", { name: "Split" }).click();
    await expect(page.getByText(/Write pages like/)).toBeVisible();

    await pages.fill("1, 2-3");
    await page.getByRole("button", { name: "Split" }).click();
    await expect(page.getByText("Done")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("three-p1.pdf")).toBeVisible();
    await expect(page.getByText("three-p2-3.pdf")).toBeVisible();
  });

  test("organizes pages: delete and rotate with buttons", async ({ page }) => {
    await page.goto("/en/tools/pdf-organize");
    await page.getByTestId("file-input").setInputFiles(fixture("three.pdf"));
    await expect(page.getByText("3 of 3 pages")).toBeVisible({ timeout: 15_000 });

    await page.getByRole("button", { name: "Delete Page 2" }).click();
    await page.getByRole("button", { name: "Rotate Page 3 by 90°" }).click();
    await page.getByRole("button", { name: "Move Page 3 earlier" }).click();
    await expect(page.getByText("2 of 3 pages")).toBeVisible();
    const cards = page.getByRole("list", { name: "PDF pages" }).getByRole("listitem");
    await expect(cards.first()).toContainText("1. Page 3 · 90°");

    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText("Done")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("three.pdf")).toBeVisible();
  });

  test("renders pages to PNG images", async ({ page }) => {
    await page.goto("/en/convert/pdf-to-png");
    await page.getByTestId("file-input").setInputFiles(fixture("two.pdf"));
    await page.getByRole("button", { name: "Convert to PNG" }).click();
    await expect(page.getByText("Done")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText("two-001.png")).toBeVisible();
    await expect(page.getByRole("link", { name: /Download all as ZIP/ })).toBeVisible();
  });

  test("compresses a scanned PDF and reports the saving", async ({ page }) => {
    await page.goto("/en/tools/pdf-compress");
    await page.getByTestId("file-input").setInputFiles(fixture("scan.pdf"));
    await page.getByText("Strong", { exact: true }).click();
    await page.getByRole("button", { name: "Compress" }).click();
    await expect(page.getByText("Done")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(/% smaller:/)).toBeVisible();
  });
});

test.describe("Office to PDF", () => {
  test.skip(!hasLibreOffice, "LibreOffice is not installed on this machine");
  test.setTimeout(90_000);

  test("converts a DOCX with Uzbek text to PDF", async ({ page }) => {
    await page.goto("/uz/convert/docx-to-pdf");
    await page.getByTestId("file-input").setInputFiles(fixture("referat.docx"));
    await page.getByRole("button", { name: "PDF qilish" }).click();
    await expect(page.getByText("Tayyor")).toBeVisible({ timeout: 60_000 });
    const download = page.waitForEvent("download");
    await page.getByRole("link", { name: "referat.pdf faylini yuklab olish" }).click();
    expect((await download).suggestedFilename()).toBe("referat.pdf");
  });
});

test("a result can go straight into the next tool", async ({ page }) => {
  await page.goto("/en/tools/images-to-pdf");
  await page.getByTestId("file-input").setInputFiles(fixture("photo.png"));
  await page.getByRole("button", { name: "Create PDF" }).click();
  await expect(page.getByText("Done")).toBeVisible({ timeout: 20_000 });
  await page.getByRole("link", { name: "Compress PDF" }).click();
  await expect(page).toHaveURL(/\/en\/tools\/pdf-compress$/);
  await expect(page.getByText("photo.pdf")).toBeVisible();
  await page.getByRole("button", { name: "Compress" }).click();
  await expect(page.getByText("Done")).toBeVisible({ timeout: 20_000 });
});
