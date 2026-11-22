/** The paperclip's wire, bent into a lowercase "j" (viewBox 0 0 48 48). Shared with the icon script. */
export const CLIP_PATH = "M31 15V35a8.5 8.5 0 0 1-17 0V19a5.5 5.5 0 0 1 11 0V33";

/**
 * jichcha mark: a paperclip, the thing that holds files together, bent into a "j", with the
 * letter's dot in lime. Colours come from tokens, so it follows the theme.
 */
export function LogoMark({ className = "size-8" }: { className?: string }) {
  return (
    <svg viewBox="2.5 3 42 42" className={className} aria-hidden="true" focusable="false">
      <path d={CLIP_PATH} fill="none" className="stroke-fg" strokeWidth="3.8" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="31" cy="7.2" r="3.8" className="fill-logo-dot" />
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
