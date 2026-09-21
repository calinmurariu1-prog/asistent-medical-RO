"use client";

import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import type { AiSkill } from "@/lib/types";
import { Button, Card, Input, PageHeader, Spinner } from "@/components/ui";

interface SkillResult {
  result: string;
  emergency?: boolean;
  sources?: {ref: string; title: string; url: string | null}[];
}

const INPUT_LABELS: Record<string, string> = {
  name: "Substanța activă",
  medications: "Substanțe active separate prin punct și virgulă",
  concern: "Preocuparea ta",
  text: "Textul medical",
  condition: "Afecțiunea",
  symptom: "Simptomul",
};

export default function AssistantPage() {
  const [skills, setSkills] = useState<AiSkill[]>([]);
  const [active, setActive] = useState<AiSkill | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [result, setResult] = useState<SkillResult | null>(null);
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
      const r = await api.post<SkillResult>(
        `/ai/skills/${active.name}`,
        { inputs: values },
      );
      setResult(r);
    } catch (e) {
      setResult({result: e instanceof Error ? e.message : "Eroare"});
    } finally {
      setLoading(false);
    }
  }

  const ready = active?.inputs.every((k) => (values[k] || "").trim()) ?? false;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Asistent AI"
        subtitle="Capabilități AI orientative — alege una și completează câmpurile."
        icon={Sparkles}
      />

      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        <div className="space-y-2">
          {skills.map((s) => (
            <button
              key={s.name}
              onClick={() => select(s)}
              className={`w-full rounded-2xl border p-3 text-left text-sm transition ${
                active?.name === s.name
                  ? "border-brand-blue bg-brand-blue/5"
                  : "border-border hover:bg-surface-2"
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
                    maxLength={12000}
                    placeholder={INPUT_LABELS[key] || key}
                    value={values[key] || ""}
                    onChange={(e) => setValues({ ...values, [key]: e.target.value })}
                    rows={5}
                    className="w-full rounded-xl border border-border bg-surface px-4 py-2.5 text-sm outline-none focus:border-brand-blue focus:ring-2 focus:ring-brand-blue/20"
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
                <div role={result.emergency ? "alert" : "status"} className="whitespace-pre-wrap break-words rounded-2xl bg-surface-2 p-4 text-sm">
                  {result.emergency && <p className="mb-2 font-semibold text-red-600 dark:text-red-400">Posibilă urgență — nu aștepta un răspuns AI</p>}
                  <p>{result.result}</p>
                  {result.sources?.map(source => source.url ? <a key={source.ref} className="mt-2 block text-primary underline" href={source.url} target="_blank" rel="noopener noreferrer">[{source.ref}] {source.title}</a> : <p key={source.ref} className="mt-2 text-muted">[{source.ref}] {source.title}</p>)}
                </div>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
