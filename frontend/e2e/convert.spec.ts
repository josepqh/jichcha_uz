import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "@playwright/test";

const fixture = (name: string) => path.join(path.dirname(fileURLToPath(import.meta.url)), "fixtures", name);

test.describe("image tools", () => {
  test("converts a PNG to JPG and downloads it", async ({ page }) => {
    await page.goto("/en/convert/png-to-jpg");
    await expect(page.getByRole("heading", { level: 1, name: "Convert PNG to JPG" })).toBeVisible();

    await page.getByTestId("file-input").setInputFiles(fixture("photo.png"));
    await expect(page.getByText("1 file selected")).toBeVisible();
    await page.getByRole("button", { name: "Convert to JPG" }).click();

    await expect(page.getByText("Done")).toBeVisible({ timeout: 20_000 });
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("link", { name: "Download photo.jpg" }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe("photo.jpg");
  });

  test("turns an iPhone HEIC and a JPG into one PDF, in the chosen order", async ({ page }) => {
    await page.goto("/en/tools/images-to-pdf");
    await page.getByTestId("file-input").setInputFiles([fixture("page2.jpg"), fixture("iphone.heic")]);
    await page.getByRole("button", { name: "Move iphone.heic up" }).click();
    const files = page.getByRole("list", { name: "2 files selected" });
    await expect(files.getByRole("listitem").first()).toContainText("iphone.heic");

    await page.getByText("Landscape", { exact: true }).click();
    await page.getByRole("button", { name: "Create PDF" }).click();

    await expect(page.getByText("Done")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("iphone.pdf")).toBeVisible();
  });

  test("shows a clear error when a file is not really an image", async ({ page }) => {
    await page.goto("/en/tools/image-convert");
    await page.getByTestId("file-input").setInputFiles(fixture("not-an-image.png"));
    await page.getByRole("button", { name: "Convert to JPG" }).click();
    await expect(page.getByRole("alert")).toContainText("isn't a file this tool accepts");
  });

  test("compression reports the size difference and files can be deleted now", async ({ page }) => {
    await page.goto("/uz/tools/image-compress");
    await page.getByTestId("file-input").setInputFiles(fixture("photo.png"));
    await page.getByText("Kuchli", { exact: true }).click();
    await page.getByRole("button", { name: "Siqish" }).click();
    await expect(page.getByText("Tayyor")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText(/kamaydi|siqib boʻlmadi/)).toBeVisible();

    page.once("dialog", (dialog) => dialog.accept());
    await page.getByRole("button", { name: "Serverdan hozir oʻchirish" }).click();
    await expect(page.getByText("Fayllar serverdan oʻchirildi.")).toBeVisible();
  });
});

test.describe("navigation", () => {
  test("search filters tools and language switch keeps the page", async ({ page }) => {
    await page.goto("/uz");
    await page.getByRole("searchbox", { name: "Vositani qidirish" }).fill("heic pdf");
    await expect(page.getByRole("link", { name: "HEIC → PDF" })).toBeVisible();
    await expect(page.getByRole("link", { name: "PNG → JPG" })).toHaveCount(0);

    await page.getByRole("link", { name: "HEIC → PDF" }).click();
    await page.getByRole("link", { name: "ru", exact: true }).click();
    await expect(page).toHaveURL(/\/ru\/convert\/heic-to-pdf$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "ru");
  });

  test("unknown pages show a not-found message", async ({ page }) => {
    await page.goto("/en/tools/does-not-exist");
    await expect(page.getByRole("heading", { name: "Page not found" })).toBeVisible();
  });
});
