"use client";

import { useRef, useState } from "react";
import { Activity, HeartPulse, Info, Trash2, Upload } from "lucide-react";
import { useFetch } from "@/lib/hooks";
import { api } from "@/lib/api";
import type {
  HealthImportResult,
  HealthSourceId,
  HealthSourceInfo,
  HealthSummary,
} from "@/lib/types";
import { Badge, Button, Card, Spinner } from "@/components/ui";

const ACCEPT: Record<HealthSourceId, string> = {
  apple_health: ".zip,.xml",
  google_health: ".json",
  huawei_health: ".json",
  manual: "",
};

function SourceCard({
  info,
  onImported,
  onDeleted,
}: {
  info: HealthSourceInfo;
  onImported: () => void;
  onDeleted: () => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function upload(e: React.FormEvent) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    setMsg(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const r = await api.postForm<HealthImportResult>(
        `/health-data/import/${info.source}`,
        form,
      );
      setMsg(r.message);
      if (fileRef.current) fileRef.current.value = "";
      onImported();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import eșuat");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!confirm(`Ștergi datele importate din ${info.label}?`)) return;
    await api.del(`/health-data/${info.source}`);
    onDeleted();
  }

  return (
    <Card className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 font-semibold">
          <HeartPulse size={18} className="text-brand-violet" />
          {info.label}
        </div>
        {info.connected ? (
          <Badge tone="green">{info.sample_count} valori</Badge>
        ) : (
          <Badge>Neconectat</Badge>
        )}
      </div>

      <p className="flex items-start gap-1.5 text-xs text-muted">
        <Info size={14} className="mt-0.5 shrink-0" />
        {info.how_to}
      </p>

      <form onSubmit={upload} className="flex flex-wrap items-center gap-2">
        <input
          ref={fileRef}
          type="file"
          accept={ACCEPT[info.source]}
          className="text-sm"
          required
        />
        <Button type="submit" disabled={busy}>
          <Upload size={16} />
          {busy ? "Se importă…" : "Importă"}
        </Button>
        {info.connected && (
          <Button type="button" variant="outline" onClick={remove}>
            <Trash2 size={16} />
          </Button>
        )}
      </form>
      <p className="text-xs text-muted">Format acceptat: {info.accepts}</p>
      {msg && <p className="text-sm text-brand-green">{msg}</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
    </Card>
  );
}

export default function HealthPage() {
  const sources = useFetch<HealthSourceInfo[]>("/health-data/sources");
  const summary = useFetch<HealthSummary>("/health-data/summary");

  function reloadAll() {
    sources.reload();
    summary.reload();
  }

  async function loadSample() {
    await api.post("/health-data/import-sample");
    reloadAll();
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Date de sănătate</h1>
        <Button variant="outline" onClick={loadSample}>
          <Activity size={16} /> Încarcă date demo
        </Button>
      </div>

      <p className="text-sm text-muted">
        Importă măsurătorile din aplicațiile de sănătate (pași, puls, somn,
        greutate, SpO₂ etc.). Datele sunt normalizate și urmărite în timp.
      </p>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {sources.loading ? (
          <Spinner />
        ) : (
          (sources.data || []).map((s) => (
            <SourceCard
              key={s.source}
              info={s}
              onImported={reloadAll}
              onDeleted={reloadAll}
            />
          ))
        )}
      </div>

      <Card>
        <h2 className="mb-3 text-lg font-semibold">Sinteză măsurători</h2>
        {summary.loading ? (
          <Spinner />
        ) : !summary.data || summary.data.total_samples === 0 ? (
          <p className="text-sm text-muted">
            Nicio măsurătoare încă. Importă un export sau încarcă date demo.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-muted">
                  <th className="py-2 pr-4 font-medium">Metrică</th>
                  <th className="py-2 pr-4 font-medium">Ultima</th>
                  <th className="py-2 pr-4 font-medium">Medie</th>
                  <th className="py-2 pr-4 font-medium">Min–Max</th>
                  <th className="py-2 pr-4 font-medium">Nr.</th>
                </tr>
              </thead>
              <tbody>
                {summary.data.metrics.map((m) => (
                  <tr key={m.metric_type} className="border-b border-border/60">
                    <td className="py-2 pr-4 font-medium">{m.label}</td>
                    <td className="py-2 pr-4">
                      {m.latest_value ?? "—"} {m.unit}
                    </td>
                    <td className="py-2 pr-4">{m.avg ?? "—"}</td>
                    <td className="py-2 pr-4 text-muted">
                      {m.min ?? "—"}–{m.max ?? "—"}
                    </td>
                    <td className="py-2 pr-4 text-muted">{m.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <p className="text-xs text-muted">
        ⚠️ Datele importate au caracter informativ și nu înlocuiesc evaluarea
        medicală.
      </p>
    </div>
  );
}
