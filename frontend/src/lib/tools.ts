import type { LucideIcon } from "lucide-react";
import {
  BookOpen,
  Combine,
  FileArchive,
  FileDown,
  FileStack,
  FileText,
  FolderArchive,
  FolderOpen,
  ImageDown,
  Images,
  LayoutGrid,
  Repeat,
  Scissors,
} from "lucide-react";

export type ToolSlug =
  | "image-convert"
  | "image-compress"
  | "images-to-pdf"
  | "office-to-pdf"
  | "pdf-merge"
  | "pdf-split"
  | "pdf-organize"
  | "pdf-compress"
  | "pdf-to-images"
  | "archive-extract"
  | "archive-create"
  | "archive-convert"
  | "ebook-convert";

/** Colour family of the icon. */
export type Category = "image" | "compress" | "pdf" | "office" | "archive" | "ebook";
/** Section on the home page. */
export type Group = "pdf" | "office" | "ebook" | "image" | "archive";

export type OptionValues = Record<string, string>;

export interface OptionField {
  name: string;
  /** Radio choices; omit for a free-text field. */
  choices?: readonly string[];
  /** Only shown (and sent) when another option has this value. */
  showWhen?: { field: string; value: string };
}

export interface ToolDef {
  slug: ToolSlug;
  category: Category;
  group: Group;
  icon: LucideIcon;
  /** File picker hint. The server detects the real format from file content. */
  accept: string;
  /** Formats shown to the user in the drop zone; empty when any file is accepted. */
  formats: string;
  minFiles: number;
  /** Hard cap regardless of the account limit. */
  maxFiles?: number;
  /** Page order matters for this tool: show move up/down controls. */
  reorder: boolean;
  /** Custom editor instead of the file list (page organizer). */
  editor?: "organize";
  fields: readonly OptionField[];
  defaults: OptionValues;
}

const IMAGE_ACCEPT =
  "image/png,image/jpeg,image/webp,image/gif,image/bmp,image/tiff,image/avif,image/heic,image/heif,.heic,.heif";
const IMAGE_FORMATS = "PNG, JPG, WEBP, HEIC, AVIF, GIF, BMP, TIFF";
const PDF_ACCEPT = "application/pdf,.pdf";
const OFFICE_ACCEPT = ".doc,.docx,.odt,.rtf,.xls,.xlsx,.ods,.csv,.ppt,.pptx,.odp";
const OFFICE_FORMATS = "DOCX, DOC, ODT, RTF, XLSX, XLS, ODS, CSV, PPTX, PPT, ODP";
const ARCHIVE_ACCEPT = ".zip,.rar,.7z,.tar,.gz,.tgz,.bz2,.tbz2,.xz,.txz";
const ARCHIVE_FORMATS = "ZIP, RAR, 7Z, TAR, GZ, BZ2, XZ";
const EBOOK_ACCEPT = ".epub,.mobi,.azw3,.fb2,.pdf,.docx";
const EBOOK_FORMATS = "EPUB, MOBI, AZW3, FB2, PDF, DOCX";
export const EBOOK_TARGETS = ["epub", "mobi", "azw3", "pdf"] as const;

export const CONVERT_TARGETS = ["jpg", "png", "webp", "avif", "gif", "bmp", "tiff"] as const;
const LEVELS = ["strong", "medium", "light"] as const;

