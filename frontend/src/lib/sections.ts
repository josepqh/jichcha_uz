/**
 * Site sections: one per file family, each at /{lang}/{slug} and in the section bar under the header.
 * A section page lists only the catalog entries of its family (lib/catalog.ts decides which).
 */
import { buildCatalog, familyOf, FAMILIES, FAMILY_FORMATS, type CatalogEntry } from "./catalog";
import { resolveConversion, TOOLS, type Family } from "./tools";

export const SECTION_SLUG: Record<Family, string> = {
  pdf: "pdf",
  word: "word",
  excel: "excel",
  powerpoint: "powerpoint",
  image: "images",
  archive: "archives",
};

/** Tailwind text colour per family (tokens in index.css). */
export const FAMILY_TEXT: Record<Family, string> = {
  pdf: "text-fam-pdf",
  word: "text-fam-word",
  excel: "text-fam-excel",
  powerpoint: "text-fam-powerpoint",
  image: "text-fam-image",
  archive: "text-fam-archive",
};

export const FAMILY_BG: Record<Family, string> = {
  pdf: "bg-fam-pdf",
  word: "bg-fam-word",
  excel: "bg-fam-excel",
  powerpoint: "bg-fam-powerpoint",
  image: "bg-fam-image",
  archive: "bg-fam-archive",
};

const CATALOG = buildCatalog();
export const SECTIONS = CATALOG.map((s) => s.family);

export function sectionEntries(family: Family): CatalogEntry[] {
  return CATALOG.find((s) => s.family === family)?.entries ?? [];
}

export function familyForSlug(slug: string | undefined): Family | undefined {
  return FAMILIES.find((family) => SECTION_SLUG[family] === slug);
}

/** Formats shown on a section: the first few, so long lists (archives, images) stay one line. */
export function sectionFormats(family: Family, max = 6): string[] {
  return FAMILY_FORMATS[family].slice(0, max);
}

/**
 * Which section a path belongs to, for the bar's highlight: a section page, a conversion page (by
 * its source format), or a tool that lives in exactly one section.
 */
export function familyForPath(rest: string): Family | undefined {
  const [first, second] = rest.split("/").filter(Boolean);
  if (!first) return undefined;
  if (first === "convert" && second) {
    const conversion = resolveConversion(second);
    return conversion ? familyOf(conversion.from) : undefined;
  }
  if (first === "tools" && second && second in TOOLS) {
    const homes = CATALOG.filter((s) => s.entries.some((e) => e.kind === "tool" && e.tool.slug === second));
    return homes.length === 1 ? homes[0]!.family : undefined;
  }
  return familyForSlug(first);
}

/** Extensions people actually have, mapped to the format keys the catalog uses. */
const ALIASES: Record<string, string> = { jpeg: "jpg", tif: "tiff", heif: "heic", tgz: "gz", tbz2: "bz2", txz: "xz" };

export function formatOf(name: string): string {
  const ext = name.toLowerCase().split(".").pop() ?? "";
  return ALIASES[ext] ?? ext;
}

/** Tools that turn a file into another format (the rest edit or manage files of their own kind). */
const CONVERTERS = new Set(["image-convert", "archive-convert", "pdf-to-images", "images-to-pdf"]);
/** Family a converting tool produces when it leaves its own family. */
const TOOL_OUTPUT: Partial<Record<string, Family>> = { "images-to-pdf": "pdf", "pdf-to-images": "image" };

export interface MenuGroups {
  /** Editing and managing files of this kind: merge, compress, extract… */
  work: CatalogEntry[];
  /** From this kind to another format. */
  from: CatalogEntry[];
  /** From other sections into this kind ("Word → PDF" under PDF). Links to the other section's entry. */
  into: { family: Family; entry: CatalogEntry }[];
}

/** What a section's dropdown shows, worked out from the catalog like the sections themselves. */
export function menuGroups(family: Family, hidden: ReadonlySet<string> = new Set()): MenuGroups {
  const own = sectionEntries(family).filter((e) => !hidden.has(e.tool.slug));
  const isConversion = (e: CatalogEntry) => e.kind === "conversion" || CONVERTERS.has(e.tool.slug);
  const outputOf = (e: CatalogEntry) => (e.kind === "conversion" ? familyOf(e.to) : TOOL_OUTPUT[e.tool.slug]);
  return {
    work: own.filter((e) => !isConversion(e)),
    from: own.filter(isConversion),
    into: SECTIONS.filter((other) => other !== family).flatMap((other) =>
      sectionEntries(other)
        .filter((e) => !hidden.has(e.tool.slug) && outputOf(e) === family)
        .map((entry) => ({ family: other, entry })),
    ),
  };
}
