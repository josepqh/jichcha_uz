import type { Language } from "@/i18n";
import { useAuthStore } from "@/stores/auth";

export type TaskStatus = "queued" | "processing" | "done" | "failed";

export interface TaskFile {
  id: string;
  name: string;
  size: number;
  mime: string;
  download_url: string | null;
}

export interface Task {
  id: string;
  tool: string;
  status: TaskStatus;
  error_code: string;
  options: Record<string, unknown>;
  created_at: string;
  finished_at: string | null;
  expires_at: string;
  files_deleted: boolean;
  outputs: TaskFile[];
  bundle: TaskFile | null;
}

export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface Usage {
  role: "guest" | "registered";
  limits: {
    max_file_mb: number;
    max_total_mb: number;
    daily_tasks: number;
    max_batch: number;
    retention_hours: number;
  };
  today: { tasks_used: number; tasks_left: number };
}

export interface Me {
  id: string;
  email: string;
  language: Language;
  email_verified: boolean;
  has_password: boolean;
  totp_enabled: boolean;
  date_joined: string;
  is_staff: boolean;
}

export interface Session {
  access: string;
  user: Me;
}

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: Record<string, unknown>;

  constructor(code: string, status: number, details: Record<string, unknown> = {}, message = code) {
    super(message);
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

const BASE = "/api/v1";

function toApiError(status: number, body: unknown): ApiError {
  const err = (body as { error?: { code?: string; message?: string; details?: Record<string, unknown> } })?.error;
  if (err?.code) return new ApiError(err.code, status, err.details ?? {}, err.message);
  return new ApiError(status >= 500 ? "internal_error" : "network_error", status);
}

async function rawRequest<T>(path: string, init: RequestInit = {}, token: string | null = null): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { credentials: "same-origin", ...init, headers });
  } catch {
    throw new ApiError("network_error", 0);
  }
  if (res.status === 204 || res.status === 202) return undefined as T;
  const body: unknown = await res.json().catch(() => null);
  if (!res.ok) throw toApiError(res.status, body);
  return body as T;
}

// --- Session handling ---------------------------------------------------------------------------

let refreshing: Promise<boolean> | null = null;

/**
 * Tabs share one refresh cookie, and each refresh rotates it. A Web Lock makes tabs take turns, so a
 * tab never sends a cookie another tab has just rotated away (the server also allows a short grace).
 */
function withRefreshLock<T>(run: () => Promise<T>): Promise<T> {
  const locks = typeof navigator === "undefined" ? undefined : navigator.locks;
  return locks ? locks.request("jichcha-auth-refresh", run) : run();
}

/** Exchanges the httpOnly refresh cookie for a new access token. Concurrent callers share one request. */
export function refreshSession(): Promise<boolean> {
  refreshing ??= withRefreshLock(() => rawRequest<Session>("/auth/refresh/", { method: "POST" }))
    .then((session) => {
      useAuthStore.getState().setSession(session.access, session.user);
      return true;
    })
    .catch(() => {
      useAuthStore.getState().clear();
      return false;
    })
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

/**
 * While the page-load session restore is in flight, wait for it: otherwise a request could go out
 * as a guest and a moment later be followed by requests made as the account (and get 404s).
 */
async function sessionSettled(): Promise<void> {
  if (useAuthStore.getState().status === "loading" && refreshing) await refreshing;
}

/** Sends the access token when signed in; on 401 refreshes once and retries. */
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  await sessionSettled();
  const token = useAuthStore.getState().accessToken;
  try {
    return await rawRequest<T>(path, init, token);
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401 || !token) throw error;
    if (!(await refreshSession())) throw error;
    return rawRequest<T>(path, init, useAuthStore.getState().accessToken);
  }
}

function startSession(session: Session): Me {
  useAuthStore.getState().setSession(session.access, session.user);
  return session.user;
}

const json = (body: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(body) });

export interface TwoFactorSetup {
  secret: string;
  otpauth_uri: string;
  /** SVG QR code as a data: URI. */
  qr: string;
}

