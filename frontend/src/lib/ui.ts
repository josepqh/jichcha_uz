/** Shared class strings so every button looks and behaves the same. */
const base =
  "inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-xl px-4 text-sm font-semibold transition-[background-color,border-color,color,transform] duration-150 ease-out active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100";

export const btn = {
  primary: `${base} bg-primary text-primary-fg hover:bg-primary-hover`,
  secondary: `${base} border border-border-strong bg-surface text-fg hover:border-fg hover:bg-surface-muted`,
  ghost: `${base} text-fg hover:bg-surface-muted`,
  danger: `${base} border border-border text-danger hover:bg-surface-muted`,
  icon: "inline-flex size-11 cursor-pointer items-center justify-center rounded-xl text-muted transition-[background-color,color,transform] duration-150 hover:bg-surface-muted hover:text-fg active:scale-95 disabled:cursor-not-allowed disabled:opacity-40",
};

export const card = "rounded-2xl border border-border bg-surface";

/** Format label in the brand's stamp style: ".PDF". */
export const formatTag =
  "inline-flex items-center rounded-md border border-current/25 px-1.5 py-0.5 font-mono text-[0.72rem] font-medium uppercase tracking-wide";
