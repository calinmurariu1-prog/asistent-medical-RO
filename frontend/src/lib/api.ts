const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const PREFIX = "/api/v1";

const TOKEN_KEY = "am_access_token";
const REFRESH_KEY = "am_refresh_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setTokens(access: string, refresh: string): void {
  generation++;
  window.localStorage.setItem(TOKEN_KEY, access);
  window.localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  generation++;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

let refreshing: Promise<boolean> | null = null;
let generation = 0;
async function refreshSession(): Promise<boolean> {
  if (refreshing) return refreshing;
  const refresh = window.localStorage.getItem(REFRESH_KEY);
  if (!refresh) return false;
  const ticket = generation;
  refreshing = (async () => {
    const res = await fetch(`${BASE_URL}${PREFIX}/auth/refresh`, {
      method: "POST", headers: {"Content-Type":"application/json"},
      body: JSON.stringify({refresh_token: refresh}),
    });
    if (ticket !== generation) return false;
    if (!res.ok) {
      if (res.status === 401 || res.status === 403) {
        clearTokens(); window.dispatchEvent(new Event("session-expired"));
      }
      return false;
    }
    const tokens = await res.json();
    if (ticket !== generation) return false;
    window.localStorage.setItem(TOKEN_KEY, tokens.access_token);
    window.localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
    return true;
  })().finally(() => { refreshing = null; });
  return refreshing;
}

async function response(path: string, options: RequestInit = {}): Promise<Response> {
  const send = () => {
    const headers = new Headers(options.headers);
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    if (!(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
    return fetch(`${BASE_URL}${PREFIX}${path}`, {...options, headers});
  };
  const ticket = generation;
  const attemptedToken = getToken();
  let res = await send();
  if (ticket !== generation) throw new ApiError(401, "Sesiunea s-a schimbat.");
  const credentialPath = /^\/auth\/(login|register|refresh|password-reset|email)/.test(path);
  if (res.status === 401 && attemptedToken && !credentialPath) {
    if ((getToken() && getToken() !== attemptedToken) || await refreshSession()) res = await send();
    if (ticket !== generation) throw new ApiError(401, "Sesiunea s-a schimbat.");
    if (res.status === 401) {clearTokens(); window.dispatchEvent(new Event("session-expired"));}
  }
  if (!res.ok) {
    let message = "Cererea nu a putut fi finalizată.";
    try { const data = await res.json(); if (typeof data.detail === "string") message = data.detail; }
    catch { /* non-JSON response */ }
    throw new ApiError(res.status, message);
  }
  return res;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await response(path, options);
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return text ? JSON.parse(text) as T : undefined as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  del: (path: string) => request<void>(path, { method: "DELETE" }),
  postForm: <T>(path: string, form: FormData) =>
    request<T>(path, { method: "POST", body: form }),
};

/** Authenticated downloads share session refresh and never expose bearer tokens in URLs. */
export async function downloadFile(path: string): Promise<Blob> {
  return (await response(path)).blob();
}
