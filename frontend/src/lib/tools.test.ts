import { describe, expect, it } from "vitest";

import { TOOLS, toApiOptions } from "./tools";

describe("toApiOptions", () => {
  it("drops hidden fields", () => {
    expect(toApiOptions(TOOLS["pdf-split"], { mode: "each", ranges: "1-2" })).toEqual({ mode: "each" });
    expect(toApiOptions(TOOLS["pdf-split"], { mode: "ranges", ranges: "1-2" })).toEqual({ mode: "ranges", ranges: "1-2" });
  });
  it("renames UI-only option names to API names", () => {
    expect(toApiOptions(TOOLS["pdf-compress"], { pdfLevel: "strong" })).toEqual({ level: "strong" });
    expect(toApiOptions(TOOLS["archive-create"], { archiveFormat: "7z" })).toEqual({ format: "7z" });
  });
});

describe("translations", () => {
  it("cover every tool, option choice and group in all languages", async () => {
    const { GROUPS } = await import("./tools");
    for (const lang of ["uz", "ru", "en"]) {
      const dict = (await import(`../i18n/locales/${lang}.json`)).default;
      for (const tool of Object.values(TOOLS)) {
        expect(dict.tools[tool.slug]?.name, `${lang} tools.${tool.slug}`).toBeTruthy();
        expect(dict.actions[tool.slug], `${lang} actions.${tool.slug}`).toBeTruthy();
        for (const field of tool.fields) {
          for (const choice of field.choices ?? []) {
            expect(dict.options[field.name]?.choices?.[choice], `${lang} options.${field.name}.${choice}`).toBeTruthy();
          }
        }
      }
      for (const group of GROUPS) expect(dict.home.groups[group], `${lang} group ${group}`).toBeTruthy();
    }
  });
});
