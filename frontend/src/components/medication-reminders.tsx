"use client";

import {FormEvent, useCallback, useEffect, useState} from "react";
import {api} from "@/lib/api";
import type {Medication} from "@/lib/types";
import {Button, Input} from "@/components/ui";

type Reminder = {id:number; medication_id:number; local_time:string; timezone:string;
  is_enabled:boolean; next_occurrence:string|null};

export function MedicationReminders({medication:med}:{medication:Medication}) {
  const [open,setOpen] = useState(false);
  const [items,setItems] = useState<Reminder[]>([]);
  const [editing,setEditing] = useState<Reminder|null>(null);
  const [deleting,setDeleting] = useState<number|null>(null);
  const [clock,setClock] = useState("");
  const [zone,setZone] = useState("Europe/Bucharest");
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const [message,setMessage] = useState("");
  const base = `/medications/${med.id}/reminders`;
  const load = useCallback(()=>api.get<Reminder[]>(base),[base]);
  useEffect(()=>{setZone(Intl.DateTimeFormat().resolvedOptions().timeZone || "Europe/Bucharest");},[]);
  useEffect(()=>{
    if(!open) return;
    let cancelled=false;
    load().then(rows=>{if(!cancelled)setItems(rows);}).catch(e=>{
      if(!cancelled)setError(e instanceof Error ? e.message : "Memento-urile nu sunt disponibile.");
    });
    return ()=>{cancelled=true;};
  },[open,load,med.is_active,med.start_date,med.end_date,med.name]);
  async function run(work:()=>Promise<unknown>, success:string) {
    setBusy(true);setError("");setMessage("");
    try {await work();setItems(await load());setMessage(success);return true;}
    catch(e){setError(e instanceof Error ? e.message : "Operația nu a reușit.");return false;}
    finally{setBusy(false);}
  }
  async function save(event:FormEvent) {
    event.preventDefault();
    const payload={local_time:clock,timezone:zone,is_enabled:editing?.is_enabled ?? true};
    if(await run(()=>editing ? api.put(`${base}/${editing.id}`,payload) : api.post(base,payload),
      "Ora memento-ului a fost salvată.")){setEditing(null);setClock("");}
  }
  return <section className="mt-3" aria-label={`Memento-uri pentru ${med.name}`}>
    <Button type="button" variant="outline" aria-expanded={open} onClick={()=>setOpen(!open)}>Memento-uri</Button>
    {open && <div className="mt-3 space-y-3 rounded-xl border border-border p-3">
      <p className="text-sm text-muted">Alege orele zilnice din programul stabilit cu medicul. Memento-ul nu confirmă administrarea și nu modifică prescripția.</p>
      {!med.is_active && <p className="text-sm">Tratamentul este în istoric. Memento-urile sunt suspendate.</p>}
      {error && <p role="alert" className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      {message && <p role="status" className="text-sm">{message}</p>}
      {items.map(r=><div key={r.id} className="space-y-2 border-b border-border pb-3 text-sm">
        <p className="break-words font-medium">Zilnic la {r.local_time} · {r.timezone} · {r.is_enabled ? "Activat" : "În pauză"}</p>
        <p className="text-muted">{r.next_occurrence ? `Următorul, în ora dispozitivului: ${new Date(r.next_occurrence).toLocaleString("ro-RO")}` : "Nicio apariție programată: verifică pauza, starea și perioada tratamentului."}</p>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" disabled={busy || editing!==null} onClick={()=>{setEditing(r);setClock(r.local_time);setZone(r.timezone);}}>Schimbă ora</Button>
          <Button type="button" variant="outline" disabled={busy || editing!==null} onClick={()=>run(()=>api.put(`${base}/${r.id}`,{local_time:r.local_time,timezone:r.timezone,is_enabled:!r.is_enabled}),"Starea memento-ului a fost actualizată.")}>{r.is_enabled ? "Pauză memento" : "Activează memento"}</Button>
          <Button type="button" variant="outline" disabled={busy || editing!==null} onClick={()=>setDeleting(r.id)}>Șterge memento</Button>
        </div>
        {deleting===r.id && <div className="flex flex-wrap items-center gap-2">
          <p>Ștergi acest memento și notificările sale?</p>
          <Button type="button" disabled={busy} onClick={async()=>{if(await run(()=>api.del(`${base}/${r.id}`),"Memento șters.")){setDeleting(null);setEditing(null);setClock("");}}}>Confirmă ștergerea memento-ului</Button>
          <Button type="button" variant="outline" disabled={busy} onClick={()=>setDeleting(null)}>Păstrează memento-ul</Button>
        </div>}
      </div>)}
      <form onSubmit={save} className="space-y-3">
        <label className="block text-sm" htmlFor={`reminder-time-${med.id}`}>Ora zilnică</label>
        <Input id={`reminder-time-${med.id}`} type="time" className="dark:[color-scheme:dark]" value={clock} required disabled={busy} onChange={e=>setClock(e.target.value)}/>
        <label className="block text-sm" htmlFor={`reminder-zone-${med.id}`}>Fus orar (ex. Europe/Bucharest)</label>
        <Input id={`reminder-zone-${med.id}`} value={zone} maxLength={64} required disabled={busy} onChange={e=>setZone(e.target.value)}/>
        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={busy || !clock || !zone}>{editing ? "Salvează ora" : "Adaugă ora de memento"}</Button>
          {editing && <Button type="button" variant="outline" disabled={busy} onClick={()=>{setEditing(null);setClock("");}}>Anulează schimbarea orei</Button>}
        </div>
      </form>
      <p className="text-xs text-muted">Maximum 12 ore pe tratament. Fusul ales rămâne fix când călătorești. La ora de vară, o oră inexistentă este omisă; o oră repetată produce un singur memento. Notificările sunt orientative și pot întârzia. Aplicația nu recomandă recuperarea dozelor omise.</p>
    </div>}
  </section>;
}
