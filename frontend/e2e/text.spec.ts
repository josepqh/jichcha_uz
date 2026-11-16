import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "@playwright/test";

const hasCalibre = process.env.E2E_EBOOK === "1" || existsSync("/Applications/calibre.app/Contents/MacOS/ebook-convert");
const fixture = (name: string) => path.join(path.dirname(fileURLToPath(import.meta.url)), "fixtures", name);

test("writes Markdown, previews it and downloads HTML without a server round trip", async ({ page }) => {
  await page.goto("/en/tools/text-convert");
  await page.getByLabel("Text", { exact: true }).fill("# Shopping\n\n- apples\n- **tea**\n\n<script>alert(1)</script>");
  await page.getByLabel("File name").fill("list");
  const preview = page.getByText("Shopping", { exact: true });
  if (!(await preview.isVisible())) await page.getByRole("tab", { name: "Preview" }).click();
  await expect(page.getByRole("heading", { name: "Shopping" })).toBeVisible();
  // Markdown marks count as words too: "#", "-", "**tea**", the script tag.
  await expect(page.getByText("7 words", { exact: false })).toBeVisible();

  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "HTML", exact: true }).click();
  const file = await download;
  expect(file.suggestedFilename()).toBe("list.html");
});

test("opens a text file and exports it to DOCX on the server", async ({ page }) => {
  test.skip(!hasCalibre, "Calibre is not installed");
  test.setTimeout(90_000);
  await page.goto("/en/tools/text-convert");
  await page.getByTestId("text-file-input").setInputFiles({
    name: "notes.md",
    mimeType: "text/markdown",
    buffer: Buffer.from("# Notes\n\nFirst line."),
  });
  await expect(page.getByLabel("File name")).toHaveValue("notes");
  await page.getByRole("button", { name: "DOCX", exact: true }).click();
  await expect(page.getByText("notes.docx")).toBeVisible({ timeout: 60_000 });
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
