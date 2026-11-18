import { execSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const VENV_PYTHON = `${ROOT}/backend/.venv/bin/python`;
// How to run manage.py for the stack under test (Docker: "docker compose exec -T backend python manage.py").
// Falls back to the system Python when there is no local virtualenv (CI installs packages globally).
const MANAGE =
  process.env.E2E_MANAGE ?? `${existsSync(VENV_PYTHON) ? VENV_PYTHON : "python"} ${ROOT}/backend/manage.py`;

/** Runs a manage.py command against the backend under test and returns its stdout. */
export function manage(args: string, env: Record<string, string> = {}): string {
  return execSync(`${MANAGE} ${args}`, { cwd: ROOT, env: { ...process.env, ...env }, stdio: "pipe" }).toString();
}

/** Runs Python inside Django (`manage.py shell -c`) and returns the last line it prints. Input goes in E2E_ARG. */
export function djangoShell(code: string, arg = ""): string {
  const lines = manage(`shell --no-imports -c ${JSON.stringify(code)}`, { E2E_ARG: arg })
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  return lines.at(-1) ?? "";
}