export const auth = {
  /** `otp` is the authenticator code, sent on the second try when the server answers otp_required. */
  login: (email: string, password: string, otp = "") =>
    rawRequest<Session>("/auth/login/", json({ email, password, otp })).then(startSession),
  register: (email: string, password: string, language: string, captcha = "") =>
    rawRequest<Session>("/auth/register/", json({ email, password, language, captcha })).then(startSession),
  google: (credential: string, otp = "") => rawRequest<Session>("/auth/google/", json({ credential, otp })).then(startSession),
  logout: async () => {
    await rawRequest<void>("/auth/logout/", { method: "POST" }).catch(() => undefined);
    useAuthStore.getState().clear();
  },
  requestReset: (email: string, language: string, captcha = "") =>
    rawRequest<void>("/auth/password/reset/", json({ email, language, captcha })),
  confirmReset: (uid: string, token: string, newPassword: string, otp = "") =>
    rawRequest<Session>("/auth/password/reset/confirm/", json({ uid, token, new_password: newPassword, otp })).then(startSession),
  verifyEmail: (token: string) => rawRequest<{ email_verified: boolean }>("/auth/email/verify/", json({ token })),
};

export interface FeedbackMessage {
  message: string;
  email: string;
  page: string;
  language: string;
  /** Honeypot: always empty from people. */
  website: string;
  captcha: string;
}

export const api = {
  sendFeedback: (body: FeedbackMessage) => rawRequest<void>("/feedback/", json(body)),
  usage: () => request<Usage>("/usage/"),
  tools: () => request<{ slug: string; enabled: boolean }[]>("/tools/"),
  task: (id: string) => request<Task>(`/tasks/${encodeURIComponent(id)}/`),
  deleteTask: (id: string) => request<void>(`/tasks/${encodeURIComponent(id)}/`, { method: "DELETE" }),
  history: (page: number) => request<Page<Task>>(`/tasks/history/?page=${page}`),
  me: () => request<Me>("/me/"),
  updateMe: (patch: Partial<Pick<Me, "language">>) =>
    request<Me>("/me/", { method: "PATCH", body: JSON.stringify(patch) }).then((me) => {
      useAuthStore.getState().setUser(me);
      return me;
    }),
  /** Ends the other sessions; this tab gets a fresh one. */
  changePassword: (currentPassword: string, newPassword: string) =>
    request<Session>("/me/password/", json({ current_password: currentPassword, new_password: newPassword })).then(startSession),
  resendVerification: (language: string) => request<void>("/me/email/verify/", json({ language })),
  twoFactorSetup: () => request<TwoFactorSetup>("/me/2fa/setup/", { method: "POST" }),
  twoFactorEnable: (code: string) =>
    request<Me>("/me/2fa/enable/", json({ code })).then((me) => {
      useAuthStore.getState().setUser(me);
      return me;
    }),
  twoFactorDisable: (proof: ({ password: string } | { google_credential: string }) & { code: string }) =>
    request<Me>("/me/2fa/disable/", json(proof)).then((me) => {
      useAuthStore.getState().setUser(me);
      return me;
    }),
  /** Confirm with the password, or with a fresh Google credential when the account has no password. */
  deleteAccount: async (proof: { password: string } | { google_credential: string }) => {
    await request<void>("/me/", { method: "DELETE", body: JSON.stringify(proof) });
    useAuthStore.getState().clear();
  },
};

// --- Upload -------------------------------------------------------------------------------------

export interface UploadParams {
  tool: string;
  options: Record<string, unknown>;
  files: File[];
  onProgress?: (fraction: number) => void;
  signal?: AbortSignal;
}

