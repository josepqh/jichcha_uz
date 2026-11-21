import { describe, expect, it } from "vitest";

import { familyOf } from "./catalog";
import { familyForPath, familyForSlug, formatOf, SECTION_SLUG, SECTIONS, sectionEntries, sectionFormats } from "./sections";

describe("sections", () => {
  it("has a page with tools for every family, and slugs map back", () => {
    for (const family of SECTIONS) {
      expect(sectionEntries(family).length).toBeGreaterThan(0);
      expect(familyForSlug(SECTION_SLUG[family])).toBe(family);
    }
    expect(familyForSlug("nope")).toBeUndefined();
    expect(sectionEntries("pdf").every((e) => e.kind === "conversion" || e.tool.inputs.includes("pdf"))).toBe(true);
  });

  it("finds the section of any page", () => {
    expect(familyForPath("/pdf")).toBe("pdf");
    expect(familyForPath("/images")).toBe("image");
    expect(familyForPath("/convert/docx-to-pdf")).toBe("word");
    expect(familyForPath("/convert/xlsx-to-pdf")).toBe("excel");
    expect(familyForPath("/tools/pdf-merge")).toBe("pdf");
    expect(familyForPath("/tools/archive-create")).toBe("archive");
    expect(familyForPath("/tools/office-to-pdf")).toBeUndefined(); // spans three sections
    expect(familyForPath("/convert/nope-to-pdf")).toBeUndefined();
    expect(familyForPath("/faq")).toBeUndefined();
    expect(familyForPath("")).toBeUndefined();
  });

  it("reads formats from file names, aliases included", () => {
    expect(formatOf("Hisobot.DOCX")).toBe("docx");
    expect(formatOf("IMG_0001.jpeg")).toBe("jpg");
    expect(formatOf("scan.TIF")).toBe("tiff");
    expect(formatOf("backup.tar.tgz")).toBe("gz");
    expect(familyOf(formatOf("photo.heif"))).toBe("image");
    expect(sectionFormats("image", 3)).toEqual(["png", "jpg", "webp"]);
  });
});

describe("section menus", () => {
  it("groups PDF like a converter site: into PDF, from PDF, then the kinds of work", async () => {
    const { menuGroups } = await import("./sections");
    const pdf = menuGroups("pdf");
    expect(pdf.into.map((i) => i.family)).toEqual(["word", "excel", "powerpoint", "image", "image"]);
    expect(pdf.into.map((i) => i.entry.key)).toContain("images-to-pdf");
    expect(pdf.from.map((e) => e.key)).toEqual(["pdf-to-images"]);
    const work = Object.fromEntries(pdf.work.map((g) => [g.group, g.entries.map((e) => e.key)]));
    expect(work.organize).toEqual(expect.arrayContaining(["pdf-merge", "pdf-split", "pdf-organize"]));
    expect(work.optimize).toContain("pdf-compress");
    expect(work.security).toContain("pdf-unlock");
  });

  it("every entry lands in exactly one of its own section's groups, and hidden tools drop out", async () => {
    const { menuGroups } = await import("./sections");
    for (const family of SECTIONS) {
      const { work, from } = menuGroups(family);
      const keys = [...work.flatMap((g) => g.entries), ...from].map((e) => e.key);
      expect(keys.toSorted()).toEqual(sectionEntries(family).map((e) => e.key).toSorted());
    }
    expect(menuGroups("image").into.map((i) => i.entry.key)).toEqual(["pdf-to-images"]);
    const pdf = menuGroups("pdf", new Set(["pdf-merge", "office-to-pdf"]));
    expect(pdf.work.flatMap((g) => g.entries).map((e) => e.key)).not.toContain("pdf-merge");
    expect(pdf.into.map((i) => i.family)).toEqual(["image", "image"]);
  });
});
