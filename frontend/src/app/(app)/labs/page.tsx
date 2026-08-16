"use client";

import { useState } from "react";
import { Activity, AlertTriangle, LineChart as LineChartIcon, Sparkles, TrendingUp } from "lucide-react";
import { useFetch } from "@/lib/hooks";
import { api } from "@/lib/api";
import type { LabResult, LabSeries } from "@/lib/types";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  PageHeader,
  Spinner,
  flagTone,
} from "@/components/ui";
import { LineChart } from "@/components/line-chart";

function shortDate(d: string | null): string {
  return d ? new Date(d).toLocaleDateString("ro-RO", { day: "2-digit", month: "short" }) : "";
}

const FLAG_LABEL: Record<string, string> = {
  normal: "Normal",
  high: "Crescut",
  low: "Scăzut",
  critical_high: "Critic ↑",
  critical_low: "Critic ↓",
};

export default function LabsPage() {
  const { data, loading, setData } = useFetch<LabResult[]>("/labs");
  const [explaining, setExplaining] = useState<number | null>(null);
  const [trends, setTrends] = useState<Record<string, string>>({});
  const [trending, setTrending] = useState<string | null>(null);
  const [charts, setCharts] = useState<Record<string, LabSeries | null>>({});
  const [charting, setCharting] = useState<string | null>(null);

  async function chart(analyte: string) {
    if (charts[analyte] !== undefined) {
      // toggle off
      setCharts((c) => {
        const next = { ...c };
        delete next[analyte];
        return next;
      });
      return;
    }
    setCharting(analyte);
    try {
      const s = await api.get<LabSeries>(`/labs/series/${encodeURIComponent(analyte)}`);
      setCharts((c) => ({ ...c, [analyte]: s }));
    } catch {
      setCharts((c) => ({ ...c, [analyte]: null }));
    } finally {
      setCharting(null);
    }
  }

  async function explain(id: number) {
    setExplaining(id);
    try {
      const updated = await api.post<LabResult>(`/labs/${id}/explain`);
      setData((prev) =>
        (prev || []).map((r) => (r.id === id ? updated : r)),
      );
    } finally {
      setExplaining(null);
    }
  }

  async function trend(analyte: string) {
    setTrending(analyte);
    try {
      const r = await api.post<{ result: string }>("/ai/compare-analyte", {
        analyte,
      });
      setTrends((t) => ({ ...t, [analyte]: r.result }));
    } finally {
      setTrending(null);
    }
  }

  if (loading) return <Spinner />;
  const results = data || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Analize"
        subtitle="Valorile tale, explicate și urmărite în timp."
        icon={Activity}
      />

      {results.length === 0 ? (
        <EmptyState
          icon={Activity}
          title="Nu ai analize încă"
          hint="Încarcă un document în secțiunea Documente și AI extrage automat valorile."
        />
      ) : (
        <div className="space-y-3">
          {results.map((r) => (
            <Card key={r.id}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2 font-semibold">
                    {r.analyte}
                    {r.confidence === "unverified" && (
                      <span
                        title="Valoare extrasă automat de AI, neconfirmată din text. Verifică pe documentul original."
                        className="inline-flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[11px] font-medium text-amber-600"
                      >
                        <AlertTriangle size={11} /> De confirmat
                      </span>
                    )}
                  </div>
                  <div className="text-sm text-muted">
                    {r.value ?? r.value_text} {r.unit}
                    {r.ref_low != null && r.ref_high != null && (
                      <span>
                        {" "}
                        · referință {r.ref_low}–{r.ref_high}
                      </span>
                    )}
                    {r.measured_on && <span> · {r.measured_on}</span>}
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <Badge tone={flagTone(r.flag)}>{FLAG_LABEL[r.flag]}</Badge>
                  <Button
                    variant="outline"
                    onClick={() => explain(r.id)}
                    disabled={explaining === r.id}
                  >
                    <Sparkles size={16} />
                    {explaining === r.id ? "…" : "Explică"}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => chart(r.analyte)}
                    disabled={charting === r.analyte}
                  >
                    <LineChartIcon size={16} />
                    {charting === r.analyte ? "…" : "Grafic"}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => trend(r.analyte)}
                    disabled={trending === r.analyte}
                  >
                    <TrendingUp size={16} />
                    {trending === r.analyte ? "…" : "Evoluție AI"}
                  </Button>
                </div>
              </div>

              {charts[r.analyte] !== undefined &&
                (charts[r.analyte] === null ? (
                  <p className="mt-3 text-sm text-muted">
                    Nu există suficiente date pentru un grafic.
                  </p>
                ) : (
                  <div className="mt-3 rounded-2xl bg-surface-2 p-3">
                    <LineChart
                      unit={charts[r.analyte]!.unit}
                      refLow={charts[r.analyte]!.ref_low}
                      refHigh={charts[r.analyte]!.ref_high}
                      points={charts[r.analyte]!.points
                        .filter((p) => p.value != null)
                        .map((p) => ({
                          label: shortDate(p.measured_on),
                          value: p.value as number,
                        }))}
                    />
                  </div>
                ))}
              {r.ai_explanation && (
                <p className="mt-3 rounded-2xl bg-surface-2 p-3 text-sm text-fg/80">
                  {r.ai_explanation}
                </p>
              )}
              {trends[r.analyte] && (
                <p className="mt-3 whitespace-pre-wrap rounded-lg bg-brand-violet/5 p-3 text-sm">
                  {trends[r.analyte]}
                </p>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
