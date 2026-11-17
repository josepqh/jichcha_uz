import { describe, expect, it } from "vitest";

import { formatBytes, formatDate, savedPercent } from "./format";
import { resolveConversion } from "./tools";

describe("formatBytes", () => {
  it("picks a readable unit", () => {
    expect(formatBytes(512, "en")).toBe("512\u00a0B");
    expect(formatBytes(1536, "en")).toBe("1.5\u00a0KB");
    expect(formatBytes(250 * 1024 * 1024, "en")).toBe("250\u00a0MB");
  });
});

describe("savedPercent", () => {
  it("rounds the reduction", () => {
    expect(savedPercent(1000, 380)).toBe(62);
    expect(savedPercent(1000, 1200)).toBe(-20);
    expect(savedPercent(0, 10)).toBe(0);
  });
});

describe("resolveConversion", () => {
  it("maps image pairs to the convert tool", () => {
    expect(resolveConversion("heic-to-jpg")).toMatchObject({ tool: "image-convert", options: { target: "jpg" } });
  });
  it("maps pdf targets to images-to-pdf", () => {
    expect(resolveConversion("png-to-pdf")?.tool).toBe("images-to-pdf");
  });
  it("maps documents and PDF pages", () => {
    expect(resolveConversion("docx-to-pdf")?.tool).toBe("office-to-pdf");
    expect(resolveConversion("rar-to-zip")).toMatchObject({ tool: "archive-convert", options: { target: "zip" } });
    expect(resolveConversion("epub-to-pdf")).toBeNull(); // e-books are not offered
    expect(resolveConversion("zip-to-zip")).toBeNull();
    expect(resolveConversion("rar-to-pdf")).toBeNull();
    expect(resolveConversion("pdf-to-png")).toMatchObject({ tool: "pdf-to-images", options: { format: "png" } });
    expect(resolveConversion("pdf-to-webp")).toBeNull();
    expect(resolveConversion("docx-to-jpg")).toBeNull();
  });
  it("rejects unknown or identical formats", () => {
    expect(resolveConversion("exe-to-jpg")).toBeNull();
    expect(resolveConversion("jpg-to-jpg")).toBeNull();
    expect(resolveConversion("jpg-to-heic")).toBeNull();
    expect(resolveConversion(undefined)).toBeNull();
  });
});

describe("formatDate", () => {
  it("writes Uzbek month names itself", () => {
    expect(formatDate("2026-11-16T12:00:00", "uz")).toBe("2026-yil 16-noyabr");
    expect(formatDate("2026-01-05T09:07:00", "uz", true)).toMatch(/^2026-yil 5-yanvar, 09:07$/);
  });
  it("uses Intl for other languages", () => {
    expect(formatDate("2026-11-16T12:00:00", "en")).toBe("November 16, 2026");
  });
});
