const UNITS = ["B", "KB", "MB", "GB"] as const;

export function formatBytes(bytes: number, locale: string): string {
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < UNITS.length - 1) {
    value /= 1024;
    unit += 1;
  }
  const digits = unit === 0 || value >= 100 ? 0 : 1;
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits: digits }).format(value)}\u00a0${UNITS[unit]}`;
}

export function savedPercent(before: number, after: number): number {
  if (before <= 0) return 0;
  return Math.round(((before - after) / before) * 100);
}

export function formatTime(iso: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, { hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
}

// Browsers' Intl data has no Uzbek month names (it prints "2026 M11 16"), so Uzbek is formatted here.
const UZ_MONTHS = [
  "yanvar",
  "fevral",
  "mart",
  "aprel",
  "may",
  "iyun",
  "iyul",
  "avgust",
  "sentabr",
  "oktabr",
  "noyabr",
  "dekabr",
] as const;

/** "2026-yil 16-noyabr" / "16 ноября 2026 г." / "November 16, 2026"; with time appended when asked. */
export function formatDate(value: string | Date, locale: string, withTime = false): string {
  const date = new Date(value);
  if (locale.startsWith("uz")) {
    const day = `${date.getFullYear()}-yil ${date.getDate()}-${UZ_MONTHS[date.getMonth()]}`;
    return withTime ? `${day}, ${formatTime(date.toISOString(), locale)}` : day;
  }
  const options: Intl.DateTimeFormatOptions = withTime
    ? { dateStyle: "medium", timeStyle: "short" }
    : { dateStyle: "long" };
  return new Intl.DateTimeFormat(locale, options).format(date);
}
