import { FileDoc, FileImage, FilePdf, FilePpt, FileXls, FileZip, type Icon } from "@phosphor-icons/react";

import { FAMILY_TEXT } from "@/lib/sections";
import type { Family } from "@/lib/tools";

/** Real file-type icons (Phosphor, duotone) for the sections, each in its family colour. */
const ICONS: Record<Family, Icon> = {
  pdf: FilePdf,
  word: FileDoc,
  excel: FileXls,
  powerpoint: FilePpt,
  image: FileImage,
  archive: FileZip,
};

export function FamilyIcon({ family, className = "size-5" }: { family: Family; className?: string }) {
  const Glyph = ICONS[family];
  return <Glyph weight="duotone" className={`shrink-0 ${FAMILY_TEXT[family]} ${className}`} aria-hidden="true" />;
}
