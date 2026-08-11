"use client";

import { useState } from "react";
import { CalendarDays, Plus, Trash2 } from "lucide-react";
import { useFetch } from "@/lib/hooks";
import { api } from "@/lib/api";
import type { Appointment } from "@/lib/types";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  PageHeader,
  Spinner,
} from "@/components/ui";

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
      <PageHeader
        title="Programări"
        subtitle="Ține evidența consultațiilor și investigațiilor."
        icon={CalendarDays}
      />

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
        <EmptyState
          icon={CalendarDays}
          title="Nicio programare"
          hint="Adaugă o programare ca să o ai la îndemână și să primești memento-uri."
        />
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
