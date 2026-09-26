"use client";

import { useRef, useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { Button, Card, EmptyState, Spinner } from "@/components/ui";

export type RecordField = {
  key: string; label: string; type?: "text" | "date" | "textarea" | "select" | "checkbox";
  required?: boolean; maxLength?: number; options?: [string, string][]; initial?: string | boolean;
};
type Row = {id: number} & Record<string, unknown>;
export type CollectionSpec = {title: string; endpoint: string; titleKey: string; fields: RecordField[]; update?: "patch" | "put"};

export function RecordCollection({spec, onEditing}: {spec: CollectionSpec; onEditing: (value: boolean) => void}) {
  const records = useFetch<Row[]>(spec.endpoint);
  const [editing, setEditing] = useState<number | "new" | null>(null);
  const [values, setValues] = useState<Record<string, string | boolean>>({});
  const [deleting, setDeleting] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const firstInput = useRef<HTMLInputElement>(null);
  const errorBox = useRef<HTMLParagraphElement>(null);

  function edit(row?: Row) {
    setValues(Object.fromEntries(spec.fields.map(f => [f.key, (row?.[f.key] ?? f.initial ?? (f.type === "checkbox" ? false : "")) as string | boolean])));
    setEditing(row?.id ?? "new"); onEditing(true); setError(null); setNotice(null); setDeleting(null);
    requestAnimationFrame(() => firstInput.current?.focus());
  }
  function cancel() {setEditing(null); onEditing(false); setError(null);}
  function report(e: unknown) {
    setError(e instanceof Error ? e.message : "Operațiunea nu a putut fi finalizată.");
    requestAnimationFrame(() => errorBox.current?.focus());
  }
  async function save(e: React.FormEvent) {
    e.preventDefault(); setError(null);
    const missing = spec.fields.find(f => f.required && !String(values[f.key] ?? "").trim());
    if (missing) {report(new Error(`Completează câmpul „${missing.label}”.`)); return;}
    setBusy(true);
    const payload = Object.fromEntries(spec.fields.map(f => {
      const v = values[f.key];
      return [f.key, typeof v === "string" ? v.trim() || null : v];
    }));
    try {
      if (editing === "new") await api.post(spec.endpoint, payload);
      else if (spec.update === "patch") await api.patch(`${spec.endpoint}/${editing}`, payload);
      else await api.put(`${spec.endpoint}/${editing}`, payload);
      cancel(); setNotice("Înregistrarea a fost salvată."); records.reload();
    } catch(e) {report(e);} finally {setBusy(false);}
  }
  async function remove(id: number) {
    setBusy(true); setError(null);
    try {
      await api.del(`${spec.endpoint}/${id}`); setDeleting(null);
      setNotice("Înregistrarea a fost ștearsă."); records.reload();
    } catch(e) {report(e);} finally {setBusy(false);}
  }

  return <section className="space-y-4" aria-label={spec.title}>
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h2 className="text-lg font-semibold">{spec.title}</h2>
      {editing === null && <Button className="min-h-12" onClick={() => edit()} disabled={busy}>
        <Plus size={16} aria-hidden="true" /> Adaugă înregistrare
      </Button>}
    </div>
    {notice && <p role="status" className="text-sm text-fg">{notice}</p>}
    {error && <p ref={errorBox} tabIndex={-1} role="alert" className="text-sm text-red-600">{error}</p>}
    {editing !== null && <Card>
      <h3 className="mb-4 font-semibold">{editing === "new" ? "Înregistrare nouă" : "Editează înregistrarea"}</h3>
      <form onSubmit={save} className="grid gap-4 sm:grid-cols-2">
        {spec.fields.map(f => <label key={f.key} className={`text-sm ${f.type === "textarea" || f.type === "checkbox" ? "sm:col-span-2" : ""}`}>
          {f.type === "checkbox" ? <span className="flex min-h-12 items-center gap-3">
            <input type="checkbox" checked={Boolean(values[f.key])} disabled={busy} onChange={e => setValues(v => ({...v,[f.key]:e.target.checked}))} className="h-5 w-5 accent-brand-blue" />
            {f.label}
          </span> : <>
            <span className="mb-1 block">{f.label}{f.required ? " *" : ""}</span>
            {f.type === "select" ? <select value={String(values[f.key] ?? "")} disabled={busy} required={f.required}
              onChange={e => setValues(v => ({...v,[f.key]:e.target.value}))}
              className="min-h-12 w-full rounded-xl border border-border bg-surface px-3 text-fg">
              {f.options?.map(([value,label]) => <option key={value} value={value}>{label}</option>)}
            </select> : f.type === "textarea" ? <textarea rows={3} value={String(values[f.key] ?? "")} disabled={busy} maxLength={f.maxLength}
              onChange={e => setValues(v => ({...v,[f.key]:e.target.value}))}
              className="w-full rounded-xl border border-border bg-surface p-3 text-fg" /> :
              <input ref={f.key === spec.titleKey ? firstInput : undefined} type={f.type || "text"}
                value={String(values[f.key] ?? "")} disabled={busy} required={f.required} maxLength={f.maxLength}
                onChange={e => setValues(v => ({...v,[f.key]:e.target.value}))}
                className="min-h-12 w-full rounded-xl border border-border bg-surface px-3 text-fg" />}
          </>}
        </label>)}
        <div className="flex flex-wrap gap-3 sm:col-span-2">
          <Button type="submit" className="min-h-12" disabled={busy}>{busy ? "Se salvează…" : "Salvează înregistrarea"}</Button>
          <Button type="button" variant="outline" className="min-h-12" onClick={cancel} disabled={busy}>Anulează editarea</Button>
        </div>
      </form>
    </Card>}
    {records.loading ? <Spinner /> : records.error ? <Card>
      <p role="alert">{records.error}</p><Button variant="outline" onClick={records.reload}>Reîncearcă încărcarea</Button>
    </Card> : records.data?.length ? records.data.map(row => <Card key={row.id} className="space-y-3">
      <h3 className="break-words font-semibold">{String(row[spec.titleKey])}</h3>
      <p className="text-xs text-muted">Informație adăugată de tine</p>
      <dl className="grid gap-2 text-sm sm:grid-cols-2">
        {spec.fields.filter(f => f.key !== spec.titleKey && row[f.key] !== null && row[f.key] !== "" && row[f.key] !== false).map(f =>
          <div key={f.key} className={f.type === "textarea" ? "sm:col-span-2" : ""}>
            <dt className="text-muted">{f.label}</dt>
            <dd className="break-words whitespace-pre-wrap">{f.type === "checkbox" ? "Da" : f.options?.find(([value]) => value === row[f.key])?.[1] ?? String(row[f.key])}</dd>
          </div>)}
      </dl>
      <div className="flex flex-wrap gap-3">
        <Button variant="outline" className="min-h-12" onClick={() => edit(row)} disabled={busy || editing !== null}><Pencil size={16} aria-hidden="true" /> Editează</Button>
        <Button variant="outline" className="min-h-12" onClick={() => {setDeleting(row.id); setError(null);}} disabled={busy || editing !== null}><Trash2 size={16} aria-hidden="true" /> Șterge</Button>
      </div>
      {deleting === row.id && <div className="space-y-3 rounded-xl border border-red-500/40 p-3">
        <p>Ștergi definitiv „{String(row[spec.titleKey])}” din dosar?</p>
        <div className="flex flex-wrap gap-3">
          <Button variant="danger" className="min-h-12" onClick={() => remove(row.id)} disabled={busy}>Confirmă ștergerea</Button>
          <Button variant="outline" className="min-h-12" onClick={() => setDeleting(null)} disabled={busy}>Păstrează înregistrarea</Button>
        </div>
      </div>}
    </Card>) : editing === null && <EmptyState title="Nicio înregistrare încă" hint="Adaugă informațiile din documentele tale. Acestea pot fi corectate ulterior." />}
  </section>;
}
