import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "@playwright/test";

const fixture = (name: string) => path.join(path.dirname(fileURLToPath(import.meta.url)), "fixtures", name);

test("unlocks a PDF with its password; a wrong one is explained", async ({ page }) => {
  await page.goto("/en/tools/pdf-unlock");
  await page.getByTestId("file-input").setInputFiles(fixture("locked.pdf"));
  const password = page.getByLabel("Password");
  await expect(password).toHaveAttribute("type", "password");

  await page.getByRole("button", { name: "Remove password" }).click();
  await expect(page.getByText("Fill in this field.")).toBeVisible();

  await password.fill("not-it");
  await page.getByRole("button", { name: "Remove password" }).click();
  await expect(page.getByRole("alert")).toContainText("That password is wrong.", { timeout: 20_000 });

  await page.getByRole("button", { name: /Try again|Start over with new files/ }).first().click();
  await page.getByTestId("file-input").setInputFiles(fixture("locked.pdf"));
  await page.getByLabel("Password").fill("user-pass");
  await page.getByRole("button", { name: "Remove password" }).click();
  await expect(page.getByText("locked-unlocked.pdf", { exact: true })).toBeVisible({ timeout: 20_000 });
});
