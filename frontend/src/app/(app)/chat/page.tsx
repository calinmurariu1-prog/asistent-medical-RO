"use client";

import { useEffect, useRef, useState } from "react";
import { MessageSquare, Send } from "lucide-react";
import { api } from "@/lib/api";
import type { Chat, ChatMessage } from "@/lib/types";
import { Button, EmptyState, Input, PageHeader } from "@/components/ui";

export default function ChatPage() {
  const [chatId, setChatId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.post<Chat>("/chats", {}).then((c) => setChatId(c.id));
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || chatId === null) return;
    const question = input.trim();
    setInput("");
    setMessages((m) => [
      ...m,
      { id: Date.now(), role: "user", content: question, sources: [], created_at: "" },
    ]);
    setSending(true);
    try {
      const reply = await api.post<ChatMessage>(`/chats/${chatId}/messages`, {
        content: question,
      });
      setMessages((m) => [...m, reply]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-3xl flex-col">
      <div className="mb-4">
        <PageHeader title="Chat Medical AI" icon={MessageSquare} />
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto pr-1">
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
                <div className="mt-2 text-xs opacity-70">
                  Surse: {m.sources.length}
                </div>
              )}
            </div>
          </div>
        ))}
        {sending && <div className="text-sm text-muted">Se gândește…</div>}
        <div ref={endRef} />
      </div>

      <form onSubmit={send} className="mt-4 flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Scrie o întrebare…"
          disabled={sending}
        />
        <Button type="submit" disabled={sending || !input.trim()}>
          <Send size={16} />
        </Button>
      </form>
    </div>
  );
}
