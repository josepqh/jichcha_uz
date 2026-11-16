import { execSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "@playwright/test";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
// How to run manage.py for the stack under test (Docker: "docker compose exec -T backend python manage.py").
const MANAGE = process.env.E2E_MANAGE ?? `${ROOT}/backend/.venv/bin/python ${ROOT}/backend/manage.py`;
const ADMIN = { email: "e2e-admin@example.com", password: "E2e-admin-pass-917" };

test.beforeAll(() => {
  try {
    execSync(`${MANAGE} createsuperuser --noinput --email ${ADMIN.email}`, {
      cwd: ROOT,
      env: { ...process.env, DJANGO_SUPERUSER_PASSWORD: ADMIN.password, DJANGO_SUPERUSER_EMAIL: ADMIN.email },
      stdio: "pipe",
    });
  } catch {
    // Already exists from an earlier run.
  }
});

async function signIn(page: import("@playwright/test").Page, email: string, password: string) {
  await page.goto("/en/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/en\/account$/, { timeout: 15_000 }); // Argon2 sign-in is slow under load
}

// Desktop and mobile run in parallel: each switches a different tool so they don't race.
const TOOL = { desktop: { slug: "pdf-merge", name: "Merge PDF" }, mobile: { slug: "pdf-split", name: "Split PDF" } };

test("staff see the panel; switching a tool off hides it from the site", async ({ page }, testInfo) => {
  const tool = TOOL[testInfo.project.name as keyof typeof TOOL];
  await signIn(page, ADMIN.email, ADMIN.password);
  await page.getByRole("link", { name: "Admin panel" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Admin panel" })).toBeVisible();
  await expect(page.getByText("Tasks", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "30 days" }).click();
  await expect(page.getByRole("heading", { name: "Tasks per day" })).toBeVisible();

  await page.getByRole("link", { name: "Load" }).click();
  await expect(page.getByRole("heading", { name: "Queues" })).toBeVisible();

  await page.getByRole("link", { name: "Tools" }).click();
  const toggle = page.getByRole("switch", { name: `${tool.name} on` });
  const saved = page.waitForResponse((r) => r.url().includes(`/admin/tools/${tool.slug}/`) && r.ok());
  // Controlled by the query cache, which re-renders a tick later; assert with a retrying expect.
  await toggle.click();
  await expect(toggle).not.toBeChecked();
  await saved;
  // Full page loads restore the session with a refresh call; let it land before the next load.
  const refreshed = page.waitForResponse((r) => r.url().includes("/auth/refresh/"));
  await page.goto(`/en/tools/${tool.slug}`);
  await refreshed;
  await expect(page.getByRole("status")).toHaveText("This tool is turned off for now. Please try again later.");

  await page.goto("/en/admin/tools");
  await page.getByRole("switch", { name: `${tool.name} on` }).click();
  await expect(page.getByRole("switch", { name: `${tool.name} on` })).toBeChecked();
});

test("ordinary users get a 404 instead of the panel", async ({ page }) => {
  const email = `e2e-${crypto.randomUUID()}@example.com`;
  await page.goto("/en/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill("Str0ng-pass-123");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/en\/account$/, { timeout: 15_000 }); // Argon2 sign-in is slow under load
  await expect(page.getByRole("link", { name: "Admin panel" })).toHaveCount(0);
  await page.goto("/en/admin");
  await expect(page.getByRole("heading", { name: "Page not found" })).toBeVisible();
});
