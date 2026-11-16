import { Eye, EyeOff, LoaderCircle } from "lucide-react";
import { useId, useState, type InputHTMLAttributes, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { btn } from "@/lib/ui";

const inputClass =
  "min-h-12 w-full rounded-xl border bg-surface px-4 text-base transition-colors duration-150 placeholder:text-muted aria-[invalid=true]:border-danger";

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string | null;
  hint?: string;
  trailing?: ReactNode;
}

export function TextField({ label, error, hint, trailing, id, className, ...input }: FieldProps) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const hintId = hint ? `${inputId}-hint` : undefined;
  const errorId = error ? `${inputId}-error` : undefined;
  return (
    <div className="space-y-1.5">
      <label htmlFor={inputId} className="block text-sm font-semibold">
        {label}
      </label>
      <div className="relative">
        <input
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={[errorId, hintId].filter(Boolean).join(" ") || undefined}
          className={`${inputClass} ${error ? "" : "border-border-strong"} ${trailing ? "pr-12" : ""} ${className ?? ""}`}
          {...input}
        />
        {trailing ? <div className="absolute inset-y-0 right-0 flex items-center pr-1">{trailing}</div> : null}
      </div>
      {error ? (
        <p id={errorId} className="text-sm text-danger">
          {error}
        </p>
      ) : null}
      {hint ? (
        <p id={hintId} className="text-sm text-muted">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

export function PasswordField(props: Omit<FieldProps, "type" | "trailing">) {
  const { t } = useTranslation();
  const [visible, setVisible] = useState(false);
  const Icon = visible ? EyeOff : Eye;
  return (
    <TextField
      {...props}
      type={visible ? "text" : "password"}
      spellCheck={false}
      autoCapitalize="none"
      trailing={
        <button
          type="button"
          className={btn.icon}
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? t("fields.hide") : t("fields.show")}
          aria-pressed={visible}
        >
          <Icon className="size-5" aria-hidden="true" />
        </button>
      }
    />
  );
}

export function FormAlert({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="rounded-lg border border-danger px-4 py-3 text-sm text-danger">
      {message}
    </p>
  );
}

export function SubmitButton({ busy, label, busyLabel }: { busy: boolean; label: string; busyLabel: string }) {
  return (
    <button type="submit" className={`${btn.primary} w-full text-base`} disabled={busy} aria-busy={busy}>
      {busy ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : null}
      {busy ? busyLabel : label}
    </button>
  );
}

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateEmail(value: string): "required" | "invalid_email" | null {
  if (!value.trim()) return "required";
  return EMAIL.test(value.trim()) ? null : "invalid_email";
}

/** Focus the first field flagged invalid, after React commits the error state. */
export function focusFirstInvalid(form: HTMLFormElement | null) {
  requestAnimationFrame(() => form?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus());
}
