"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  chat,
  ChatMsg,
  exportInline,
  listSkills,
  runSkill,
  saveDocument,
  Skill,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";

const INPUT_LABELS: Record<string, string> = {
  type: "Tip contract",
  parties: "Părțile",
  terms: "Termeni / condiții",
  text: "Textul contractului",
  form: "Formă (SRL / PFA)",
  activity: "Activitatea",
  situation: "Descrie situația",
  idea: "Ideea de afacere",
  business: "Afacerea / ideea",
  employer: "Angajator",
  employee: "Salariat",
  position: "Funcție / post",
  salary: "Salariu brut",
  data_types: "Tipuri de date prelucrate",
};

const LONG_FIELDS = new Set(["text", "situation", "terms"]);

export default function Home() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [active, setActive] = useState<Skill | null>(null);
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [domain, setDomain] = useState<"business" | "juridic">("business");
  const [msg, setMsg] = useState("");
  const [history, setHistory] = useState<ChatMsg[]>([]);
  const [chatLoading, setChatLoading] = useState(false);

  useEffect(() => {
    listSkills()
      .then(setSkills)
      .catch((e) => setError(String(e.message || e)));
  }, []);

  function selectSkill(s: Skill) {
    setActive(s);
    setInputs({});
    setResult("");
    setError("");
  }

  async function onRun() {
    if (!active) return;
    setLoading(true);
    setError("");
    setResult("");
    try {
      setResult(await runSkill(active.name, inputs));
    } catch (e: any) {
      setError(String(e.message || e));
    } finally {
      setLoading(false);
    }
  }

  async function onSend() {
    if (!msg.trim()) return;
    const q = msg.trim();
    const next: ChatMsg[] = [...history, { role: "user", content: q }];
    setHistory(next);
    setMsg("");
    setChatLoading(true);
    try {
      const reply = await chat(q, domain, history);
      setHistory([...next, { role: "assistant", content: reply }]);
    } catch (e: any) {
      setHistory([...next, { role: "assistant", content: "Eroare: " + (e.message || e) }]);
    } finally {
      setChatLoading(false);
    }
  }

  const legal = skills.filter((s) => s.category === "juridic");
  const biz = skills.filter((s) => s.category === "business");

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-brand dark:text-brand-accent">
          ⚖️ Agent Afaceri &amp; Juridic AI
        </h1>
        <p className="mt-1 text-slate-600 dark:text-slate-400">
          Contracte, înființare firmă, fiscalitate, GDPR, protecția consumatorului
          și planuri de afaceri. Context România, în limba română.
        </p>
      </header>

      {error && (
        <div className="mb-4 rounded-lg bg-red-100 px-4 py-2 text-red-800 dark:bg-red-950 dark:text-red-200">
          {error}
        </div>
      )}

      <div className="grid gap-8 md:grid-cols-2">
        <section>
          <h2 className="mb-3 text-lg font-semibold">Skill-uri</h2>
          <SkillGroup label="Juridic ⚖️" list={legal} onPick={selectSkill} active={active} />
          <SkillGroup label="Business 📈" list={biz} onPick={selectSkill} active={active} />
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold">
            {active ? active.title : "Alege un skill"}
          </h2>

          {active && (
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <p className="mb-3 text-sm text-slate-600 dark:text-slate-400">
                {active.description}
              </p>
              {active.inputs.map((f) => (
                <div key={f} className="mb-3">
                  <label className="mb-1 block text-sm font-medium">
                    {INPUT_LABELS[f] || f}
                  </label>
                  {LONG_FIELDS.has(f) ? (
                    <textarea
                      className="w-full rounded-lg border border-slate-300 bg-transparent p-2 text-sm dark:border-slate-700"
                      rows={4}
                      value={inputs[f] || ""}
                      onChange={(e) => setInputs({ ...inputs, [f]: e.target.value })}
                    />
                  ) : (
                    <input
                      className="w-full rounded-lg border border-slate-300 bg-transparent p-2 text-sm dark:border-slate-700"
                      value={inputs[f] || ""}
                      onChange={(e) => setInputs({ ...inputs, [f]: e.target.value })}
                    />
                  )}
                </div>
              ))}
              <button
                onClick={onRun}
                disabled={loading}
                className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-light disabled:opacity-50"
              >
                {loading ? "Se generează…" : "Rulează"}
              </button>

              {result && (
                <>
                  <pre className="mt-4 whitespace-pre-wrap rounded-lg bg-slate-100 p-3 text-sm dark:bg-slate-800">
                    {result}
                  </pre>
                  <ResultActions
                    title={active.title}
                    content={result}
                    category={active.category}
                  />
                </>
              )}
            </div>
          )}
        </section>
      </div>

      <section className="mt-10">
        <div className="mb-3 flex items-center gap-3">
          <h2 className="text-lg font-semibold">Chat cu agentul</h2>
          <select
            value={domain}
            onChange={(e) => setDomain(e.target.value as any)}
            className="rounded-lg border border-slate-300 bg-transparent px-2 py-1 text-sm dark:border-slate-700"
          >
            <option value="business">Business</option>
            <option value="juridic">Juridic</option>
          </select>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <div className="mb-3 max-h-96 space-y-3 overflow-y-auto">
            {history.length === 0 && (
              <p className="text-sm text-slate-500">
                Întreabă orice despre afaceri sau juridic…
              </p>
            )}
            {history.map((m, i) => (
              <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
                <span
                  className={
                    "inline-block max-w-[85%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm " +
                    (m.role === "user"
                      ? "bg-brand text-white"
                      : "bg-slate-100 dark:bg-slate-800")
                  }
                >
                  {m.content}
                </span>
                {m.role === "assistant" && (
                  <ResultActions
                    title={`Chat ${domain}`}
                    content={m.content}
                    category={domain}
                    compact
                  />
                )}
              </div>
            ))}
            {chatLoading && <p className="text-sm text-slate-500">Agentul scrie…</p>}
          </div>
          <div className="flex gap-2">
            <input
              className="flex-1 rounded-lg border border-slate-300 bg-transparent p-2 text-sm dark:border-slate-700"
              placeholder="Scrie o întrebare…"
              value={msg}
              onChange={(e) => setMsg(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && onSend()}
            />
            <button
              onClick={onSend}
              disabled={chatLoading}
              className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-light disabled:opacity-50"
            >
              Trimite
            </button>
          </div>
        </div>
      </section>

      <footer className="mt-10 border-t border-slate-200 pt-4 text-xs text-slate-500 dark:border-slate-800">
        ⚖️ Informațiile sunt orientative și nu constituie consultanță juridică,
        fiscală sau contabilă profesională. Consultă un avocat / contabil pentru
        decizii concrete.
      </footer>
    </main>
  );
}

