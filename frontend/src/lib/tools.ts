import type { LucideIcon } from "lucide-react";
import {
  Combine,
  FileMinus,
  FileOutput,
  Hash,
  Lock,
  RotateCw,
  ScanLine,
  Stamp,
  Wrench,
  FileArchive,
  FileDown,
  FileStack,
  FileText,
  FolderArchive,
  FolderOpen,
  ImageDown,
  Crop,
  Images,
  LayoutGrid,
  LockOpen,
  Repeat,
  Scissors,
} from "lucide-react";

export type ToolSlug =
  | "image-convert"
  | "image-edit"
  | "image-compress"
  | "images-to-pdf"
  | "office-to-pdf"
  | "pdf-merge"
  | "pdf-split"
  | "pdf-organize"
  | "pdf-compress"
  | "pdf-to-images"
  | "pdf-unlock"
  | "archive-extract"
  | "archive-create"
  | "archive-convert"
  | "pdf-rotate"
  | "pdf-remove-pages"
  | "pdf-extract-pages"
  | "pdf-page-numbers"
  | "pdf-watermark"
  | "pdf-crop"
  | "pdf-protect"
  | "pdf-repair"
  | "scan-to-pdf";

/** Colour family of the icon. */
export type Category = "image" | "compress" | "pdf" | "office" | "archive";
/** File family: home page sections are built per family (see catalog.ts). */
export type Family = "pdf" | "word" | "excel" | "powerpoint" | "image" | "archive";

export type OptionValues = Record<string, string>;

export interface OptionField {
  name: string;
  /** Radio choices; omit for a free-text field. */
  choices?: readonly string[];
  /** Only shown (and sent) when another option has this value. */
  showWhen?: { field: string; value: string };
  /** A password: masked input, and the backend keeps it out of storage. */
  secret?: boolean;
  /** Must be filled in (checked before upload, when visible). */
  required?: boolean;
  /** Page numbers and ranges like "1-3, 5, 8-" (checked before upload, when visible). */
  pages?: boolean;
}

