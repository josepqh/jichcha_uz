import { describe, expect, it } from "vitest";

import { buildCatalog, familyOf, FAMILY_FORMATS, FAMILIES } from "./catalog";
import { TOOL_LIST, TOOLS } from "./tools";

const catalog = buildCatalog();
const keysOf = (family: string) => catalog.find((s) => s.family === family)?.entries.map((e) => e.key) ?? [];

describe("buildCatalog", () => {
  it("puts each item in the section of the file the user has", () => {
    expect(keysOf("pdf")).toEqual(["pdf-merge", "pdf-split", "pdf-organize", "pdf-compress", "pdf-to-images", "pdf-unlock"]);
    expect(keysOf("word")).toEqual(["docx-to-pdf"]);
    expect(keysOf("excel")).toEqual(["xlsx-to-pdf"]);
    expect(keysOf("powerpoint")).toEqual(["pptx-to-pdf"]);
    expect(keysOf("image")).toEqual(["images-to-pdf", "image-convert", "image-edit", "image-compress"]);
    expect(keysOf("archive")).toEqual(["archive-extract", "archive-create", "archive-convert"]);
  });

  it("never files an item under a family it doesn't read", () => {
    for (const { family, entries } of catalog) {
      for (const entry of entries) {
        if (entry.kind === "conversion") {
          expect(familyOf(entry.pair.split("-to-")[0]!)).toBe(family);
        } else if (!entry.tool.home) {
          expect(entry.tool.inputs.every((f) => familyOf(f) === family), entry.key).toBe(true);
        }
      }
    }
  });

  it("reaches every tool and lists nothing twice in a section", () => {
    const reached = new Set(catalog.flatMap((s) => s.entries.map((e) => e.tool.slug)));
    expect([...reached].toSorted()).toEqual(TOOL_LIST.map((t) => t.slug).toSorted());
    for (const { entries } of catalog) expect(new Set(entries.map((e) => e.key)).size).toBe(entries.length);
  });

  it("links conversion cards to pages that resolve to the right tool", () => {
    const wordToPdf = catalog.flatMap((s) => s.entries).find((e) => e.key === "docx-to-pdf");
    expect(wordToPdf).toMatchObject({ kind: "conversion", family: "word", to: "pdf", tool: TOOLS["office-to-pdf"] });
  });

  it("adds a new tool to the right section without touching the catalog", () => {
    const fake = { ...TOOLS["pdf-compress"], slug: "pdf-compress" as const, inputs: ["xlsx", "csv"] };
    const sections = buildCatalog([fake]);
    expect(sections.map((s) => s.family)).toEqual(["excel"]);
  });

  it("knows every format of every family exactly once", () => {
    const all = FAMILIES.flatMap((f) => FAMILY_FORMATS[f]);
    expect(new Set(all).size).toBe(all.length);
  });
});
