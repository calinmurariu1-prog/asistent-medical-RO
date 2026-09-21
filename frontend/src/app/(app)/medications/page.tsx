"use client";

import { type FormEvent, useState } from "react";
import { AlertTriangle, Pill, Sparkles } from "lucide-react";
import { useFetch } from "@/lib/hooks";
import { api } from "@/lib/api";
import { MedicationReminders } from "@/components/medication-reminders";
import type { Medication } from "@/lib/types";
import { Badge, Button, Card, EmptyState, Input, PageHeader, Spinner } from "@/components/ui";

interface MedicationExplanation {
  result: string;
  sources: {ref: string; title: string; url: string}[];
}

interface CheckResult {
  interactions: { drug_a: string; drug_b: string; severity: string; description: string; source_title: string; source_url: string; source_checked_on: string }[];
  duplicates: { substance: string; medications: string[] }[];
  disclaimer: string;
  unassessed_pairs: number;
  unidentified_medications: string[];
}

export default function MedicationsPage() {
  const { data, loading, reload, error: loadError } = useFetch<Medication[]>("/medications");
  const [editing, setEditing] = useState<Medication | "new" | null>(null);
  const [deleting, setDeleting] = useState<Medication | null>(null);
  const [filter, setFilter] = useState<"active" | "history">("active");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [check, setCheck] = useState<CheckResult | null>(null);
  const [explains, setExplains] = useState<Record<number, MedicationExplanation>>({});
  async function action(work: () => Promise<unknown>, success: string) {
    setBusy(true); setError(""); setMessage("");
    try { await work(); setCheck(null);setExplains({});setMessage(success);reload(); }
    catch(e) {setError(e instanceof Error ? e.message : "Operația nu a reușit.");}
    finally {setBusy(false);}
  }
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const text = (key: string) => String(form.get(key) || "").trim() || null;
    const payload = {name:text("name"), active_substance:text("active_substance"), dose:text("dose"),
      frequency:text("frequency"), interval:text("interval"), start_date:text("start_date"),
      end_date:text("end_date"), notes:text("notes")};
    setMessage("");
    if (!payload.name) {setError("Introdu denumirea tratamentului.");return;}
    if (payload.start_date && payload.end_date && payload.end_date < payload.start_date) {
      setError("Data de sfârșit nu poate preceda data de început.");return;
    }
    await action(async()=>{
      if (editing === "new") {await api.post("/medications",payload);setFilter("active");}
      else if (editing) await api.patch(`/medications/${editing.id}`,payload);
      setEditing(null);
    },"Înregistrarea tratamentului a fost salvată.");
  }
  async function runCheck() {
    setBusy(true);setError("");
    try {setCheck(await api.get<CheckResult>("/medications/check"));}
    catch(e) {setError(e instanceof Error ? e.message : "Verificarea nu este disponibilă.");}
    finally {setBusy(false);}
  }
  async function explain(med: Medication) {
    setBusy(true);setError("");
    try {
      const result = await api.post<MedicationExplanation>("/ai/skills/explain_medication",{inputs:{name:med.active_substance || med.name}});
      setExplains(previous=>({...previous,[med.id]:result}));
    } catch(e) {setError(e instanceof Error ? e.message : "Explicația nu este disponibilă.");}
    finally {setBusy(false);}
  }
  const meds = (data || []).filter(m=>filter === "active" ? m.is_active : !m.is_active);
  const locked = busy || !!editing || !!deleting;
  return <div className="space-y-5">
    <PageHeader title="Medicamente" subtitle="Evidența tratamentelor și istoricul lor." icon={Pill}
      action={<Button disabled={locked} onClick={()=>{setError("");setEditing("new");}}>Adaugă tratament</Button>} />
    <p className="text-sm text-muted">Transcrie schema primită de la medic. Aplicația păstrează evidența; nu stabilește doze sau tratamente.</p>
    {(error || loadError) && <p role="alert" className="rounded-xl border border-red-500/30 p-3">{error || loadError}</p>}
    {message && <p role="status" className="text-sm text-muted">{message}</p>}
    {editing && <Card><form onSubmit={save} className="space-y-4" key={editing === "new" ? "new" : editing.id}>
      <h2 className="font-semibold">{editing === "new" ? "Înregistrare tratament" : "Corectează înregistrarea"}</h2>
      <div className="grid gap-4 sm:grid-cols-2">
        {([
          ["name","Denumire","text",200], ["active_substance","Substanță activă","text",200],
          ["dose","Doza din prescripție","text",100], ["frequency","Frecvența din prescripție","text",100],
          ["interval","Instrucțiuni de administrare","text",100], ["start_date","Data de început","date",0],
          ["end_date","Data de sfârșit","date",0],
        ] as const).map(([key,label,type,max])=><label className="text-sm" key={key}>{label}
          <Input name={key} type={type} required={key === "name"} maxLength={max || undefined}
            defaultValue={editing === "new" ? "" : editing[key] || ""} disabled={busy} />
        </label>)}
        <label className="text-sm sm:col-span-2">Note
          <textarea name="notes" maxLength={4000} rows={3} disabled={busy} defaultValue={editing === "new" ? "" : editing.notes || ""}
            className="mt-1 w-full rounded-xl border border-border bg-surface p-3 text-fg" />
        </label>
      </div>
      <div className="flex flex-wrap gap-3"><Button type="submit" disabled={busy}>Salvează tratamentul</Button>
        <Button type="button" variant="outline" disabled={busy} onClick={()=>setEditing(null)}>Renunță</Button></div>
    </form></Card>}
    {deleting && <Card><p>Ștergi definitiv înregistrarea „{deleting.name}”? Pentru a o păstra, folosește mutarea în istoric.</p>
      <div className="mt-3 flex flex-wrap gap-3">
        <Button variant="danger" disabled={busy} onClick={()=>action(async()=>{await api.del(`/medications/${deleting.id}`);setDeleting(null);},"Înregistrarea a fost ștearsă.")}>Confirmă ștergerea</Button>
        <Button variant="outline" disabled={busy} onClick={()=>setDeleting(null)}>Păstrează înregistrarea</Button>
      </div></Card>}
    <div className="flex flex-wrap gap-3">
      <Button variant={filter === "active" ? "primary" : "outline"} aria-pressed={filter === "active"} onClick={()=>setFilter("active")}>Active</Button>
      <Button variant={filter === "history" ? "primary" : "outline"} aria-pressed={filter === "history"} onClick={()=>setFilter("history")}>Istoric</Button>
      <Button variant="outline" disabled={locked} onClick={runCheck}>Verifică lista activă</Button>
    </div>
    {check && <Card className="border-amber-500/30">
      <h2 className="flex items-center gap-2 font-semibold"><AlertTriangle size={18} />Verificare limitată</h2>
      {!check.interactions.length && !check.duplicates.length && <p className="mt-2 text-sm">Lista locală nu a identificat potriviri. Acest rezultat nu confirmă siguranța combinației.</p>}
      <ul className="mt-2 space-y-2 text-sm">
        {check.interactions.map((item,i)=><li key={`interaction-${i}`}>{item.drug_a} + {item.drug_b}: {item.description} <a className="underline text-primary" href={item.source_url} target="_blank" rel="noopener noreferrer">{item.source_title}</a> <span className="text-muted">(sursă consultată: {item.source_checked_on})</span></li>)}
        {check.duplicates.map((item,i)=><li key={`duplicate-${i}`}>Aceeași substanță declarată: {item.substance} — {item.medications.join(", ")}</li>)}
      </ul>
        <p className="mt-3 text-sm">Perechi fără regulă documentată în catalog: {check.unassessed_pairs}. Nu au fost evaluate.</p>
        {!!check.unidentified_medications.length && <p className="mt-2 text-sm break-words">Substanță nespecificată sau nerecunoscută în catalog: {check.unidentified_medications.join(", ")}. Denumirile comerciale nu sunt interpretate automat.</p>}
        <p className="mt-3 text-sm text-muted">{check.disclaimer}</p>
    </Card>}
    {loading ? <Spinner /> : !meds.length ? <EmptyState icon={Pill} title={filter === "active" ? "Niciun tratament activ înregistrat" : "Niciun tratament în istoric"} /> :
      <div className="space-y-3">{meds.map(m=><Card key={m.id}>
        <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="break-words font-semibold">{m.name}</h2><Badge>{m.is_active ? "În lista activă" : "În istoric"}</Badge></div>
        <div className="mt-2 space-y-1 break-words text-sm text-muted">
          {m.active_substance && <p>Substanță: {m.active_substance}</p>}{m.dose && <p>Doză înregistrată: {m.dose}</p>}
          {m.frequency && <p>Frecvență: {m.frequency}</p>}{m.interval && <p>Administrare: {m.interval}</p>}
          {(m.start_date || m.end_date) && <p>Perioadă: {m.start_date || "început nespecificat"} — {m.end_date || "sfârșit nespecificat"}</p>}
          {m.notes && <p className="whitespace-pre-wrap">{m.notes}</p>}
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button variant="outline" disabled={locked} onClick={()=>{setError("");setEditing(m);}}>Corectează</Button>
          <Button variant="outline" disabled={locked} onClick={()=>action(()=>api.patch(`/medications/${m.id}`,{is_active:!m.is_active}),"Starea înregistrării a fost actualizată.")}>{m.is_active ? "Mută în istoric" : "Mută în lista activă"}</Button>
          <Button variant="outline" disabled={locked} onClick={()=>explain(m)}><Sparkles size={16} />Explică</Button>
          <Button variant="outline" disabled={locked} onClick={()=>setDeleting(m)}>Șterge</Button>
        </div>
        <MedicationReminders medication={m} />
        {explains[m.id] && <div className="mt-3 whitespace-pre-wrap break-words rounded-xl bg-surface-2 p-3 text-sm"><p>{explains[m.id].result}</p>{explains[m.id].sources.map(source => <a key={source.ref} className="mt-2 block text-primary underline" href={source.url} target="_blank" rel="noopener noreferrer">Consultă sursa: {source.title}</a>)}</div>}
      </Card>)}</div>}
  </div>;
}
