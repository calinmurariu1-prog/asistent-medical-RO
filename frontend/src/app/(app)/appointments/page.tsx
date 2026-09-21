"use client";

import { useState } from "react";
import { CalendarDays } from "lucide-react";
import { useFetch } from "@/lib/hooks";
import { api } from "@/lib/api";
import type { Appointment } from "@/lib/types";
import { Badge, Button, Card, EmptyState, Input, PageHeader, Spinner } from "@/components/ui";

const labels: Record<string,string> = {scheduled:"Programată", completed:"Efectuată", cancelled:"Anulată", no_show:"Neprezentare"};
function localTime(value: string) {
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0,16);
}

export default function AppointmentsPage() {
  const { data, loading, reload, error: loadError } = useFetch<Appointment[]>("/appointments");
  const [editing, setEditing] = useState<Appointment | null>(null);
  const [title, setTitle] = useState("");
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [location, setLocation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [deleting, setDeleting] = useState<Appointment | null>(null);

  function clear() { setEditing(null); setTitle(""); setStartsAt(""); setEndsAt(""); setLocation(""); }
  async function action(work: () => Promise<unknown>, success: string) {
    setBusy(true); setError(""); setMessage("");
    try { await work(); setMessage(success); reload(); }
    catch(e) { setError(e instanceof Error ? e.message : "Operația nu a reușit."); }
    finally { setBusy(false); }
  }
  async function save(e: React.FormEvent) {
    e.preventDefault();
    await action(async () => {
      const payload = {title: title.trim(), starts_at: new Date(startsAt).toISOString(), ends_at: endsAt ? new Date(endsAt).toISOString() : null, location: location.trim() || null};
      if (editing) await api.patch(`/appointments/${editing.id}`, payload);
      else await api.post("/appointments", payload);
      clear();
    }, "Programarea și memento-ul au fost salvate.");
  }

  return <div className="space-y-6">
    <PageHeader title="Programări" subtitle="Consultații, investigații și memento-uri." icon={CalendarDays} />
    {(error || loadError) && <p role="alert" className="rounded-xl border border-red-500/30 p-3">{error || loadError}</p>}
    {message && <p role="status" className="text-sm text-muted">{message}</p>}
    <Card>
      <form onSubmit={save} className="space-y-4">
        <h2 className="font-semibold">{editing ? "Reprogramează consultația" : "Adaugă o programare"}</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="text-sm">Titlul programării<Input required maxLength={300} value={title} disabled={busy} onChange={e=>setTitle(e.target.value)} /></label>
          <label className="text-sm">Data și ora locală<Input required type="datetime-local" value={startsAt} disabled={busy} onChange={e=>setStartsAt(e.target.value)} /></label>
          <label className="text-sm">Sfârșit (opțional)<Input type="datetime-local" value={endsAt} disabled={busy} onChange={e=>setEndsAt(e.target.value)} /></label>
          <label className="text-sm sm:col-span-2">Locație<Input maxLength={300} value={location} disabled={busy} onChange={e=>setLocation(e.target.value)} /></label>
        </div>
        <p className="text-sm text-muted">Pentru programările viitoare, memento-ul este pregătit cu 24 de ore înainte sau imediat dacă sunt mai apropiate. Livrarea pe telefon necesită serviciul push configurat; modul simulat nu trimite mesaje.</p>
        <div className="flex flex-wrap gap-3">
          <Button type="submit" disabled={busy || !!deleting}>Salvează programarea</Button>
          {editing && <Button type="button" variant="outline" disabled={busy} onClick={clear}>Renunță la modificare</Button>}
        </div>
      </form>
    </Card>
    {deleting && <Card>
      <p>Ștergi programarea „{deleting.title}” și memento-ul ei?</p>
      <div className="mt-3 flex flex-wrap gap-3">
        <Button variant="danger" disabled={busy} onClick={()=>action(async()=>{await api.del(`/appointments/${deleting.id}`); setDeleting(null);},"Programarea a fost ștearsă.")}>Confirmă ștergerea</Button>
        <Button variant="outline" disabled={busy} onClick={()=>setDeleting(null)}>Păstrează programarea</Button>
      </div>
    </Card>}
    <Button variant="outline" disabled={busy} onClick={()=>action(()=>api.post("/notifications/reminders/appointments"),"Memento-urile lipsă au fost pregătite.")}>Pregătește memento-urile programărilor vechi</Button>
    {loading ? <Spinner /> : !(data || []).length ? <EmptyState icon={CalendarDays} title="Nicio programare" hint="Adaugă o consultație sau o investigație." /> :
      <div className="space-y-3">{(data || []).map(a=><Card key={a.id}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0 break-words"><h2 className="font-semibold">{a.title}</h2>
            <p className="text-sm text-muted">{new Date(a.starts_at).toLocaleString("ro-RO")}</p>
            {a.location && <p className="text-sm text-muted">{a.location}</p>}
          </div>
          <Badge tone={a.status === "scheduled" ? "blue" : "neutral"}>{labels[a.status] || a.status}</Badge>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button variant="outline" disabled={busy || !!editing || !!deleting} onClick={()=>{setEditing(a);setTitle(a.title);setStartsAt(localTime(a.starts_at));setEndsAt(a.ends_at ? localTime(a.ends_at) : "");setLocation(a.location || "");}}>Reprogramează</Button>
          {a.status === "scheduled" ? <>
            <Button variant="outline" disabled={busy || !!editing || !!deleting} onClick={()=>action(()=>api.patch(`/appointments/${a.id}`,{status:"completed"}),"Programarea este marcată ca efectuată.")}>Marchează efectuată</Button>
            <Button variant="outline" disabled={busy || !!editing || !!deleting} onClick={()=>action(()=>api.patch(`/appointments/${a.id}`,{status:"cancelled"}),"Programarea și memento-ul au fost anulate.")}>Anulează programarea</Button>
          </> : <Button variant="outline" disabled={busy || !!editing || !!deleting} onClick={()=>action(()=>api.patch(`/appointments/${a.id}`,{status:"scheduled"}),"Programarea a fost reactivată.")}>Reactivează programarea</Button>}
          <Button variant="outline" disabled={busy || !!editing || !!deleting} onClick={()=>setDeleting(a)}>Șterge</Button>
        </div>
      </Card>)}</div>}
  </div>;
}
