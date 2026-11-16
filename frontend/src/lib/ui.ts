/** Shared class strings so every button looks and behaves the same. */
const base =
  "inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-lg px-4 text-sm font-semibold transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50";

export const btn = {
  primary: `${base} bg-primary text-primary-fg hover:bg-primary-hover`,
  secondary: `${base} border border-border-strong bg-surface text-fg hover:bg-surface-muted`,
  ghost: `${base} text-fg hover:bg-surface-muted`,
  danger: `${base} border border-border text-danger hover:bg-surface-muted`,
  icon: "inline-flex size-11 cursor-pointer items-center justify-center rounded-lg text-muted transition-colors duration-150 hover:bg-surface-muted hover:text-fg disabled:cursor-not-allowed disabled:opacity-40",
};

export const card = "rounded-2xl border border-border bg-surface";