export const TOOLS: Record<ToolSlug, ToolDef> = {
  "pdf-merge": {
    slug: "pdf-merge",
    category: "pdf",
    group: "pdf",
    icon: Combine,
    accept: PDF_ACCEPT,
    formats: "PDF",
    minFiles: 2,
    maxFiles: 50,
    reorder: true,
    fields: [],
    defaults: {},
  },
  "pdf-split": {
    slug: "pdf-split",
    category: "pdf",
    group: "pdf",
    icon: Scissors,
    accept: PDF_ACCEPT,
    formats: "PDF",
    minFiles: 1,
    maxFiles: 1,
    reorder: false,
    fields: [{ name: "mode", choices: ["each", "ranges"] }, { name: "ranges", showWhen: { field: "mode", value: "ranges" } }],
    defaults: { mode: "each", ranges: "" },
  },
  "pdf-organize": {
    slug: "pdf-organize",
    category: "pdf",
    group: "pdf",
    icon: LayoutGrid,
    accept: PDF_ACCEPT,
    formats: "PDF",
    minFiles: 1,
    maxFiles: 1,
    reorder: false,
    editor: "organize",
    fields: [],
    defaults: {},
  },
  "pdf-compress": {
    slug: "pdf-compress",
    category: "compress",
    group: "pdf",
    icon: FileDown,
    accept: PDF_ACCEPT,
    formats: "PDF",
    minFiles: 1,
    maxFiles: 10,
    reorder: false,
    fields: [{ name: "pdfLevel", choices: LEVELS }],
    defaults: { pdfLevel: "medium" },
  },
  "pdf-to-images": {
    slug: "pdf-to-images",
    category: "pdf",
    group: "pdf",
    icon: Images,
    accept: PDF_ACCEPT,
    formats: "PDF",
    minFiles: 1,
    maxFiles: 1,
    reorder: false,
    fields: [
      { name: "format", choices: ["jpg", "png"] },
      { name: "quality", choices: ["low", "medium", "high"] },
    ],
    defaults: { format: "jpg", quality: "medium" },
  },
  "images-to-pdf": {
    slug: "images-to-pdf",
    category: "pdf",
    group: "pdf",
    icon: FileStack,
    accept: IMAGE_ACCEPT,
    formats: IMAGE_FORMATS,
    minFiles: 1,
    maxFiles: 100,
    reorder: true,
    fields: [
      { name: "page_size", choices: ["a4", "letter", "fit"] },
      { name: "orientation", choices: ["auto", "portrait", "landscape"] },
      { name: "margin", choices: ["none", "small", "large"] },
    ],
    defaults: { page_size: "a4", orientation: "auto", margin: "small" },
  },
  "office-to-pdf": {
    slug: "office-to-pdf",
    category: "office",
    group: "office",
    icon: FileText,
    accept: OFFICE_ACCEPT,
    formats: OFFICE_FORMATS,
    minFiles: 1,
    maxFiles: 10,
    reorder: false,
    fields: [],
    defaults: {},
  },
  "ebook-convert": {
    slug: "ebook-convert",
    category: "ebook",
    group: "ebook",
    icon: BookOpen,
    accept: EBOOK_ACCEPT,
    formats: EBOOK_FORMATS,
    minFiles: 1,
    maxFiles: 5,
    reorder: false,
    fields: [{ name: "target", choices: EBOOK_TARGETS }],
    defaults: { target: "epub" },
  },
  "archive-extract": {
    slug: "archive-extract",
    category: "archive",
    group: "archive",
    icon: FolderOpen,
    accept: ARCHIVE_ACCEPT,
    formats: ARCHIVE_FORMATS,
    minFiles: 1,
    maxFiles: 1,
    reorder: false,
    fields: [],
    defaults: {},
  },
  "archive-create": {
    slug: "archive-create",
    category: "archive",
    group: "archive",
    icon: FolderArchive,
    accept: "",
    formats: "",
    minFiles: 1,
    reorder: false,
    fields: [{ name: "archiveFormat", choices: ["zip", "7z"] }],
    defaults: { archiveFormat: "zip" },
  },
  "archive-convert": {
    slug: "archive-convert",
    category: "archive",
    group: "archive",
    icon: FileArchive,
    accept: ARCHIVE_ACCEPT,
    formats: ARCHIVE_FORMATS,
    minFiles: 1,
    maxFiles: 5,
    reorder: false,
    fields: [{ name: "target", choices: ["zip", "7z"] }],
    defaults: { target: "zip" },
  },
  "image-convert": {
    slug: "image-convert",
    category: "image",
    group: "image",
    icon: Repeat,
    accept: IMAGE_ACCEPT,
    formats: IMAGE_FORMATS,
    minFiles: 1,
    reorder: false,
    fields: [{ name: "target", choices: CONVERT_TARGETS }],
    defaults: { target: "jpg" },
  },
  "image-compress": {
    slug: "image-compress",
    category: "compress",
    group: "image",
    icon: ImageDown,
    accept: IMAGE_ACCEPT,
    formats: IMAGE_FORMATS,
    minFiles: 1,
    reorder: false,
    fields: [{ name: "level", choices: LEVELS }],
    defaults: { level: "medium" },
  },
};

