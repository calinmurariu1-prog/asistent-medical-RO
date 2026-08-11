"use client";

import Link from "next/link";
import { ArrowLeft, HeartPulse } from "lucide-react";
import { useFetch } from "@/lib/hooks";
import type { HealthSummary } from "@/lib/types";
import { Card, EmptyState, PageHeader, Spinner } from "@/components/ui";
import { LineChart } from "@/components/line-chart";

interface Sample {
  value: number;
  unit: string;
  recorded_at: string;
}

function shortDate(d: string): string {
  return new Date(d).toLocaleDateString("ro-RO", {
    day: "2-digit",
    month: "short",
  });
}

export function MetricDetail({ metric }: { metric: string }) {
  const summary = useFetch<HealthSummary>("/health-data/summary");
  const series = useFetch<Sample[]>(`/health-data/metrics/${metric}`);

  if (summary.loading || series.loading) return <Spinner />;

  const info = summary.data?.metrics.find((m) => m.metric_type === metric);
  const points = (series.data || []).map((s) => ({
    label: shortDate(s.recorded_at),
    value: s.value,
  }));

  return (
    <div className="space-y-6">
      <Link
        href="/health"
        className="inline-flex items-center gap-1 text-sm font-medium text-brand-blue"
      >
        <ArrowLeft size={16} /> Date de sănătate
      </Link>

      <PageHeader
        title={info?.label || metric}
        subtitle={info ? `Ultima: ${info.latest_value ?? "—"} ${info.unit}` : undefined}
        icon={HeartPulse}
      />

      {points.length === 0 ? (
        <EmptyState
          icon={HeartPulse}
          title="Nicio măsurătoare"
          hint="Sincronizează-ți ceasul sau importă un fișier pentru a vedea evoluția."
        />
      ) : (
        <>
          <Card>
            <LineChart
              unit={info?.unit}
              color="rgb(var(--brand-violet))"
              height={200}
              points={points}
            />
          </Card>

          {info && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                ["Ultima", info.latest_value],
                ["Medie", info.avg],
                ["Minim", info.min],
                ["Maxim", info.max],
              ].map(([label, val]) => (
                <Card key={label as string} className="p-4 text-center">
                  <div className="text-xl font-bold">
                    {val ?? "—"}
                    <span className="ml-1 text-xs font-normal text-muted">
                      {info.unit}
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-muted">{label}</div>
                </Card>
              ))}
            </div>
          )}

          <Card>
            <h2 className="mb-3 text-lg font-semibold">Măsurători recente</h2>
            <ul className="divide-y divide-border/60 text-sm">
              {(series.data || [])
                .slice()
                .reverse()
                .slice(0, 15)
                .map((s, i) => (
                  <li key={i} className="flex items-center justify-between py-2">
                    <span className="text-muted">{shortDate(s.recorded_at)}</span>
                    <span className="font-medium">
                      {s.value} {s.unit}
                    </span>
                  </li>
                ))}
            </ul>
          </Card>
        </>
      )}
    </div>
  );
}
