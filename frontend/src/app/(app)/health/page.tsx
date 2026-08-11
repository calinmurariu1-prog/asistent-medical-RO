"use client";

import { useEffect, useRef, useState } from "react";
import {
  Activity,
  HeartPulse,
  Info,
  Smartphone,
  Trash2,
  Upload,
  Watch,
} from "lucide-react";
import { useFetch } from "@/lib/hooks";
import { api } from "@/lib/api";
import {
  healthNativeAvailable,
  isAutoSyncEnabled,
  setAutoSyncEnabled,
  syncNativeHealth,
} from "@/lib/health-native";
import type {
  HealthDevice,
  HealthImportResult,
  HealthSourceId,
  HealthSourceInfo,
  HealthSummary,
} from "@/lib/types";
import { Badge, Button, Card, PageHeader, Spinner } from "@/components/ui";
import { LineChart } from "@/components/line-chart";

const ACCEPT: Record<HealthSourceId, string> = {
  apple_health: ".zip,.xml",
  google_health: ".json",
  huawei_health: ".json",
  bluetooth: "",
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
  const devices = useFetch<HealthDevice[]>("/health-data/devices");
  const [native, setNative] = useState(false);
  const [autoSync, setAutoSync] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);
  const [syncErr, setSyncErr] = useState<string | null>(null);

  useEffect(() => {
    healthNativeAvailable().then(setNative);
    isAutoSyncEnabled().then(setAutoSync);
  }, []);

  async function toggleAutoSync() {
    const next = !autoSync;
    setAutoSync(next);
    await setAutoSyncEnabled(next);
    if (next) syncPhone();
  }

  const [openChart, setOpenChart] = useState<string | null>(null);
  const [chartData, setChartData] = useState<
    Record<string, { label: string; value: number }[]>
  >({});

  async function toggleChart(metric: string) {
    if (openChart === metric) {
      setOpenChart(null);
      return;
    }
    setOpenChart(metric);
    if (!chartData[metric]) {
      const rows = await api.get<{ value: number; recorded_at: string }[]>(
        `/health-data/metrics/${metric}`,
      );
      setChartData((c) => ({
        ...c,
        [metric]: rows.map((r) => ({
          label: new Date(r.recorded_at).toLocaleDateString("ro-RO", {
            day: "2-digit",
            month: "short",
          }),
          value: r.value,
        })),
      }));
    }
  }

  function reloadAll() {
    sources.reload();
    summary.reload();
    devices.reload();
    setChartData({});
  }

  async function loadSample() {
    await api.post("/health-data/import-sample");
    reloadAll();
  }

  async function syncPhone() {
    setSyncing(true);
    setSyncMsg(null);
    setSyncErr(null);
    try {
      const r = await syncNativeHealth(30);
      setSyncMsg(r.message);
      reloadAll();
    } catch (err) {
      setSyncErr(err instanceof Error ? err.message : "Sincronizare eșuată");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Date de sănătate"
        subtitle="Pași, puls, somn, greutate, SpO₂ — normalizate și urmărite în timp."
        icon={HeartPulse}
        action={
          <Button variant="outline" onClick={loadSample}>
            <Activity size={16} /> Date demo
          </Button>
        }
      />

      {native && (
        <Card className="space-y-3 ring-2 ring-brand-blue/30">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-start gap-2">
              <Smartphone size={18} className="mt-0.5 text-brand-blue" />
              <div>
                <p className="font-semibold">Sincronizare directă de pe telefon</p>
                <p className="text-sm text-muted">
                  Citește automat din Sănătate (HealthKit) / Health Connect și
                  detectează ceasul — fără export de fișiere.
                </p>
              </div>
            </div>
            <Button onClick={syncPhone} disabled={syncing}>
              <HeartPulse size={16} />
              {syncing ? "Se sincronizează…" : "Sincronizează acum"}
            </Button>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={autoSync}
              onChange={toggleAutoSync}
              className="h-4 w-4 accent-brand-blue"
            />
            Sincronizare automată la deschiderea aplicației
          </label>
        </Card>
      )}
      {syncMsg && <p className="text-sm text-brand-green">{syncMsg}</p>}
      {syncErr && <p className="text-sm text-red-600">{syncErr}</p>}

      {(devices.data || []).length > 0 && (
        <Card className="space-y-3">
          <h2 className="flex items-center gap-2 text-lg font-semibold">
            <Watch size={18} className="text-brand-violet" /> Dispozitive detectate
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {(devices.data || []).map((d) => (
              <div
                key={`${d.source}-${d.name}`}
                className="flex items-center justify-between rounded-lg border border-border p-3"
              >
                <div>
                  <p className="font-medium">{d.name}</p>
                  <p className="text-xs text-muted">
                    {d.vendor ? `${d.vendor} · ` : ""}
                    {d.metrics.length} metrici
                  </p>
                </div>
                <Badge tone="green">activ</Badge>
              </div>
            ))}
          </div>
        </Card>
      )}

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
          <div className="space-y-2">
            {summary.data.metrics.map((m) => {
              const open = openChart === m.metric_type;
              return (
                <div
                  key={m.metric_type}
                  className="rounded-2xl border border-border/70"
                >
                  <button
                    onClick={() => toggleChart(m.metric_type)}
                    className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition hover:bg-surface-2"
                  >
                    <span className="font-medium">{m.label}</span>
                    <span className="flex items-center gap-3 text-sm">
                      <span className="font-semibold">
                        {m.latest_value ?? "—"} {m.unit}
                      </span>
                      <span className="text-xs text-muted">
                        medie {m.avg ?? "—"} · {m.count} măs.
                      </span>
                      <span
                        className={`text-muted transition ${open ? "rotate-90" : ""}`}
                      >
                        ›
                      </span>
                    </span>
                  </button>
                  {open && (
                    <div className="px-3 pb-3">
                      {!chartData[m.metric_type] ? (
                        <Spinner />
                      ) : chartData[m.metric_type].length < 2 ? (
                        <p className="px-1 pb-2 text-sm text-muted">
                          Este nevoie de cel puțin două măsurători pentru grafic.
                        </p>
                      ) : (
                        <LineChart
                          unit={m.unit}
                          color="rgb(var(--brand-violet))"
                          points={chartData[m.metric_type]}
                        />
                      )}
                    </div>
                  )}
                </div>
              );
            })}
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