export const TOOL_LIST: ToolDef[] = Object.values(TOOLS);
export const GROUPS: Group[] = ["pdf", "office", "ebook", "image", "archive"];

/** UI option names that differ from the API's (same API name, different choices and labels). */
const API_NAMES: Record<string, string> = { pdfLevel: "level", archiveFormat: "format" };

export function isFieldVisible(field: OptionField, values: OptionValues): boolean {
  return !field.showWhen || values[field.showWhen.field] === field.showWhen.value;
}

/** Only visible fields are sent, under their API names. */
export function toApiOptions(tool: ToolDef, values: OptionValues): Record<string, string> {
  const out: Record<string, string> = {};
  for (const field of tool.fields) {
    const value = values[field.name];
    if (value !== undefined && isFieldVisible(field, values)) out[API_NAMES[field.name] ?? field.name] = value;
  }
  return out;
}

export function isToolSlug(value: string | undefined): value is ToolSlug {
  return value !== undefined && value in TOOLS;
}

const IMAGE_INPUTS = ["png", "jpg", "webp", "heic", "avif", "gif", "bmp", "tiff"] as const;
const OFFICE_INPUTS = ["docx", "doc", "odt", "rtf", "xlsx", "xls", "ods", "csv", "pptx", "ppt", "odp"] as const;
const ARCHIVE_INPUTS = ["zip", "rar", "7z", "tar", "gz", "bz2", "xz"] as const;
const ARCHIVE_TARGETS = ["zip", "7z"] as const;
const EBOOK_INPUTS = ["epub", "mobi", "azw3", "fb2", "pdf", "docx"] as const;

export interface Conversion {
  pair: string;
  from: string;
  to: string;
  tool: ToolSlug;
  options: OptionValues;
}

const includes = (list: readonly string[], value: string) => list.includes(value);

/** Parses SEO pairs like "heic-to-jpg", "docx-to-pdf", "pdf-to-png", "rar-to-zip" or "epub-to-pdf". */
export function resolveConversion(pair: string | undefined): Conversion | null {
  const match = /^([a-z0-9]+)-to-([a-z0-9]+)$/.exec(pair ?? "");
  if (!match) return null;
  const [, from = "", to = ""] = match;
  if (from === to) return null;
  const base = { pair: `${from}-to-${to}`, from, to };
  if (includes(IMAGE_INPUTS, from)) {
    if (to === "pdf") return { ...base, tool: "images-to-pdf", options: TOOLS["images-to-pdf"].defaults };
    if (includes(CONVERT_TARGETS, to)) return { ...base, tool: "image-convert", options: { target: to } };
  }
  if (includes(OFFICE_INPUTS, from) && to === "pdf") return { ...base, tool: "office-to-pdf", options: {} };
  if (from === "pdf" && (to === "jpg" || to === "png")) {
    return { ...base, tool: "pdf-to-images", options: { ...TOOLS["pdf-to-images"].defaults, format: to } };
  }
  if (includes(ARCHIVE_INPUTS, from) && includes(ARCHIVE_TARGETS, to)) {
    return { ...base, tool: "archive-convert", options: { target: to } };
  }
  if (includes(EBOOK_INPUTS, from) && includes(EBOOK_TARGETS, to)) {
    return { ...base, tool: "ebook-convert", options: { target: to } };
  }
  return null;
}

export const POPULAR_CONVERSIONS = [
  "docx-to-pdf",
  "xlsx-to-pdf",
  "pptx-to-pdf",
  "pdf-to-jpg",
  "heic-to-jpg",
  "png-to-jpg",
  "jpg-to-png",
  "webp-to-jpg",
  "jpg-to-pdf",
  "png-to-pdf",
  "heic-to-pdf",
  "pdf-to-png",
  "epub-to-pdf",
  "fb2-to-epub",
  "epub-to-mobi",
  "rar-to-zip",
] as const;

export const CATEGORY_COLOR: Record<Category, string> = {
  image: "text-cat-image",
  compress: "text-cat-compress",
  pdf: "text-cat-pdf",
  office: "text-cat-office",
  archive: "text-cat-archive",
  ebook: "text-cat-ebook",
};
