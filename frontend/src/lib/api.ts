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
  language: "uz" | "ru" | "en";
  email_verified: boolean;
  has_password: boolean;
  date_joined: string;
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

/** Exchanges the httpOnly refresh cookie for a new access token. Concurrent callers share one request. */
export function refreshSession(): Promise<boolean> {
  refreshing ??= rawRequest<Session>("/auth/refresh/", { method: "POST" })
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

export const auth = {
  login: (email: string, password: string) => rawRequest<Session>("/auth/login/", json({ email, password })).then(startSession),
  register: (email: string, password: string, language: string) =>
    rawRequest<Session>("/auth/register/", json({ email, password, language })).then(startSession),
  google: (credential: string) => rawRequest<Session>("/auth/google/", json({ credential })).then(startSession),
  logout: async () => {
    await rawRequest<void>("/auth/logout/", { method: "POST" }).catch(() => undefined);
    useAuthStore.getState().clear();
  },
  requestReset: (email: string, language: string) => rawRequest<void>("/auth/password/reset/", json({ email, language })),
  confirmReset: (uid: string, token: string, newPassword: string) =>
    rawRequest<Session>("/auth/password/reset/confirm/", json({ uid, token, new_password: newPassword })).then(startSession),
};

export const api = {
  usage: () => request<Usage>("/usage/"),
  task: (id: string) => request<Task>(`/tasks/${encodeURIComponent(id)}/`),
  deleteTask: (id: string) => request<void>(`/tasks/${encodeURIComponent(id)}/`, { method: "DELETE" }),
  history: (page: number) => request<Page<Task>>(`/tasks/history/?page=${page}`),
  me: () => request<Me>("/me/"),
  updateMe: (patch: Partial<Pick<Me, "language">>) =>
    request<Me>("/me/", { method: "PATCH", body: JSON.stringify(patch) }).then((me) => {
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
