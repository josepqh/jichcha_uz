import { expect, test } from "@playwright/test";

test("home sections group tools by the file you have", async ({ page }) => {
  await page.goto("/en");
  const pdf = page.getByRole("region", { name: "PDF", exact: true });
  await expect(pdf.getByRole("link", { name: /Merge PDF/ })).toBeVisible();
  await expect(pdf.getByRole("link", { name: /Word to PDF/ })).toHaveCount(0); // Word files live under Word

  await page.getByRole("navigation", { name: "Sections" }).getByRole("link", { name: "Word" }).click();
  await expect(page).toHaveURL(/#group-word$/);
  const word = page.getByRole("region", { name: "Word", exact: true });
  await word.getByRole("link", { name: /Word to PDF/ }).click();
  await expect(page).toHaveURL(/\/en\/convert\/docx-to-pdf$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Convert DOCX to PDF");
});

test("search filters inside sections and hides empty ones", async ({ page }) => {
  await page.goto("/en");
  await page.getByRole("searchbox", { name: "Search tools" }).fill("excel");
  await expect(page.getByRole("region", { name: "Excel", exact: true })).toBeVisible();
  await expect(page.getByRole("region", { name: "Archives", exact: true })).toHaveCount(0);
});
