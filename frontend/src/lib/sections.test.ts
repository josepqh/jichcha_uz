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
