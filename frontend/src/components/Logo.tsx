/**
 * jichcha mark: a document in front of a second sheet (one file becoming another), and the
 * small square — "jichcha" means "a little bit". Colours come from tokens, so it follows the theme.
 */
export function LogoMark({ className = "size-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true" focusable="false">
      <rect x="11" y="2" width="18" height="22" rx="3.5" className="fill-accent" />
      <path
        d="M6.5 8h11.2L23 13.3V27.5A2.5 2.5 0 0 1 20.5 30h-14A2.5 2.5 0 0 1 4 27.5v-17A2.5 2.5 0 0 1 6.5 8Z"
        className="fill-fg"
      />
      <path d="M17.7 8v3.8a1.5 1.5 0 0 0 1.5 1.5H23" fill="none" className="stroke-accent" strokeWidth="1.6" strokeLinejoin="round" />
      <rect x="8" y="22" width="4.5" height="4.5" rx="1" className="fill-logo-dot" />
    </svg>
  );
}

export function Wordmark() {
  return (
    <span className="font-display text-[1.35rem] leading-none font-semibold tracking-[-0.04em]" translate="no">
      jichcha
    </span>
  );
}
