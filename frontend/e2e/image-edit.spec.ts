import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "@playwright/test";

const fixture = (name: string) => path.join(path.dirname(fileURLToPath(import.meta.url)), "fixtures", name);

test("crops a photo to a square, rotates it and saves it as WEBP", async ({ page }) => {
  await page.goto("/en/tools/image-edit");
  await page.getByTestId("file-input").setInputFiles(fixture("photo.png"));
  await page.getByText("1:1 square", { exact: true }).click();
  const area = page.getByRole("slider", { name: "Crop area" });
  await expect(area).toBeVisible();
  // Keyboard works too: nudge the box, then rotate.
  await area.focus();
  await page.keyboard.press("ArrowLeft");
  await page.getByRole("button", { name: "Rotate right" }).click();
  await expect(page.getByText("Rotation: 90°")).toBeVisible();
  await page.getByText("WEBP", { exact: true }).click();

  const created = page.waitForResponse((r) => r.url().endsWith("/api/v1/tasks/") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Apply" }).click();
  const { options } = await (await created).json();
  expect(options).toMatchObject({ aspect: "1:1", rotate: 90, format: "webp" });
  expect(options.crop.w).toBeGreaterThan(0);
  await expect(page.getByText("Done")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("photo-edited.webp")).toBeVisible();
});

test("asks for a size before resizing in pixels", async ({ page }) => {
  await page.goto("/en/tools/image-edit");
  await page.getByTestId("file-input").setInputFiles(fixture("photo.png"));
  await page.getByText("In pixels", { exact: true }).click();
  await page.getByRole("button", { name: "Apply" }).click();
  await expect(page.getByRole("alert")).toContainText("Enter a width or a height.");
});
