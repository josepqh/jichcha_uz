import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "./test";

const fixture = (name: string) => path.join(path.dirname(fileURLToPath(import.meta.url)), "fixtures", name);

test("each section under the header opens its menu and its page shows only its own tools", async ({ page }) => {
  await page.goto("/en");
  const bar = page.getByRole("navigation", { name: "Sections" });
  const pdf = bar.getByRole("button", { name: "PDF" });
  await pdf.click();
  await expect(pdf).toHaveAttribute("aria-expanded", "true");
  // Like a converter site: converting first, then the kinds of work on PDFs.
  await expect(bar.getByRole("list", { name: "Convert into this format" }).getByRole("link", { name: "Word to PDF" })).toBeVisible();
  await expect(bar.getByRole("list", { name: "Convert to another format" }).getByRole("link", { name: "PDF → JPG, PNG" })).toBeVisible();
  await expect(bar.getByRole("list", { name: "Organize" }).getByRole("link", { name: "Merge PDF" })).toBeVisible();
  await expect(bar.getByRole("list", { name: "Security" }).getByRole("link", { name: "Protect PDF" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(pdf).toHaveAttribute("aria-expanded", "false");
  await expect(pdf).toBeFocused();

  await page.goto("/en/pdf");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("PDF");
  await expect(pdf).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("main").getByRole("link", { name: /Merge PDF/ })).toBeVisible();
  await expect(page.getByRole("main").getByRole("link", { name: /Word to PDF/ })).toHaveCount(0); // Word files live under Word

  await bar.getByRole("button", { name: "Word" }).click();
  await bar.getByRole("link", { name: "Word to PDF" }).click();
  await expect(page).toHaveURL(/\/en\/convert\/docx-to-pdf$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Convert DOCX to PDF");
  // The tool page still says which section it belongs to.
  await expect(bar.getByRole("button", { name: "Word" })).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("navigation", { name: "You are here" }).getByRole("link", { name: "Word" })).toBeVisible();
});

test("the footer links every section and the help pages", async ({ page }) => {
  await page.goto("/en/faq");
  const footer = page.getByRole("contentinfo");
  for (const name of ["PDF", "Word", "Excel", "PowerPoint", "Photos", "Archives", "FAQ", "Privacy policy", "Terms of use", "Suggestions and complaints"]) {
    await expect(footer.getByRole("link", { name, exact: true })).toBeVisible();
  }
  await expect(footer.getByRole("link", { name: "@jichcha_info" })).toHaveAttribute("href", "https://t.me/jichcha_info");
  await expect(footer.getByRole("link", { name: "jichchainfo@gmail.com" })).toHaveAttribute("href", "mailto:jichchainfo@gmail.com");
  await expect(footer.getByRole("link", { name: "DOCX → PDF" })).toHaveCount(0);
  await expect(footer).toContainText(`© ${new Date().getFullYear()} jichcha.`);
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

test("a suggestion is sent from the feedback page", async ({ page }) => {
  await page.goto("/en/feedback");
  await expect(page.getByText("Complaint", { exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("Fill in this field.")).toBeVisible();
  await page.getByLabel("Your message").fill("The download button did nothing on my phone.");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByRole("status")).toContainText("Thank you, your message is on its way.");
});
