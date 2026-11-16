import { expect, test, type Page } from "@playwright/test";

const PASSWORD = "Str0ng-e2e-pass!";

function uniqueEmail(testId: string) {
  return `e2e-${testId.slice(0, 8)}-${crypto.randomUUID().slice(0, 8)}@example.com`;
}

async function register(page: Page, email: string) {
  await page.goto("/en/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/en\/account$/);
}

test.describe("accounts", () => {
  test("register, keep the session after reload, sign out and sign back in", async ({ page }, info) => {
    const email = uniqueEmail(info.testId);
    await register(page, email);
    await expect(page.getByRole("heading", { level: 1, name: "Account" })).toBeVisible();
    await expect(page.getByText(email)).toBeVisible();
    await expect(page.getByText("No tasks yet.")).toBeVisible();

    await page.reload(); // session restored from the httpOnly refresh cookie
    await expect(page.getByText(email)).toBeVisible();

    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/en$/);
    await expect(page.getByRole("link", { name: "Sign in" })).toBeVisible();

    await page.goto("/en/account");
    await expect(page).toHaveURL(/\/en\/login\?next=%2Fen%2Faccount$/);
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).toHaveURL(/\/en\/account$/);
  });

  test("shows field errors and a generic message for wrong credentials", async ({ page }) => {
    await page.goto("/en/login");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByLabel("Email")).toBeFocused();
    await expect(page.getByText("Fill in this field.").first()).toBeVisible();

    await page.getByLabel("Email").fill("nobody@example.com");
    await page.getByLabel("Password", { exact: true }).fill("wrong-password-1");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("alert")).toHaveText("Wrong email or password.");
  });

  test("rejects a weak password with reasons next to the field", async ({ page }, info) => {
    await page.goto("/en/register");
    await page.getByLabel("Email").fill(uniqueEmail(info.testId));
    await page.getByLabel("Password", { exact: true }).fill("password123");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByText(/The password isn't strong enough: this password is too common/)).toBeVisible();
  });

  test("a signed-in user's conversion shows up in history with a working download", async ({ page }, info) => {
    await register(page, uniqueEmail(info.testId));
    await page.goto("/en/convert/png-to-webp");
    await page.getByTestId("file-input").setInputFiles({
      name: "logo.png",
      mimeType: "image/png",
      buffer: Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
        "base64",
      ),
    });
    await page.getByRole("button", { name: "Convert to WEBP" }).click();
    await expect(page.getByText("Done")).toBeVisible({ timeout: 20_000 });

    await page.goto("/en/account");
    await expect(page.getByText("logo.webp")).toBeVisible();
    const download = page.waitForEvent("download");
    await page.getByRole("link", { name: "Download logo.webp" }).click();
    expect((await download).suggestedFilename()).toBe("logo.webp");
  });

  test("deleting the account signs out and removes it", async ({ page }, info) => {
    const email = uniqueEmail(info.testId);
    await register(page, email);
    await page.getByLabel("Your password, to confirm").fill(PASSWORD);
    page.once("dialog", (dialog) => dialog.accept());
    await page.getByRole("button", { name: "Delete account permanently" }).click();
    await expect(page).toHaveURL(/\/en$/);

    await page.goto("/en/login");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("alert")).toHaveText("Wrong email or password.");
  });

  test("forgot password never reveals whether an account exists", async ({ page }) => {
    await page.goto("/en/forgot");
    await page.getByLabel("Email").fill("ghost-account@example.com");
    await page.getByRole("button", { name: "Send reset link" }).click();
    await expect(page.getByRole("status")).toContainText("If an account exists for ghost-account@example.com");
  });
});
