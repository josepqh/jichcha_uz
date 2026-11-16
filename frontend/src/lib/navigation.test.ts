import { describe, expect, it } from "vitest";

import { safeNext } from "./navigation";

describe("safeNext", () => {
  it("keeps internal paths", () => {
    expect(safeNext("/ru/tools/image-compress", "ru")).toBe("/ru/tools/image-compress");
  });
  it.each(["https://evil.example", "//evil.example", "/\\evil.example", null, ""])("falls back for %s", (raw) => {
    expect(safeNext(raw, "uz")).toBe("/uz/account");
  });
});