/** XHR instead of fetch: fetch has no upload progress events. */
function uploadOnce({ tool, options, files, onProgress, signal }: UploadParams, token: string | null): Promise<Task> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("tool", tool);
    form.append("options", JSON.stringify(options));
    for (const file of files) form.append("files", file, file.name);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE}/tasks/`);
    xhr.withCredentials = true;
    xhr.responseType = "json";
    xhr.setRequestHeader("Accept", "application/json");
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress?.(e.loaded / e.total);
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve(xhr.response as Task);
      else reject(toApiError(xhr.status, xhr.response));
    };
    xhr.onerror = () => reject(new ApiError("network_error", 0));
    xhr.onabort = () => reject(new ApiError("aborted", 0));
    signal?.addEventListener("abort", () => xhr.abort(), { once: true });
    xhr.send(form);
  });
}

export async function createTask(params: UploadParams): Promise<Task> {
  await sessionSettled();
  const token = useAuthStore.getState().accessToken;
  try {
    return await uploadOnce(params, token);
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401 || !token) throw error;
    if (!(await refreshSession())) throw error;
    params.onProgress?.(0);
    return uploadOnce(params, useAuthStore.getState().accessToken);
  }
}


// --- Admin panel (staff only) -------------------------------------------------------------------

export interface DashboardStats {
  days: number;
  per_day: { date: string; tasks: number; failed: number; active: number }[];
  top_tools: { tool: string; count: number; failed: number }[];
  totals: {
    tasks: number;
    failed: number;
    active: number;
    telegram_users: number;
    web_tasks: number;
    telegram_tasks: number;
    error_rate: number;
    registered_users: number;
    new_users: number;
  };
}

export interface StaffUser {
  id: string;
  email: string;
  date_joined: string;
  last_login: string | null;
  is_active: boolean;
  is_staff: boolean;
  email_verified: boolean;
  language: string;
  has_password: boolean;
  tasks_30d: number;
}

export interface FailedTask {
  id: string;
  tool: string;
  source: "web" | "telegram";
  error_code: string;
  created_at: string;
  duration_ms: number | null;
  input_meta: { format: string; size: number }[];
}

export interface LoadSnapshot {
  queues: Record<string, number | null>;
  workers: { name: string; ok: boolean }[];
  tasks: { queued: number; processing: number };
  storage: { files_bytes: number; disk_total: number | null; disk_free: number | null };
}

export interface LimitPolicy {
  role: "guest" | "registered";
  max_file_mb: number;
  max_total_mb: number;
  daily_tasks: number;
  max_batch: number;
  retention_hours: number;
}

const patch = (body: unknown): RequestInit => ({ method: "PATCH", body: JSON.stringify(body) });

export const adminApi = {
  dashboard: (days: 7 | 30) => request<DashboardStats>(`/admin/dashboard/?days=${days}`),
  load: () => request<LoadSnapshot>("/admin/load/"),
  users: (params: { q: string; blocked: boolean; page: number }) =>
    request<Page<StaffUser>>(
      `/admin/users/?${new URLSearchParams({ q: params.q, page: String(params.page), ...(params.blocked ? { blocked: "1" } : {}) })}`,
    ),
  block: (id: string) => request<StaffUser>(`/admin/users/${encodeURIComponent(id)}/block/`, { method: "POST" }),
  unblock: (id: string) => request<StaffUser>(`/admin/users/${encodeURIComponent(id)}/block/`, { method: "DELETE" }),
  failures: (params: { tool: string; code: string; page: number }) =>
    request<Page<FailedTask> & { summary: { tool: string; error_code: string; count: number }[] }>(
      `/admin/failures/?${new URLSearchParams({ tool: params.tool, code: params.code, page: String(params.page) })}`,
    ),
  limits: () => request<LimitPolicy[]>("/admin/limits/"),
  saveLimits: (role: string, values: Partial<LimitPolicy>) =>
    request<LimitPolicy>(`/admin/limits/${encodeURIComponent(role)}/`, patch(values)),
  tools: () => request<{ slug: string; enabled: boolean }[]>("/admin/tools/"),
  setTool: (slug: string, enabled: boolean) =>
    request<{ slug: string; enabled: boolean }>(`/admin/tools/${encodeURIComponent(slug)}/`, patch({ enabled })),
};
