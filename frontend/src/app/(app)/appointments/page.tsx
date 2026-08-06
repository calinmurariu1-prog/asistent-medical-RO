"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { useFetch } from "@/lib/hooks";
import { api } from "@/lib/api";
import type { Appointment } from "@/lib/types";
import { Badge, Button, Card, Input, Spinner } from "@/components/ui";

export default function AppointmentsPage() {
  const { data, loading, reload } = useFetch<Appointment[]>("/appointments");
  const [title, setTitle] = useState("");
  const [startsAt, setStartsAt] = useState("");

  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || !startsAt) return;
    await api.post("/appointments", {
      title,
      starts_at: new Date(startsAt).toISOString(),
    });
    setTitle("");
    setStartsAt("");
    reload();
  }

  async function remove(id: number) {
    await api.del(`/appointments/${id}`);
    reload();
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Programări</h1>

      <Card>
        <form onSubmit={add} className="flex flex-wrap gap-2">
          <Input
            className="flex-1"
            placeholder="Titlu (ex. Cardiolog)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <Input
            type="datetime-local"
            className="w-56"
            value={startsAt}
            onChange={(e) => setStartsAt(e.target.value)}
          />
          <Button type="submit">
            <Plus size={16} /> Adaugă
          </Button>
        </form>
      </Card>

      {loading ? (
        <Spinner />
      ) : (data || []).length === 0 ? (
        <p className="text-sm text-muted">Nicio programare.</p>
      ) : (
        <div className="space-y-2">
          {(data || []).map((a) => (
            <Card key={a.id} className="flex items-center justify-between">
              <div>
                <div className="font-medium">{a.title}</div>
                <div className="text-sm text-muted">
                  {new Date(a.starts_at).toLocaleString("ro-RO")}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Badge tone={a.status === "scheduled" ? "blue" : "neutral"}>
                  {a.status}
                </Badge>
                <button
                  onClick={() => remove(a.id)}
                  className="text-muted hover:text-red-600"
                  aria-label="Șterge"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
