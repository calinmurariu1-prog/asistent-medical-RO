"use client";

import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import type { AiSkill } from "@/lib/types";
import { Button, Card, Input, Spinner } from "@/components/ui";

const INPUT_LABELS: Record<string, string> = {
  name: "Denumire medicament",
  concern: "Preocuparea ta",
  text: "Textul medical",
  condition: "Afecțiunea",
  symptom: "Simptomul",
};

export default function AssistantPage() {
  const [skills, setSkills] = useState<AiSkill[]>([]);
  const [active, setActive] = useState<AiSkill | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get<AiSkill[]>("/ai/skills").then(setSkills).catch(() => {});
  }, []);

  function select(skill: AiSkill) {
    setActive(skill);
    setValues({});
    setResult(null);
  }

  async function run() {
    if (!active) return;
    setLoading(true);
    setResult(null);
    try {
      const r = await api.post<{ result: string }>(
        `/ai/skills/${active.name}`,
        { inputs: values },
      );
      setResult(r.result);
    } catch (e) {
      setResult(e instanceof Error ? e.message : "Eroare");
    } finally {
      setLoading(false);
    }
  }

  const ready = active?.inputs.every((k) => (values[k] || "").trim()) ?? false;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Asistent AI</h1>
        <p className="text-muted text-sm">
          Capabilități AI orientative — alege una și completează câmpurile.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        <div className="space-y-2">
          {skills.map((s) => (
            <button
              key={s.name}
              onClick={() => select(s)}
              className={`w-full rounded-xl border p-3 text-left text-sm transition ${
                active?.name === s.name
                  ? "border-brand-blue bg-brand-blue/5"
                  : "border-border hover:bg-bg"
              }`}
            >
              <div className="font-medium">{s.title}</div>
              <div className="text-muted text-xs">{s.description}</div>
            </button>
          ))}
        </div>

        <Card>
          {!active ? (
            <p className="text-muted text-sm">Selectează o capabilitate din stânga.</p>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-2 font-semibold">
                <Sparkles size={18} className="text-brand-violet" /> {active.title}
              </div>
              {active.inputs.map((key) =>
                key === "text" ? (
                  <textarea
                    key={key}
                    placeholder={INPUT_LABELS[key] || key}
                    value={values[key] || ""}
                    onChange={(e) => setValues({ ...values, [key]: e.target.value })}
                    rows={5}
                    className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm"
                  />
                ) : (
                  <Input
                    key={key}
                    placeholder={INPUT_LABELS[key] || key}
                    value={values[key] || ""}
                    onChange={(e) => setValues({ ...values, [key]: e.target.value })}
                  />
                ),
              )}
              <Button onClick={run} disabled={!ready || loading}>
                <Sparkles size={16} /> {loading ? "Se generează…" : "Rulează"}
              </Button>

              {loading && <Spinner />}
              {result && (
                <div className="whitespace-pre-wrap rounded-lg bg-bg p-4 text-sm">
                  {result}
                </div>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
