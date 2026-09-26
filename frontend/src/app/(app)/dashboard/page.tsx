"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Bell,
  CalendarDays,
  FileText,
  HeartPulse,
  Lightbulb,
  Pill,
  Sparkles,
} from "lucide-react";
import { useFetch } from "@/lib/hooks";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Dashboard, HealthSummary } from "@/lib/types";
import { Badge, Button, Card, Spinner } from "@/components/ui";
import { HealthRing } from "@/components/health-ring";
import { Sparkline } from "@/components/line-chart";
import { Reveal } from "@/components/motion";

const STAT_STYLES = [
  { tint: "bg-brand-blue/10", fg: "text-brand-blue" },
  { tint: "bg-amber-500/10", fg: "text-amber-600" },
  { tint: "bg-red-500/10", fg: "text-red-600" },
  { tint: "bg-brand-green/10", fg: "text-brand-green" },
];

function Stat({
  label,
  value,
  icon: Icon,
  idx,
}: {
  label: string;
  value: number | string;
  icon: typeof Activity;
  idx: number;
}) {
  const s = STAT_STYLES[idx % STAT_STYLES.length];
  return (
    <Card className="flex items-center gap-3 p-4">
      <span className={`flex h-11 w-11 items-center justify-center rounded-2xl ${s.tint} ${s.fg}`}>
        <Icon size={20} />
      </span>
      <div>
        <div className="text-2xl font-bold leading-none tabular-nums">{value}</div>
        <div className="mt-1 text-xs text-muted">{label}</div>
      </div>
    </Card>
  );
}

const RING_CONFIG: Record<
  string,
  { goal: number; color: string; order: number; display?: (v: number) => string; unit?: string }
> = {
  steps: { goal: 10000, color: "rgb(var(--brand-green))", order: 1, unit: "pași" },
  sleep: {
    goal: 480,
    color: "rgb(var(--brand-violet))",
    order: 2,
    display: (v) => `${(v / 60).toFixed(1)}h`,
    unit: "somn",
  },
  oxygen_saturation: { goal: 100, color: "rgb(var(--brand-blue))", order: 3, unit: "%" },
  heart_rate: { goal: 100, color: "rgb(var(--brand-mint))", order: 4, unit: "bpm" },
  active_energy: { goal: 500, color: "rgb(var(--brand-green))", order: 5, unit: "kcal" },
};

export default function DashboardPage() {
  const { user } = useAuth();
  const { data, loading } = useFetch<Dashboard>("/dashboard");
  const health = useFetch<HealthSummary>("/health-data/summary");
  const [summary, setSummary] = useState<string | null>(null);
  const [summarizing, setSummarizing] = useState(false);
  const [sparks, setSparks] = useState<Record<string, number[]>>({});

  const rings = (health.data?.metrics || [])
    .filter((m) => RING_CONFIG[m.metric_type] && m.latest_value != null)
    .sort((a, b) => RING_CONFIG[a.metric_type].order - RING_CONFIG[b.metric_type].order)
    .slice(0, 4);
  const ringKey = rings.map((r) => r.metric_type).join(",");

  useEffect(() => {
    if (!ringKey) return;
    let cancelled = false;
    Promise.all(
      ringKey.split(",").map((metric) =>
        api
          .get<{ value: number }[]>(`/health-data/metrics/${metric}`)
          .then((rows) => [metric, rows.map((r) => r.value)] as const)
          .catch(() => [metric, []] as const),
      ),
    ).then((entries) => {
      if (!cancelled) setSparks(Object.fromEntries(entries));
    });
    return () => {
      cancelled = true;
    };
  }, [ringKey]);

  async function summarize() {
    setSummarizing(true);
    try {
      const r = await api.post<{ result: string }>("/ai/summarize-record");
      setSummary(r.result);
    } finally {
      setSummarizing(false);
    }
  }

  if (loading) return <Spinner />;
  if (!data) return <p className="text-muted">Nu s-au putut încărca datele.</p>;

  const name = user?.full_name?.split(" ")[0] || user?.email?.split("@")[0] || "";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">
            Bună{name ? `, ${name}` : ""} <span className="align-middle">👋</span>
          </h1>
          <p className="text-sm text-muted">Iată sănătatea ta pe scurt.</p>
        </div>
        <Button variant="outline" onClick={summarize} disabled={summarizing}>
          <Sparkles size={16} />
          {summarizing ? "Se generează…" : "Rezumat AI"}
        </Button>
      </div>

      {summary && (
        <Card className="border-brand-violet/30 bg-brand-violet/5">
          <div className="mb-2 flex items-center gap-2 font-semibold text-brand-violet">
            <Sparkles size={18} /> Rezumat AI
          </div>
          <p className="whitespace-pre-wrap text-sm">{summary}</p>
        </Card>
      )}

      {/* Health rings */}
      <Reveal className="brand-gradient-3 rounded-3xl border-0 text-white shadow-soft">
      <Card className="border-0 bg-transparent text-white shadow-none">
        <div className="mb-4 flex items-center gap-2 font-semibold">
          <HeartPulse size={18} /> Activitatea ta
        </div>
        {rings.length > 0 ? (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {rings.map((m) => {
              const cfg = RING_CONFIG[m.metric_type];
              return (
                <Link
                  key={m.metric_type}
                  href={`/health/${m.metric_type}`}
                  className="rounded-2xl bg-white/15 py-4 backdrop-blur transition hover:bg-white/25"
                >
                  <HealthRing
                    value={m.latest_value as number}
                    goal={cfg.goal}
                    color="#ffffff"
                    label={m.label}
                    unit={cfg.unit}
                    displayValue={cfg.display?.(m.latest_value as number)}
                  />
                  {sparks[m.metric_type] && sparks[m.metric_type].length > 1 && (
                    <div className="mt-2 px-3">
                      <Sparkline values={sparks[m.metric_type]} color="#ffffff" />
                    </div>
                  )}
                </Link>
              );
            })}
          </div>
        ) : (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-white/90">
              Conectează-ți ceasul ca să vezi pașii, somnul și pulsul aici.
            </p>
            <Link href="/health">
              <span className="inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-semibold text-brand-blue">
                <Activity size={16} /> Conectează
              </span>
            </Link>
          </div>
        )}
      </Card>
      </Reveal>

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

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Analize urmărite" value={data.lab_summary.total_analytes} icon={Activity} idx={0} />
        <Stat label="În afara intervalului" value={data.lab_summary.abnormal_count} icon={AlertTriangle} idx={1} />
        <Stat label="Neevaluabile" value={data.lab_summary.unknown_count ?? "—"} icon={FileText} idx={2} />
        <Link href="/notifications" aria-label={`Deschide cele ${data.unread_notifications} notificări noi`}><Stat label="Notificări noi" value={data.unread_notifications} icon={Bell} idx={3} /></Link>
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
            className="mt-3 inline-block text-sm font-medium text-brand-blue hover:underline"
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
