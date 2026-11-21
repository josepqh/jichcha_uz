import { expect, test } from "@playwright/test";

test("footer links open the privacy policy and terms in the current language", async ({ page }) => {
  await page.goto("/ru");
  await page.getByRole("contentinfo").getByRole("link", { name: "Политика конфиденциальности" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Политика конфиденциальности");
  await expect(page.getByRole("heading", { name: "Cookie и память браузера" })).toBeVisible();

  await page.getByRole("link", { name: "Условия использования" }).click();
  await expect(page).toHaveURL(/\/ru\/terms$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Условия использования");
});

test("the header fits a 360px phone without horizontal scrolling", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await page.goto("/uz/privacy");
  await expect(page.getByText("2026-yil 21-noyabr", { exact: false })).toBeVisible();
  const overflow = await page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth");
  expect(overflow).toBe(0);
});
