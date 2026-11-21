// Every locale must have English's keys (admin may fall back to English), the same {{placeholders}}
// and the same <tags> in each string. Plural keys may differ by language (_one, _few, _other, ...).
import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const dir = path.join(path.dirname(fileURLToPath(import.meta.url)), "../src/i18n/locales");
const load = (code) => JSON.parse(readFileSync(path.join(dir, `${code}.json`), "utf8"));
const PLURAL = /_(zero|one|two|few|many|other)$/;
const OPTIONAL_TOP = new Set(["admin"]);

function flatten(value, prefix = "", out = new Map()) {
  if (Array.isArray(value)) value.forEach((v, i) => flatten(v, `${prefix}[${i}]`, out));
  else if (value && typeof value === "object") for (const [k, v] of Object.entries(value)) flatten(v, prefix ? `${prefix}.${k}` : k, out);
  else out.set(prefix, String(value));
  return out;
}
const marks = (s) => [...s.matchAll(/\{\{\s*(\w+)\s*\}\}|<\/?(\w+)>/g)].map((m) => m[1] ?? `<${m[2]}>`).toSorted().join(",");

const en = flatten(load("en"));
const enBase = new Map();
for (const [k, v] of en) enBase.set(k.replace(PLURAL, ""), v);
let failed = 0;
for (const file of readdirSync(dir).filter((f) => f.endsWith(".json"))) {
  const code = file.replace(".json", "");
  if (code === "en") continue;
  const other = flatten(load(code));
  const base = new Map();
  for (const [k, v] of other) base.set(k.replace(PLURAL, ""), v);
  const problems = [];
  for (const [key, text] of enBase) {
    if (OPTIONAL_TOP.has(key.split(".")[0])) continue;
    if (!base.has(key)) problems.push(`missing ${key}`);
    else if (marks(base.get(key)) !== marks(text)) problems.push(`placeholders differ in ${key}: ${marks(base.get(key))} vs ${marks(text)}`);
  }
  for (const key of base.keys()) if (!enBase.has(key)) problems.push(`extra ${key}`);
  if (problems.length) {
    failed += problems.length;
    console.log(`${code}: ${problems.length} problem(s)\n  ${problems.slice(0, 15).join("\n  ")}`);
  } else console.log(`${code}: ok`);
}
process.exit(failed ? 1 : 0);
