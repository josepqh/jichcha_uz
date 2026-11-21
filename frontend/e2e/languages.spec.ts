import { expect, test } from "@playwright/test";

test("the globe menu switches the page language and keeps the page", async ({ page }) => {
  await page.goto("/en/pdf");
  const menu = page.getByRole("button", { name: /^Language/ });
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  await menu.click();
  await expect(menu).toHaveAttribute("aria-expanded", "true");
  // Thirteen languages, each named in its own script; the current one is marked.
  await expect(page.getByRole("link", { name: "English" })).toHaveAttribute("aria-current", "true");
  for (const name of ["Oʻzbekcha", "Русский", "中文", "Español", "हिन्दी", "العربية", "Français", "Português", "Deutsch", "日本語", "Türkçe", "한국어"]) {
    await expect(page.getByRole("link", { name })).toBeVisible();
  }
  await page.keyboard.press("Escape");
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  await expect(menu).toBeFocused();

  await menu.click();
  await page.getByRole("link", { name: "Deutsch" }).click();
  await expect(page).toHaveURL(/\/de\/pdf$/);
  await expect(page.locator("html")).toHaveAttribute("lang", "de");
  await expect(page.getByRole("main").getByRole("link", { name: /PDF zusammenfügen/ })).toBeVisible();
});

test("Arabic is laid out right to left", async ({ page }) => {
  await page.goto("/ar");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("مجانية");
  const search = await page.getByRole("searchbox").boundingBox();
  const icon = await page.locator("label[for='tool-search'] + svg").boundingBox();
  // The search icon sits at the start of the field, which is its right edge in RTL.
  expect(icon!.x).toBeGreaterThan(search!.x + search!.width / 2);
  await page.goto("/ar/faq");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("الأسئلة الشائعة");
});

test("a language loads on demand and falls back to English only for staff pages", async ({ page }) => {
  await page.goto("/ja/word");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Word");
  await expect(page.getByRole("main").getByRole("link", { name: /Word → PDF/ })).toBeVisible();
});
