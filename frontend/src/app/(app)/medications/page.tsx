"use client";

import { useState } from "react";
import { AlertTriangle, Pill, Plus, ShieldCheck, Sparkles, Trash2 } from "lucide-react";
import { useFetch } from "@/lib/hooks";
import { api } from "@/lib/api";
import type { Medication } from "@/lib/types";
import { Badge, Button, Card, Input, PageHeader, Spinner } from "@/components/ui";

interface CheckResult {
  interactions: { drug_a: string; drug_b: string; severity: string; description: string }[];
  duplicates: { substance: string; medications: string[] }[];
  disclaimer: string;
}

export default function MedicationsPage() {
  const { data, loading, reload } = useFetch<Medication[]>("/medications");
  const [name, setName] = useState("");
  const [substance, setSubstance] = useState("");
  const [dose, setDose] = useState("");
  const [check, setCheck] = useState<CheckResult | null>(null);
  const [explains, setExplains] = useState<Record<number, string>>({});
  const [explaining, setExplaining] = useState<number | null>(null);

  async function explain(med: Medication) {
    setExplaining(med.id);
    try {
      const r = await api.post<{ result: string }>("/ai/skills/explain_medication", {
        inputs: { name: med.name },
      });
      setExplains((e) => ({ ...e, [med.id]: r.result }));
    } finally {
      setExplaining(null);
    }
  }

  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    await api.post("/medications", {
      name,
      active_substance: substance || null,
      dose: dose || null,
    });
    setName("");
    setSubstance("");
    setDose("");
    reload();
  }

  async function remove(id: number) {
    await api.del(`/medications/${id}`);
    reload();
  }

  async function runCheck() {
    setCheck(await api.get<CheckResult>("/medications/check"));
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Medicamente"
        subtitle="Tratamentele tale active, cu verificare de interacțiuni."
        icon={Pill}
        action={
          <Button variant="outline" onClick={runCheck}>
            <ShieldCheck size={16} /> Verifică interacțiuni
          </Button>
        }
      />

      <Card>
        <form onSubmit={add} className="flex flex-wrap gap-2">
          <Input
            className="flex-1"
            placeholder="Denumire"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <Input
            className="flex-1"
            placeholder="Substanță activă"
            value={substance}
            onChange={(e) => setSubstance(e.target.value)}
          />
          <Input
            className="w-32"
            placeholder="Doză"
            value={dose}
            onChange={(e) => setDose(e.target.value)}
          />
          <Button type="submit">
            <Plus size={16} /> Adaugă
          </Button>
        </form>
      </Card>

      {check && (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <div className="mb-2 flex items-center gap-2 font-semibold text-amber-600">
            <AlertTriangle size={18} /> Rezultat verificare
          </div>
          {check.interactions.length === 0 && check.duplicates.length === 0 ? (
            <p className="text-sm">Nu s-au găsit interacțiuni sau dubluri.</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {check.interactions.map((it, i) => (
                <li key={`i${i}`}>
                  <Badge tone="red">{it.severity}</Badge> {it.drug_a} + {it.drug_b}:{" "}
                  {it.description}
                </li>
              ))}
              {check.duplicates.map((d, i) => (
                <li key={`d${i}`}>
                  <Badge tone="amber">dublură</Badge> {d.substance}:{" "}
                  {d.medications.join(", ")}
                </li>
              ))}
            </ul>
          )}
          <p className="mt-2 text-xs text-muted">{check.disclaimer}</p>
        </Card>
      )}

      {loading ? (
        <Spinner />
      ) : (
        <div className="space-y-2">
          {(data || []).map((m) => (
            <Card key={m.id}>
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-medium">{m.name}</span>{" "}
                  {m.dose && <span className="text-muted">· {m.dose}</span>}
                  {!m.is_active && <Badge>inactiv</Badge>}
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    className="px-2.5 py-1.5"
                    onClick={() => explain(m)}
                    disabled={explaining === m.id}
                  >
                    <Sparkles size={15} />
                    {explaining === m.id ? "…" : "Explică"}
                  </Button>
                  <button
                    onClick={() => remove(m.id)}
                    className="text-muted hover:text-red-600"
                    aria-label="Șterge"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
              {explains[m.id] && (
                <div className="mt-3 whitespace-pre-wrap rounded-lg bg-bg p-3 text-sm">
                  {explains[m.id]}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
