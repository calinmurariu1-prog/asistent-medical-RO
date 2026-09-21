"use client";

import { useEffect, useState } from "react";
import { Capacitor } from "@capacitor/core";
import { Download } from "lucide-react";
import { saveExport } from "@/lib/file-export";
import { downloadFile } from "@/lib/api";
import { Button, Card } from "@/components/ui";

export function DataExport() {
  const [busy, setBusy] = useState(false);
  const [native, setNative] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  useEffect(() => { setNative(Capacitor.isNativePlatform()); }, []);

  async function download() {
    if (busy) return;
    setBusy(true); setMessage(""); setError("");
    try {
      const blob = await downloadFile("/gdpr/export");
      setMessage(await saveExport(blob, `dosar-medical-${new Date().toISOString().slice(0, 10)}.json`));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Exportul nu a putut fi descărcat. Reîncearcă.");
    } finally { setBusy(false); }
  }

  return <Card className="space-y-3" aria-labelledby="data-export-title">
    <h2 id="data-export-title" className="flex items-center gap-2 font-semibold">
      <Download size={18} aria-hidden="true" /> Exportă datele din dosar
    </h2>
    <p className="text-sm text-muted">Descarcă un fișier JSON cu profilul, acordurile, istoricul medical,
      analizele, documentele extrase, tratamentele, memento-urile, programările, conversațiile, măsurătorile de sănătate, dispozitivele, notificările și feedbackul.</p>
    <p className="text-sm text-muted">Originalele se descarcă separat din Documente. Exportul nu include
      CNP, facturarea sau jurnalul de audit.</p>
    <p className="text-sm">Fișierul conține date personale și medicale. Păstrează-l într-un loc sigur.</p>
    {native && <p className="text-sm text-muted">Alege destinația în dialogul sistemului. Copia temporară
      rămâne în memoria cache privată; copiile mai vechi de 24 de ore se curăță la următorul export.</p>}
    <Button onClick={download} disabled={busy}>
      <Download size={16} aria-hidden="true" /> {busy ? "Se pregătește exportul…" : native ? "Salvează sau partajează JSON" : "Descarcă dosarul JSON"}
    </Button>
    {message && <p role="status" className="text-sm text-brand-green">{message}</p>}
    {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
  </Card>;
}
