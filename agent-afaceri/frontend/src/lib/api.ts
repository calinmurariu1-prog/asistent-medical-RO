export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const TOKEN_KEY = "agent_afaceri_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignoră stocarea indisponibilă */
  }
}

function authHeaders(): Record<string, string> {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

async function jsonOrThrow(r: Response) {
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data?.detail || `Eroare ${r.status}`);
  return data;
}

// ---------------------------------------------------------------- Skills
export type Skill = {
  name: string;
  title: string;
  description: string;
  category: "juridic" | "business";
  inputs: string[];
};

export async function listSkills(): Promise<Skill[]> {
  const r = await fetch(`${API_URL}/skills`, { cache: "no-store" });
  return jsonOrThrow(r);
}

export async function runSkill(
  name: string,
  inputs: Record<string, string>
): Promise<string> {
  const r = await fetch(`${API_URL}/skills/${name}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ inputs }),
  });
  return (await jsonOrThrow(r)).result as string;
}

// ---------------------------------------------------------------- Chat
export type ChatMsg = { role: "user" | "assistant"; content: string };

export async function chat(
  message: string,
  domain: "juridic" | "business",
  history: ChatMsg[]
): Promise<string> {
  const r = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, domain, history }),
  });
  return (await jsonOrThrow(r)).reply as string;
}

// ---------------------------------------------------------------- Auth
export type User = { id: number; email: string };

export async function register(email: string, password: string): Promise<string> {
  const r = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return (await jsonOrThrow(r)).access_token as string;
}

export async function login(email: string, password: string): Promise<string> {
  const body = new URLSearchParams({ username: email, password });
  const r = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  return (await jsonOrThrow(r)).access_token as string;
}

export async function me(): Promise<User> {
  const r = await fetch(`${API_URL}/auth/me`, { headers: authHeaders() });
  return jsonOrThrow(r);
}

// ---------------------------------------------------------------- Documents
export type DocItem = {
  id: number;
  title: string;
  category: string;
  created_at: string;
};

export async function saveDocument(
  title: string,
  content: string,
  category = "general"
): Promise<DocItem> {
  const r = await fetch(`${API_URL}/documents`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ title, content, category }),
  });
  return jsonOrThrow(r);
}

export async function listDocuments(): Promise<DocItem[]> {
  const r = await fetch(`${API_URL}/documents`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  return jsonOrThrow(r);
}

export async function deleteDocument(id: number): Promise<void> {
  const r = await fetch(`${API_URL}/documents/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!r.ok && r.status !== 204) throw new Error(`Eroare ${r.status}`);
}

async function downloadBlob(r: Response, fallbackName: string) {
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    throw new Error(d?.detail || `Eroare ${r.status}`);
  }
  const blob = await r.blob();
  const cd = r.headers.get("Content-Disposition") || "";
  const match = cd.match(/filename="?([^"]+)"?/);
  const name = match ? match[1] : fallbackName;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function exportDocument(id: number, format: "pdf" | "docx") {
  const r = await fetch(`${API_URL}/documents/${id}/export?format=${format}`, {
    headers: authHeaders(),
  });
  await downloadBlob(r, `document.${format}`);
}

export async function exportInline(
  title: string,
  content: string,
  format: "pdf" | "docx"
) {
  const r = await fetch(`${API_URL}/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ title, content, format }),
  });
  await downloadBlob(r, `${title}.${format}`);
}
