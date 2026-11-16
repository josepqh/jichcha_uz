import type { TFunction } from "i18next";

import { ApiError } from "./api";

export function errorMessage(t: TFunction, error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "weak_password") {
      const reasons = (error.details.reasons as string[] | undefined) ?? ["invalid"];
      return t("errors.weak_password", { reasons: reasons.map((r) => t(`weak.${r}`, { defaultValue: t("weak.invalid") })).join("; ") });
    }
    const text = t(`errors.${error.code}`, { ...error.details, defaultValue: "" });
    if (text) return text;
    if (error.status === 404) return t("errors.not_found");
  }
  return t("errors.internal_error");
}

export function taskErrorMessage(t: TFunction, code: string): string {
  return t(`errors.${code}`, { defaultValue: t("errors.internal_error") });
}
