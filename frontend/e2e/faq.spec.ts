import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "@playwright/test";

const fixture = (name: string) => path.join(path.dirname(fileURLToPath(import.meta.url)), "fixtures", name);

test("FAQ answers open and the page carries FAQPage data", async ({ page }) => {
  await page.goto("/en/faq");
  await expect(page.getByRole("heading", { level: 1, name: "Frequently asked questions" })).toBeVisible();
  const question = page.getByText("Do I need an account?");
  await question.click();
  await expect(page.getByText("Without an account you can upload files up to 50 MB")).toBeVisible();
  const data = JSON.parse((await page.locator('script[type="application/ld+json"]').textContent()) ?? "{}");
  expect(data["@type"]).toBe("FAQPage");
  expect(data.mainEntity).toHaveLength(10);
  expect(JSON.stringify(data)).not.toContain("{{");
  await page.getByRole("contentinfo").getByRole("link", { name: "FAQ" }).click();
  await expect(page).toHaveURL(/\/en\/faq$/);
});

test("compressed photo can be compared with the original", async ({ page }) => {
  await page.goto("/en/tools/image-compress");
  await page.getByTestId("file-input").setInputFiles(fixture("photo.png"));
  await page.getByRole("button", { name: /compress/i }).last().click();
  const slider = page.getByRole("slider", { name: "Compare original and compressed image" });
  await expect(slider).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole("img", { name: "After" })).toHaveJSProperty("complete", true);
  await slider.focus();
  await page.keyboard.press("ArrowLeft");
  await expect(slider).toHaveValue("49");
});
