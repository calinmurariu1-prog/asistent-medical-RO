"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";
import { useFetch } from "@/lib/hooks";
import { api } from "@/lib/api";
import type { LabResult } from "@/lib/types";
import { Badge, Button, Card, Spinner, flagTone } from "@/components/ui";

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

  if (loading) return <Spinner />;
  const results = data || [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Analize</h1>

      {results.length === 0 ? (
        <Card>
          <p className="text-sm text-muted">
            Nu ai analize încă. Încarcă un document în secțiunea Documente sau
            adaugă manual.
          </p>
        </Card>
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
                <div className="flex items-center gap-3">
                  <Badge tone={flagTone(r.flag)}>{FLAG_LABEL[r.flag]}</Badge>
                  <Button
                    variant="outline"
                    onClick={() => explain(r.id)}
                    disabled={explaining === r.id}
                  >
                    <Sparkles size={16} />
                    {explaining === r.id ? "…" : "Explică"}
                  </Button>
                </div>
              </div>
              {r.ai_explanation && (
                <p className="mt-3 rounded-lg bg-bg p-3 text-sm text-fg/80">
                  {r.ai_explanation}
                </p>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
