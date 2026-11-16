/**
 * Home page sections, built from the tool registry instead of by hand.
 *
 * Rule: an item lives in the section of the file the user has (its input family).
 * - A tool whose inputs all belong to one family is a tool card there ("Merge PDF" in PDF).
 * - A tool that takes several families (Office → PDF takes Word, Excel and PowerPoint) gets one
 *   "Family → output" card per family ("Word → PDF" in Word, "Excel → PDF" in Excel), linking to
 *   the conversion page. If it names a `home` family, it is a tool card there instead.
 * So the PDF section holds only work on PDF files, the Word section only work on Word files, etc.
 */
import type { LucideIcon } from "lucide-react";
import { BookOpen, FileArchive, FileImage, FileSpreadsheet, FileText, Presentation } from "lucide-react";

import {
  ARCHIVE_INPUTS,
  IMAGE_INPUTS,
  resolveConversion,
  TOOL_LIST,
  TOOLS,
  type Family,
  type ToolDef,
} from "./tools";

export const FAMILIES: readonly Family[] = ["pdf", "word", "excel", "powerpoint", "image", "ebook", "archive"];

export const FAMILY_FORMATS: Record<Family, readonly string[]> = {
  pdf: ["pdf"],
  word: ["docx", "doc", "odt", "rtf"],
  excel: ["xlsx", "xls", "ods", "csv"],
  powerpoint: ["pptx", "ppt", "odp"],
  image: IMAGE_INPUTS,
  ebook: ["epub", "mobi", "azw3", "fb2"],
  archive: ARCHIVE_INPUTS,
};

/** Format used in links for a family: "Word → PDF" opens /convert/docx-to-pdf. */
const REPRESENTATIVE: Record<Family, string> = {
  pdf: "pdf",
  word: "docx",
  excel: "xlsx",
  powerpoint: "pptx",
  image: "jpg",
  ebook: "epub",
  archive: "rar",
};

export const FAMILY_ICON: Record<Family, LucideIcon> = {
  pdf: FileText,
  word: FileText,
  excel: FileSpreadsheet,
  powerpoint: Presentation,
  image: FileImage,
  ebook: BookOpen,
  archive: FileArchive,
};

export function familyOf(format: string): Family | undefined {
  return FAMILIES.find((family) => FAMILY_FORMATS[family].includes(format));
}

export type CatalogEntry =
  | { kind: "tool"; key: string; tool: ToolDef }
  | { kind: "conversion"; key: string; tool: ToolDef; family: Family; to: string; pair: string };

export interface CatalogSection {
  family: Family;
  entries: CatalogEntry[];
}

function familiesOf(tool: ToolDef): Family[] {
  const found = new Set<Family>();
  for (const format of tool.inputs) {
    const family = familyOf(format);
    if (family) found.add(family);
  }
  return FAMILIES.filter((family) => found.has(family));
}

export function buildCatalog(tools: readonly ToolDef[] = TOOL_LIST): CatalogSection[] {
  const sections = new Map<Family, CatalogEntry[]>(FAMILIES.map((family) => [family, []]));
  const add = (family: Family, entry: CatalogEntry) => {
    const list = sections.get(family)!;
    if (!list.some((e) => e.key === entry.key)) list.push(entry);
  };

  for (const tool of tools) {
    const families = familiesOf(tool);
    const home = tool.home ?? (families.length === 1 ? families[0] : undefined);
    if (home) add(home, { kind: "tool", key: tool.slug, tool });

    const to = tool.primaryOutput;
    if (!to) continue;
    for (const family of families) {
      if (family === home || familyOf(to) === family) continue;
      const pair = `${REPRESENTATIVE[family]}-to-${to}`;
      const conversion = resolveConversion(pair);
      if (!conversion) continue;
      add(family, { kind: "conversion", key: pair, tool: TOOLS[conversion.tool], family, to, pair });
    }
  }

  return FAMILIES.map((family) => ({ family, entries: sections.get(family)! })).filter((s) => s.entries.length);
}
