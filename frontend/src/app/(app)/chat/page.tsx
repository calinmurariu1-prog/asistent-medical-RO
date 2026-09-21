"use client";

import { useEffect, useRef, useState } from "react";
import { MessageSquare, Send } from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Chat, ChatMessage } from "@/lib/types";
import { Button, EmptyState, Input, PageHeader } from "@/components/ui";

export default function ChatPage() {
  const [chatId, setChatId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.post<Chat>("/chats", {}).then((c) => setChatId(c.id))
      .catch(() => setError("Conversația nu a putut fi deschisă. Reîncarcă pagina pentru a încerca din nou."));
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || chatId === null) return;
    const question = input.trim();
    setError("");
    setInput("");
    const pendingId = Date.now();
    setMessages((m) => [
      ...m,
      { id: pendingId, role: "user", content: question, sources: [], created_at: "" },
    ]);
    setSending(true);
    try {
      const reply = await api.post<ChatMessage>(`/chats/${chatId}/messages`, {
        content: question,
      });
      setMessages((m) => [...m, reply]);
    } catch (cause) {
      setMessages((m) => m.filter(message => message.id !== pendingId));
      setInput(question);
      setError(cause instanceof Error ? cause.message : "Întrebarea nu a putut fi trimisă. Încearcă din nou.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col">
      <div className="mb-4">
        <PageHeader title="Chat Medical AI" icon={MessageSquare} />
      </div>

      <p className="mb-3 text-sm text-muted">Pentru o urgență medicală, sună la 112. Acest chat nu este un serviciu de urgență.</p>
      {error && <p role="alert" className="mb-3 text-sm text-red-600 dark:text-red-400">{error}</p>}
      <div aria-live="polite" className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
        {messages.length === 0 && (
          <EmptyState
            icon={MessageSquare}
            title="Întreabă despre dosarul tău"
            hint="Răspund folosind doar informațiile tale medicale și indic sursele [S#]."
          />
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-3xl px-4 py-2.5 text-sm shadow-soft ${
                m.role === "user"
                  ? "brand-gradient text-white"
                  : "border border-border bg-surface-2"
              }`}
            >
              {m.content}
              {m.sources && m.sources.length > 0 && (
                <ul className="mt-2 border-t border-border pt-2 text-xs">
                  {m.sources.map((source, index) => {
                    const destination = source.type === "document" ? "/documents"
                      : source.type === "lab_result" ? "/labs"
                      : source.type === "medication" ? "/medications" : "/record";
                    return <li key={`${String(source.ref)}-${index}`}>
                      <Link className="flex min-h-12 items-center underline" href={destination}>
                        [{String(source.ref)}] {String(source.title || "Înregistrare din dosar")}
                      </Link>
                    </li>;
                  })}
                </ul>
              )}
            </div>
          </div>
        ))}
        {sending && <div className="text-sm text-muted">Se gândește…</div>}
        <div ref={endRef} />
      </div>

      <label htmlFor="chat-question" className="mt-4 text-sm">Întrebarea ta</label>
      <form onSubmit={send} className="mt-2 flex gap-2">
        <Input
          id="chat-question"
          maxLength={4000}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Scrie o întrebare…"
          disabled={sending || chatId === null}
        />
        <Button type="submit" aria-label="Trimite întrebarea" disabled={sending || chatId === null || !input.trim()}>
          <Send size={16} />
        </Button>
      </form>
    </div>
  );
}