function ResultActions({
  title,
  content,
  category,
  compact,
}: {
  title: string;
  content: string;
  category: string;
  compact?: boolean;
}) {
  const { user } = useAuth();
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");

  if (!user) {
    return (
      <p className={"text-xs text-slate-500 " + (compact ? "mt-1" : "mt-3")}>
        <Link href="/login" className="text-brand hover:underline dark:text-brand-accent">
          Autentifică-te
        </Link>{" "}
        ca să salvezi sau să exporți (PDF/Word).
      </p>
    );
  }

  async function doExport(format: "pdf" | "docx") {
    setBusy(format);
    setErr("");
    try {
      await exportInline(title, content, format);
    } catch (e: any) {
      setErr(e.message || String(e));
    } finally {
      setBusy("");
    }
  }

  async function doSave() {
    setBusy("save");
    setErr("");
    try {
      await saveDocument(title, content, category);
      setSaved(true);
    } catch (e: any) {
      setErr(e.message || String(e));
    } finally {
      setBusy("");
    }
  }

  return (
    <div className={"flex flex-wrap items-center gap-2 " + (compact ? "mt-1" : "mt-3")}>
      <button
        onClick={doSave}
        disabled={busy !== "" || saved}
        className="rounded-lg border border-slate-300 px-3 py-1 text-xs hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800"
      >
        {saved ? "✓ Salvat" : busy === "save" ? "Se salvează…" : "Salvează"}
      </button>
      <button
        onClick={() => doExport("pdf")}
        disabled={busy !== ""}
        className="rounded-lg border border-slate-300 px-3 py-1 text-xs hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800"
      >
        {busy === "pdf" ? "…" : "PDF"}
      </button>
      <button
        onClick={() => doExport("docx")}
        disabled={busy !== ""}
        className="rounded-lg border border-slate-300 px-3 py-1 text-xs hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800"
      >
        {busy === "docx" ? "…" : "Word"}
      </button>
      {err && <span className="text-xs text-red-600">{err}</span>}
    </div>
  );
}

function SkillGroup({
  label,
  list,
  onPick,
  active,
}: {
  label: string;
  list: Skill[];
  onPick: (s: Skill) => void;
  active: Skill | null;
}) {
  return (
    <div className="mb-4">
      <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </h3>
      <div className="space-y-2">
        {list.map((s) => (
          <button
            key={s.name}
            onClick={() => onPick(s)}
            className={
              "block w-full rounded-lg border p-3 text-left transition " +
              (active?.name === s.name
                ? "border-brand bg-brand/5"
                : "border-slate-200 hover:border-brand dark:border-slate-800")
            }
          >
            <div className="font-medium">{s.title}</div>
            <div className="text-xs text-slate-500">{s.description}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
