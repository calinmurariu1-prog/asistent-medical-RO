"use client";

import Link from "next/link";
import {
  AlertTriangle,
  Bell,
  CalendarDays,
  FileText,
  Lightbulb,
  Pill,
} from "lucide-react";
import { useFetch } from "@/lib/hooks";
import type { Dashboard } from "@/lib/types";
import { Badge, Card, Spinner } from "@/components/ui";

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <Card className="text-center">
      <div className="text-3xl font-bold brand-text-gradient">{value}</div>
      <div className="mt-1 text-sm text-muted">{label}</div>
    </Card>
  );
}

export default function DashboardPage() {
  const { data, loading } = useFetch<Dashboard>("/dashboard");

  if (loading) return <Spinner />;
  if (!data) return <p className="text-muted">Nu s-au putut încărca datele.</p>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {data.alerts.length > 0 && (
        <Card className="border-red-500/30 bg-red-500/5">
          <div className="mb-2 flex items-center gap-2 font-semibold text-red-600">
            <AlertTriangle size={18} /> Alerte
          </div>
          <ul className="space-y-1 text-sm">
            {data.alerts.map((a, i) => (
              <li key={i}>• {a}</li>
            ))}
          </ul>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Analize urmărite" value={data.lab_summary.total_analytes} />
        <Stat label="Valori anormale" value={data.lab_summary.abnormal_count} />
        <Stat label="Valori critice" value={data.lab_summary.critical_count} />
        <Stat label="Notificări noi" value={data.unread_notifications} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <div className="mb-3 flex items-center gap-2 font-semibold">
            <FileText size={18} className="text-brand-blue" /> Documente recente
          </div>
          {data.recent_documents.length === 0 ? (
            <p className="text-sm text-muted">Niciun document încă.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {data.recent_documents.map((d) => (
                <li key={d.id} className="flex items-center justify-between">
                  <span className="truncate">{d.original_filename}</span>
                  <Badge tone={d.status === "done" ? "green" : "amber"}>
                    {d.status}
                  </Badge>
                </li>
              ))}
            </ul>
          )}
          <Link
            href="/documents"
            className="mt-3 inline-block text-sm text-brand-blue hover:underline"
          >
            Vezi toate →
          </Link>
        </Card>

        <Card>
          <div className="mb-3 flex items-center gap-2 font-semibold">
            <CalendarDays size={18} className="text-brand-violet" /> Programări
            viitoare
          </div>
          {data.upcoming_appointments.length === 0 ? (
            <p className="text-sm text-muted">Nicio programare.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {data.upcoming_appointments.map((a) => (
                <li key={a.id} className="flex items-center justify-between">
                  <span className="truncate">{a.title}</span>
                  <span className="text-muted">
                    {new Date(a.starts_at).toLocaleDateString("ro-RO")}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <div className="mb-3 flex items-center gap-2 font-semibold">
            <Pill size={18} className="text-brand-green" /> Tratamente active
          </div>
          {data.active_medications.length === 0 ? (
            <p className="text-sm text-muted">Niciun tratament activ.</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {data.active_medications.map((m) => (
                <li key={m.id}>
                  {m.name} {m.dose && <span className="text-muted">· {m.dose}</span>}
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <div className="mb-3 flex items-center gap-2 font-semibold">
            <Lightbulb size={18} className="text-amber-500" /> Recomandări
          </div>
          {data.recommendations_preview.length === 0 ? (
            <p className="text-sm text-muted">Nicio recomandare momentan.</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {data.recommendations_preview.map((r, i) => (
                <li key={i}>• {r}</li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <p className="flex items-center gap-2 text-xs text-muted">
        <Bell size={14} /> Informațiile sunt orientative și nu înlocuiesc
        consultul medical.
      </p>
    </div>
  );
}
