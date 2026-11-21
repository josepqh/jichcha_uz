import { createHmac } from "node:crypto";

import { expect, test, type Page } from "./test";

import { djangoShell } from "./manage";

const PASSWORD = "Str0ng-pass-123";

function base32(secret: string): Buffer {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const ch of secret.replace(/=+$/, "")) bits += alphabet.indexOf(ch).toString(2).padStart(5, "0");
  const bytes = bits.match(/.{8}/g) ?? [];
  return Buffer.from(bytes.map((b) => parseInt(b, 2)));
}

/** RFC 6238 code, `offset` steps of 30 s from now (the server allows one step of drift). */
function totp(secret: string, offset = 0): string {
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30_000) + offset));
  const digest = createHmac("sha1", base32(secret)).update(counter).digest();
  const at = digest[digest.length - 1] & 0x0f;
  return String((digest.readUInt32BE(at) & 0x7fffffff) % 1_000_000).padStart(6, "0");
}

async function register(page: Page): Promise<string> {
  const email = `e2e-${crypto.randomUUID()}@example.com`;
  await page.goto("/en/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/en\/account$/, { timeout: 15_000 });
  return email;
}

function verifyLink(email: string): string {
  const token = djangoShell(
    "import os; from apps.users.models import User; from apps.users.verification import make_token; " +
      "print(make_token(User.objects.get(email=os.environ['E2E_ARG'])))",
    email,
  );
  return `/en/verify-email/${token}`;
}

test("the emailed link confirms the address", async ({ page }) => {
  const email = await register(page);
  await expect(page.getByText("Email not verified yet")).toBeVisible();
  await page.getByRole("button", { name: "Send again" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Sent." })).toBeVisible();

  await page.goto(verifyLink(email));
  await expect(page.getByRole("status")).toHaveText("Your email is confirmed. Thank you!");
  await page.getByRole("link", { name: "Go to your account" }).click();
  await expect(page.getByText("Email verified")).toBeVisible();
});

test("changing the password keeps you signed in here", async ({ page }) => {
  const email = await register(page);
  const security = page.getByRole("region", { name: "Security" });
  await security.getByLabel("Current password").fill("wrong-pass-0");
  await security.getByLabel("New password").fill("An0ther-strong-pass");
  await security.getByRole("button", { name: "Change password" }).click();
  await expect(security.getByText("That password is wrong.")).toBeVisible();

  await security.getByLabel("Current password").fill(PASSWORD);
  await security.getByLabel("New password").fill("An0ther-strong-pass");
  await security.getByRole("button", { name: "Change password" }).click();
  await expect(security.getByRole("status")).toContainText("Password changed.");

  await page.reload();
  await expect(page.getByRole("heading", { level: 1, name: "Account" })).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.goto("/en/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill("An0ther-strong-pass");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/en\/account$/, { timeout: 15_000 });
});

test("two-step sign-in: set up, sign in with a code; a spent code cannot turn it off", async ({ page }) => {
  const email = await register(page);
  await page.goto(verifyLink(email));
  await expect(page.getByRole("status")).toHaveText("Your email is confirmed. Thank you!");
  await page.goto("/en/account#security");

  const security = page.getByRole("region", { name: "Security" });
  await security.getByRole("button", { name: "Turn on" }).click();
  await expect(security.getByRole("img", { name: "QR code for the authenticator app" })).toBeVisible();
  const secret = (await security.locator("code").textContent()) ?? "";
  await security.getByLabel("Code from the app").fill(totp(secret));
  await security.getByRole("button", { name: "Confirm and turn on" }).click();
  await expect(security.getByText("On. Every sign-in asks for a code")).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();
  await page.goto("/en/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Two-step sign-in is on for this account.")).toBeVisible({ timeout: 15_000 });
  await page.getByLabel("Code from the app").fill("000000");
  await page.getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByText("That code is not right")).toBeVisible();
  // The code that switched it on is spent; the next step's code is still within the allowed drift.
  const loginCode = totp(secret, 1);
  await page.getByLabel("Code from the app").fill(loginCode);
  await page.getByRole("button", { name: "Confirm" }).click();
  await expect(page).toHaveURL(/\/en\/account$/, { timeout: 15_000 });

  await security.getByRole("button", { name: "Turn off" }).click();
  await security.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await security.getByLabel("Code from the app").fill(loginCode);
  await security.getByRole("button", { name: "Turn off" }).click();
  // Same code again: refused, because each code works once.
  await expect(security.getByText("That code is not right")).toBeVisible();
});
