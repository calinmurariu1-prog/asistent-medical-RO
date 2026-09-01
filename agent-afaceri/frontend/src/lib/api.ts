export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Skill = {
  name: string;
  title: string;
  description: string;
  category: "juridic" | "business";
  inputs: string[];
};

export async function listSkills(): Promise<Skill[]> {
  const r = await fetch(`${API_URL}/skills`, { cache: "no-store" });
  if (!r.ok) throw new Error("Nu am putut încărca skill-urile");
  return r.json();
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
  const data = await r.json();
  if (!r.ok) throw new Error(data?.detail || "Eroare la rularea skill-ului");
  return data.result as string;
}

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
  const data = await r.json();
  if (!r.ok) throw new Error(data?.detail || "Eroare la chat");
  return data.reply as string;
}