export interface ToolDef {
  slug: ToolSlug;
  category: Category;
  /** Format keys the tool accepts (empty when any file is accepted). Decides its home page section. */
  inputs: readonly string[];
  /** Section for a tool whose inputs span several families; it shows there as a tool card. */
  home?: Family;
  /** Main output of a multi-family tool: other families get an "X → output" card for it. */
  primaryOutput?: string;
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
  /** Phones open the camera for this tool's file picker (scanning paper). */
  capture?: boolean;
  /** Custom editor next to the file list: PDF page organizer, image crop/rotate/resize. */
  editor?: "organize" | "image";
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
export const IMAGE_INPUTS = ["png", "jpg", "webp", "heic", "avif", "gif", "bmp", "tiff"] as const;
export const OFFICE_INPUTS = ["docx", "doc", "odt", "rtf", "xlsx", "xls", "ods", "csv", "pptx", "ppt", "odp"] as const;
export const ARCHIVE_INPUTS = ["zip", "rar", "7z", "tar", "gz", "bz2", "xz"] as const;
const ARCHIVE_TARGETS = ["zip", "7z"] as const;

export const CONVERT_TARGETS = ["jpg", "png", "webp", "avif", "gif", "bmp", "tiff"] as const;
const LEVELS = ["strong", "medium", "light"] as const;

export const TOOLS: Record<ToolSlug, ToolDef> = {
  "pdf-merge": {
    slug: "pdf-merge",
    category: "pdf",
    inputs: ["pdf"],
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
    inputs: ["pdf"],
    icon: Scissors,
    accept: PDF_ACCEPT,
    formats: "PDF",
    minFiles: 1,
    maxFiles: 1,
    reorder: false,
    fields: [
      { name: "mode", choices: ["each", "ranges"] },
      { name: "ranges", showWhen: { field: "mode", value: "ranges" }, pages: true },
    ],
    defaults: { mode: "each", ranges: "" },
  },
  "pdf-organize": {
    slug: "pdf-organize",
    category: "pdf",
    inputs: ["pdf"],
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
    inputs: ["pdf"],
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
    inputs: ["pdf"],
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
  "pdf-unlock": {
    slug: "pdf-unlock",
    category: "pdf",
    inputs: ["pdf"],
    icon: LockOpen,
    accept: PDF_ACCEPT,
    formats: "PDF",
    minFiles: 1,
    maxFiles: 1,
    reorder: false,
    fields: [{ name: "password", secret: true, required: true }],
    defaults: { password: "" },
  },
  "pdf-rotate": {
    slug: "pdf-rotate",
    category: "pdf",
    inputs: ["pdf"],
    icon: RotateCw,
    accept: PDF_ACCEPT,
    formats: "PDF",
    minFiles: 1,
    maxFiles: 1,
    reorder: false,
    fields: [{ name: "angle", choices: ["90", "180", "270"] }],
    defaults: { angle: "90" },
  },
  "pdf-remove-pages": {
    slug: "pdf-remove-pages",
    category: "pdf",
    inputs: ["pdf"],
    icon: FileMinus,
    accept: PDF_ACCEPT,
    formats: "PDF",
    minFiles: 1,
    maxFiles: 1,
    reorder: false,
    fields: [{ name: "removePages", required: true, pages: true }],
    defaults: { removePages: "" },
  },
  "pdf-extract-pages": {
    slug: "pdf-extract-pages",
    category: "pdf",
    inputs: ["pdf"],
    icon: FileOutput,
    accept: PDF_ACCEPT,
    formats: "PDF",
    minFiles: 1,
    maxFiles: 1,
    reorder: false,
    fields: [{ name: "extractPages", required: true, pages: true }],
    defaults: { extractPages: "" },
  },
  "pdf-page-numbers": {
    slug: "pdf-page-numbers",
    category: "pdf",
    inputs: ["pdf"],
    icon: Hash,
    accept: PDF_ACCEPT,
    formats: "PDF",
    minFiles: 1,
    maxFiles: 1,
    reorder: false,
    fields: [
      { name: "numberPosition", choices: ["bottom-center", "bottom-right", "bottom-left", "top-center", "top-right", "top-left"] },
      { name: "numberStyle", choices: ["n", "n-of-total"] },
      { name: "numberStart", required: true },
    ],
    defaults: { numberPosition: "bottom-center", numberStyle: "n", numberStart: "1" },
  },
  "pdf-watermark": {
    slug: "pdf-watermark",
    category: "pdf",
    inputs: ["pdf"],
    icon: Stamp,
    accept: PDF_ACCEPT,
    formats: "PDF",
    minFiles: 1,
    maxFiles: 1,
    reorder: false,
    fields: [
      { name: "watermarkText", required: true },
      { name: "opacity", choices: ["light", "medium", "strong"] },
    ],
    defaults: { watermarkText: "", opacity: "medium" },
  },
  "pdf-crop": {
    slug: "pdf-crop",
    category: "pdf",
    inputs: ["pdf"],
    icon: Crop,
    accept: PDF_ACCEPT,
    formats: "PDF",
    minFiles: 1,
    maxFiles: 1,
    reorder: false,
    fields: [{ name: "cropMargin", choices: ["5", "10", "15", "25"] }],
    defaults: { cropMargin: "10" },
  },
  "pdf-protect": {
    slug: "pdf-protect",
    category: "pdf",
    inputs: ["pdf"],
    icon: Lock,
    accept: PDF_ACCEPT,
    formats: "PDF",
    minFiles: 1,
    maxFiles: 1,
    reorder: false,
    fields: [{ name: "password", secret: true, required: true }],
    defaults: { password: "" },
  },
  "pdf-repair": {
    slug: "pdf-repair",
    category: "pdf",
    inputs: ["pdf"],
    icon: Wrench,
    accept: PDF_ACCEPT,
    formats: "PDF",
    minFiles: 1,
    maxFiles: 1,
    reorder: false,
    fields: [],
    defaults: {},
  },
  "scan-to-pdf": {
    slug: "scan-to-pdf",
    category: "pdf",
    inputs: IMAGE_INPUTS,
    icon: ScanLine,
    accept: IMAGE_ACCEPT,
    formats: IMAGE_FORMATS,
    minFiles: 1,
    maxFiles: 100,
    reorder: true,
    capture: true,
    fields: [
      { name: "page_size", choices: ["a4", "letter", "fit"] },
      { name: "margin", choices: ["none", "small", "large"] },
    ],
    defaults: { page_size: "a4", orientation: "auto", margin: "small" },
  },
  "images-to-pdf": {
    slug: "images-to-pdf",
    category: "pdf",
    inputs: IMAGE_INPUTS,
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
    inputs: OFFICE_INPUTS,
    primaryOutput: "pdf",
    icon: FileText,
    accept: OFFICE_ACCEPT,
    formats: OFFICE_FORMATS,
    minFiles: 1,
    maxFiles: 10,
    reorder: false,
    fields: [],
    defaults: {},
  },
  "archive-extract": {
    slug: "archive-extract",
    category: "archive",
    inputs: ARCHIVE_INPUTS,
    icon: FolderOpen,
    accept: ARCHIVE_ACCEPT,
    formats: ARCHIVE_FORMATS,
    minFiles: 1,
    maxFiles: 1,
    reorder: false,
    fields: [{ name: "password", secret: true }],
    defaults: { password: "" },
  },
  "archive-create": {
    slug: "archive-create",
    category: "archive",
    inputs: [],
    home: "archive",
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
    inputs: ARCHIVE_INPUTS,
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
    inputs: IMAGE_INPUTS,
    icon: Repeat,
    accept: IMAGE_ACCEPT,
    formats: IMAGE_FORMATS,
    minFiles: 1,
    reorder: false,
    fields: [{ name: "target", choices: CONVERT_TARGETS }],
    defaults: { target: "jpg" },
  },
  "image-edit": {
    slug: "image-edit",
    category: "image",
    inputs: IMAGE_INPUTS,
    icon: Crop,
    accept: IMAGE_ACCEPT,
    formats: IMAGE_FORMATS,
    minFiles: 1,
    reorder: false,
    editor: "image",
    fields: [],
    defaults: {},
  },
  "image-compress": {
    slug: "image-compress",
    category: "compress",
    inputs: IMAGE_INPUTS,
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

/** UI option names that differ from the API's (same API name, different choices and labels). */
const API_NAMES: Record<string, string> = {
  pdfLevel: "level",
  archiveFormat: "format",
  removePages: "pages",
  extractPages: "pages",
  numberPosition: "position",
  numberStart: "start",
  numberStyle: "style",
  watermarkText: "text",
  cropMargin: "margin",
};

export function isFieldVisible(field: OptionField, values: OptionValues): boolean {
  return !field.showWhen || values[field.showWhen.field] === field.showWhen.value;
}

/** Only visible fields are sent, under their API names. An empty optional password is left out. */
export function toApiOptions(tool: ToolDef, values: OptionValues): Record<string, string> {
  const out: Record<string, string> = {};
  for (const field of tool.fields) {
    const value = values[field.name];
    if (field.secret && !value) continue;
    if (value !== undefined && isFieldVisible(field, values)) out[API_NAMES[field.name] ?? field.name] = value;
  }
  return out;
}

export function isToolSlug(value: string | undefined): value is ToolSlug {
  return value !== undefined && value in TOOLS;
}


export interface Conversion {
  pair: string;
  from: string;
  to: string;
  tool: ToolSlug;
  options: OptionValues;
}

const includes = (list: readonly string[], value: string) => list.includes(value);

/** Parses SEO pairs like "heic-to-jpg", "docx-to-pdf", "pdf-to-png" or "rar-to-zip". */
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
  "rar-to-zip",
] as const;

export const CATEGORY_COLOR: Record<Category, string> = {
  image: "text-cat-image",
  compress: "text-cat-compress",
  pdf: "text-cat-pdf",
  office: "text-cat-office",
  archive: "text-cat-archive",
};
