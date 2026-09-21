"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Bell } from "lucide-react";
import { useFetch } from "@/lib/hooks";
import { api } from "@/lib/api";
import type { MedicalNotification } from "@/lib/types";
import { Badge, Button, Card, EmptyState, PageHeader, Spinner } from "@/components/ui";

function dateLabel(value: string) { return new Date(value).toLocaleString("ro-RO"); }

export default function NotificationsPage() {
  const {data, loading, error: loadError, reload} = useFetch<MedicalNotification[]>("/notifications");
  const [filter, setFilter] = useState<"unread" | "future" | "all">("unread");
  const [now, setNow] = useState(Date.now());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [deleting, setDeleting] = useState<MedicalNotification | null>(null);
  useEffect(() => {
    const refresh = () => { if (!document.hidden) {setNow(Date.now()); reload();} };
    const timer = setInterval(refresh, 30000);
    window.addEventListener("focus", refresh);
    return () => {clearInterval(timer); window.removeEventListener("focus", refresh);};
  }, [reload]);
  const future = (n: MedicalNotification) => !!n.scheduled_for && new Date(n.scheduled_for).getTime() > now;
  const unread = (data || []).filter(n => n.status !== "read" && !future(n));
  const upcoming = (data || []).filter(n => future(n) && n.status !== "read");
  const entries = filter === "unread" ? unread : filter === "future" ? upcoming : data || [];
  async function action(work: () => Promise<unknown>, success: string) {
    setBusy(true); setError(""); setMessage("");
    try { await work(); setMessage(success); setNow(Date.now()); reload(); }
    catch (e) {setError(e instanceof Error ? e.message : "Operația nu a reușit.");}
    finally {setBusy(false);}
  }

  return <div className="space-y-5">
    <PageHeader title="Notificări" subtitle="Memento-urile tale și mesajele din aplicație." icon={Bell}
      action={<Button variant="outline" disabled={loading || busy} onClick={()=>{setNow(Date.now());reload();}}>Actualizează</Button>} />
    <p className="text-sm text-muted">Mesajele sunt disponibile aici chiar și fără notificări push. Starea de trimitere nu confirmă afișarea pe telefon. În modul simulat nu se expediază mesaje reale.</p>
    {(error || loadError) && <p role="alert" className="rounded-xl border border-red-500/30 p-3">{error || loadError}</p>}
    {message && <p role="status" className="text-sm text-muted">{message}</p>}
    <div className="flex flex-wrap gap-2" aria-label="Filtre notificări">
      <Button variant={filter === "unread" ? "primary" : "outline"} aria-pressed={filter === "unread"} onClick={()=>setFilter("unread")}>Necitite ({unread.length})</Button>
      <Button variant={filter === "future" ? "primary" : "outline"} aria-pressed={filter === "future"} onClick={()=>setFilter("future")}>Viitoare ({upcoming.length})</Button>
      <Button variant={filter === "all" ? "primary" : "outline"} aria-pressed={filter === "all"} onClick={()=>setFilter("all")}>Toate ({data?.length || 0})</Button>
    </div>
    <Button variant="outline" disabled={busy || !unread.length} onClick={()=>action(()=>api.post("/notifications/read-all"),"Notificările curente au fost marcate citite. Memento-urile viitoare sunt păstrate.")}>Marchează toate notificările curente citite</Button>
    {deleting && <Card>
      <p>Ștergi notificarea „{deleting.title}”? Încercările viitoare de trimitere se opresc. Un mesaj deja trimis nu poate fi retras.</p>
      <div className="mt-3 flex flex-wrap gap-3">
        <Button variant="danger" disabled={busy} onClick={()=>action(async()=>{await api.del(`/notifications/${deleting.id}`);setDeleting(null);},"Notificarea a fost ștearsă.")}>Confirmă ștergerea</Button>
        <Button variant="outline" disabled={busy} onClick={()=>setDeleting(null)}>Păstrează notificarea</Button>
      </div>
    </Card>}
    {loading && !data ? <Spinner /> : !entries.length ? <EmptyState icon={Bell} title="Nicio notificare în această categorie" hint="Memento-urile programărilor apar automat după salvare." /> :
      <div className="space-y-3">{entries.map(n => <Card key={n.id}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h2 className="min-w-0 break-words font-semibold">{n.title}</h2>
          <Badge tone={n.status === "read" ? "neutral" : future(n) ? "blue" : "amber"}>
            {n.status === "read" ? "Citită" : future(n) ? "Programată" : "Necitită"}
          </Badge>
        </div>
        {n.body && <p className="mt-2 whitespace-pre-wrap break-words text-sm">{n.body}</p>}
        <p className="mt-2 text-sm text-muted">{n.scheduled_for ? `Termen: ${dateLabel(n.scheduled_for)}` : `Creată: ${dateLabel(n.created_at)}`}</p>
        <p className="mt-1 text-sm text-muted">{n.status === "sent" ? "Marcată trimisă către serviciul de livrare." : n.status === "failed" ? "Trimiterea nu a fost efectuată." : n.status === "pending" ? "Expedierea externă este în așteptare." : "Ai marcat această notificare ca citită."}</p>
        <div className="mt-3 flex flex-wrap gap-3">
          {n.resource_type === "appointment" && n.resource_id && /^\d+$/.test(n.resource_id) && <Link className="inline-flex min-h-11 items-center rounded-full border border-border px-4 text-sm" href={`/appointments#appointment-${n.resource_id}`}>Deschide programarea</Link>}
          {n.status !== "read" && !future(n) && <Button variant="outline" disabled={busy || !!deleting} onClick={()=>action(()=>api.post(`/notifications/${n.id}/read`),"Notificarea a fost marcată citită.")}>Marchează citită</Button>}
          <Button variant="outline" disabled={busy || !!deleting} onClick={()=>setDeleting(n)}>Șterge notificarea</Button>
        </div>
      </Card>)}</div>}
  </div>;
}
