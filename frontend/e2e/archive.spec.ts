import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "@playwright/test";

const fixture = (name: string) => path.join(path.dirname(fileURLToPath(import.meta.url)), "fixtures", name);
const hasCalibre = process.env.E2E_EBOOK === "1" || existsSync("/Applications/calibre.app/Contents/MacOS/ebook-convert");

test.describe("Archives", () => {
  test("extracts a RAR and keeps folders in the file names", async ({ page }) => {
    await page.goto("/en/tools/archive-extract");
    await page.getByTestId("file-input").setInputFiles(fixture("hujjatlar.rar"));
    await page.getByRole("button", { name: "Extract" }).click();
    await expect(page.getByText("Done")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("hisobotlar/yanvar.txt")).toBeVisible();
    await expect(page.getByText("eslatma.txt")).toBeVisible();

    const download = page.waitForEvent("download");
    await page.getByRole("link", { name: "Download hisobotlar/yanvar.txt" }).click();
    expect((await download).suggestedFilename()).toBe("yanvar.txt");
    // The original archive is the "all files" copy; no second zip is made.
    await expect(page.getByRole("link", { name: /Download all as ZIP/ })).toHaveCount(0);
  });

  test("packs files of any type into a 7Z", async ({ page }) => {
    await page.goto("/uz/tools/archive-create");
    await expect(page.getByText("Istalgan turdagi fayl.")).toBeVisible();
    await page.getByTestId("file-input").setInputFiles([fixture("referat.docx"), fixture("photo.png"), fixture("not-an-image.png")]);
    await page.getByText("7Z", { exact: true }).click();
    await page.getByRole("button", { name: "7Z yaratish" }).click();
    await expect(page.getByText("Tayyor")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("archive.7z")).toBeVisible();
  });

  test("converts RAR to ZIP from the SEO page", async ({ page }) => {
    await page.goto("/ru/convert/rar-to-zip");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Конвертировать RAR в ZIP");
    await page.getByTestId("file-input").setInputFiles(fixture("hujjatlar.rar"));
    await page.getByRole("button", { name: "Перевести в ZIP" }).click();
    await expect(page.getByText("hujjatlar.zip")).toBeVisible({ timeout: 20_000 });
  });

  test("explains that an image is not an archive", async ({ page }) => {
    await page.goto("/en/tools/archive-extract");
    await page.getByTestId("file-input").setInputFiles(fixture("photo.png"));
    await page.getByRole("button", { name: "Extract" }).click();
    await expect(page.getByRole("alert")).toContainText("photo.png");
  });
});

test.describe("E-books", () => {
  test.skip(!hasCalibre, "Calibre is not installed");

  test("converts EPUB to PDF", async ({ page }) => {
    await page.goto("/en/convert/epub-to-pdf");
    await page.getByTestId("file-input").setInputFiles(fixture("kitob.epub"));
    await page.getByRole("button", { name: "Convert to PDF" }).click();
    await expect(page.getByText("Done")).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText("kitob.pdf")).toBeVisible();
  });

  test("converts FB2 to an e-book for Kindle", async ({ page }) => {
    await page.goto("/uz/tools/ebook-convert");
    await page.getByTestId("file-input").setInputFiles(fixture("ertak.fb2"));
    await page.getByText("AZW3 (Kindle)", { exact: true }).click();
    await page.getByRole("button", { name: "AZW3 qilish" }).click();
    await expect(page.getByText("ertak.azw3")).toBeVisible({ timeout: 60_000 });
  });
});
