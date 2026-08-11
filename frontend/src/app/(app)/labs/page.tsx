"use client";

import { useState } from "react";
import { Activity, Sparkles, TrendingUp } from "lucide-react";
import { useFetch } from "@/lib/hooks";
import { api } from "@/lib/api";
import type { LabResult } from "@/lib/types";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  PageHeader,
  Spinner,
  flagTone,
} from "@/components/ui";

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
                  <div className="font-semibold">{r.analyte}</div>
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
                    onClick={() => trend(r.analyte)}
                    disabled={trending === r.analyte}
                  >
                    <TrendingUp size={16} />
                    {trending === r.analyte ? "…" : "Evoluție AI"}
                  </Button>
                </div>
              </div>
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
