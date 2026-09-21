"use client";

import { type FormEvent, useState } from "react";
import { Activity, AlertTriangle, LineChart as LineChartIcon, Sparkles, TrendingUp } from "lucide-react";
import { useFetch } from "@/lib/hooks";
import { api } from "@/lib/api";
import type { LabResult, LabSeries } from "@/lib/types";
import {
  Input,
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
  unknown: "Neevaluabil",
  normal: "În interval",
  high: "Crescut",
  low: "Scăzut",
  critical_high: "Critic ↑",
  critical_low: "Critic ↓",
};

export default function LabsPage() {
  const { data, loading, error: loadError, setData } = useFetch<LabResult[]>("/labs");
  const [explaining, setExplaining] = useState<number | null>(null);
  const [trends, setTrends] = useState<Record<string, string>>({});
  const [trending, setTrending] = useState<string | null>(null);
  const [charts, setCharts] = useState<Record<string, LabSeries | null>>({});
  const [charting, setCharting] = useState<string | null>(null);

  const [editing, setEditing] = useState<LabResult | "new" | null>(null);
  const [deleting, setDeleting] = useState<LabResult | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function refreshResults() {
    setCharts({}); setTrends({});
    setData(await api.get<LabResult[]>("/labs"));
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editing) return;
    const form = new FormData(event.currentTarget);
    const text = (name: string) => String(form.get(name) || "").trim();
    const number = (name: string) => text(name) === "" ? null : Number(text(name));
    const payload = {analyte: text("analyte"), value: number("value"),
      value_text: text("value_text") || null, unit: text("unit") || null,
      ref_low: number("ref_low"), ref_high: number("ref_high"),
      measured_on: text("measured_on") || null};
    if (payload.value === null && !payload.value_text) {
      setError("Introdu o valoare numerică sau un rezultat textual."); return;
    }
    setSaving(true); setError("");
    try {
      if (editing === "new") await api.post("/labs", payload);
      else await api.put(`/labs/${editing.id}`, payload);
      setEditing(null);
      await refreshResults();
    } catch (e) { setError(e instanceof Error ? e.message : "Rezultatul nu a putut fi salvat."); }
    finally { setSaving(false); }
  }

  async function remove() {
    if (!deleting) return;
    setSaving(true); setError("");
    try {
      await api.del(`/labs/${deleting.id}`);
      setDeleting(null);
      await refreshResults();
    } catch (e) { setError(e instanceof Error ? e.message : "Rezultatul nu a putut fi șters."); }
    finally { setSaving(false); }
  }

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
    } catch (e) {
      setError(e instanceof Error ? e.message : "Explicația nu este disponibilă.");
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
    } catch (e) {
      setError(e instanceof Error ? e.message : "Comparația nu este disponibilă.");
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
        action={<Button disabled={!!editing || !!deleting || saving} onClick={() => {setError(""); setEditing("new");}}>Adaugă rezultat</Button>}
      />
      {(error || loadError) && <p role="alert" className="rounded-xl border border-red-500/30 p-3 text-sm">{error || loadError}</p>}
      {editing && <Card>
        <form onSubmit={save} className="space-y-4" key={editing === "new" ? "new" : editing.id}>
          <h2 className="font-semibold">{editing === "new" ? "Rezultat introdus manual" : "Corectează rezultatul"}</h2>
          <p className="text-sm text-muted">Transcrie valorile și intervalele exact din buletinul de analize. Confirmarea transcrierii nu reprezintă validare medicală.</p>
          {editing !== "new" && editing.document_id && <p className="text-sm text-muted">Originalul rămâne neschimbat. Reprocesarea documentului va înlocui această corectură.</p>}
          <div className="grid gap-4 sm:grid-cols-2">
            {([
              ["analyte", "Denumirea analizei", "text"], ["value", "Valoare numerică", "number"],
              ["value_text", "Rezultat textual", "text"], ["unit", "Unitate", "text"],
              ["ref_low", "Limita inferioară", "number"], ["ref_high", "Limita superioară", "number"],
              ["measured_on", "Data recoltării", "date"],
            ] as const).map(([name, label, type]) => <label key={name} className="block text-sm">
              {label}
              <Input name={name} type={type} step={type === "number" ? "any" : undefined}
                required={name === "analyte"} maxLength={type === "text" ? (name === "unit" ? 50 : 200) : undefined}
                defaultValue={editing === "new" ? "" : editing[name] ?? ""} disabled={saving} />
            </label>)}
          </div>
          <label className="flex min-h-12 items-center gap-3 text-sm"><input type="checkbox" required disabled={saving} />Am verificat transcrierea cu documentul sursă.</label>
          <div className="flex flex-wrap gap-3">
            <Button type="submit" disabled={saving}>Salvează rezultatul</Button>
            <Button type="button" variant="outline" disabled={saving} onClick={() => setEditing(null)}>Renunță</Button>
          </div>
        </form>
      </Card>}
      {deleting && <Card>
        <p>Ștergi rezultatul {deleting.analyte}? Documentul original rămâne disponibil.</p>
        <div className="mt-3 flex flex-wrap gap-3">
          <Button variant="danger" disabled={saving} onClick={remove}>Confirmă ștergerea</Button>
          <Button variant="outline" disabled={saving} onClick={() => setDeleting(null)}>Păstrează rezultatul</Button>
        </div>
      </Card>}

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
                  <Button variant="outline" disabled={!!editing || !!deleting || saving} onClick={() => {setError(""); setEditing(r);}}>Corectează</Button>
                  <Button variant="outline" disabled={!!editing || !!deleting || saving} onClick={() => {setError(""); setDeleting(r);}}>Șterge</Button>
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
                    {charts[r.analyte]!.comparison_warning ? (
                      <p className="text-sm text-muted">{charts[r.analyte]!.comparison_warning}</p>
                    ) : <LineChart
                      unit={charts[r.analyte]!.unit}
                      refLow={charts[r.analyte]!.ref_low}
                      refHigh={charts[r.analyte]!.ref_high}
                      points={charts[r.analyte]!.points
                        .filter((p) => p.value != null)
                        .map((p) => ({
                          label: shortDate(p.measured_on),
                          value: p.value as number,
                        }))}
                    />}
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
