/** Only same-site paths are allowed as post-login targets (no open redirects). */
export function safeNext(raw: string | null, lang: string): string {
  if (raw && raw.startsWith("/") && !raw.startsWith("//") && !raw.includes("\\")) return raw;
  return `/${lang}/account`;
}
