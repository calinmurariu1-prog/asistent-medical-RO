"use client";

import { useEffect, useState } from "react";
import { Capacitor } from "@capacitor/core";
import { Download } from "lucide-react";
import { saveExport } from "@/lib/file-export";
import { useAuth } from "@/lib/auth";
import { api, downloadFile } from "@/lib/api";
import { Button, Card, Input } from "@/components/ui";

export function DataExport() {
  const { user } = useAuth();
  const [includeCnp, setIncludeCnp] = useState(false);
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [native, setNative] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  useEffect(() => { setNative(Capacitor.isNativePlatform()); }, []);

  async function download(archive = false) {
    if (busy) return;
    setBusy(true); setMessage(""); setError("");
    try {
      const blob = includeCnp && !archive
        ? new Blob([JSON.stringify(await api.post("/gdpr/export/with-identifier", {
            password, mfa_code: mfaCode || null, include_cnp: true,
          }), null, 2)], {type: "application/json"})
        : await downloadFile(archive ? "/gdpr/export/archive" : "/gdpr/export");
      setPassword(""); setMfaCode("");
      setMessage(await saveExport(blob, `dosar-medical-${new Date().toISOString().slice(0, 10)}.${archive ? "zip" : "json"}`));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Exportul nu a putut fi descărcat. Reîncearcă.");
    } finally { setBusy(false); }
  }

  return <Card className="space-y-3" aria-labelledby="data-export-title">
    <h2 id="data-export-title" className="flex items-center gap-2 font-semibold">
      <Download size={18} aria-hidden="true" /> Exportă datele din dosar
    </h2>
    <p className="text-sm text-muted">Descarcă un fișier JSON cu profilul, acordurile, istoricul medical,
      analizele, documentele extrase, tratamentele, memento-urile, programările, conversațiile, măsurătorile de sănătate, dispozitivele, notificările, feedbackul, starea abonamentului și istoricul acțiunilor contului.</p>
    <p className="text-sm text-muted">Originalele se descarcă separat din Documente sau împreună cu JSON într-o arhivă ZIP de maximum 25 MB și 1000 de documente. Exportul obișnuit nu include
      CNP, facturi externe sau identificatori ai furnizorului de plăți.</p>
    <p className="text-sm">Fișierul conține date personale și medicale. Păstrează-l într-un loc sigur.</p>
    {native && <p className="text-sm text-muted">Alege destinația în dialogul sistemului. Copia temporară
      rămâne în memoria cache privată; copiile mai vechi de 24 de ore se curăță la următorul export.</p>}
    <label className="flex items-start gap-2 text-sm"><input type="checkbox" disabled={busy} checked={includeCnp}
      onChange={e => {setIncludeCnp(e.target.checked); setPassword(""); setMfaCode("");}} />Include CNP în fișierul JSON, dacă este salvat în profil</label>
    {includeCnp && <div className="space-y-3">
      <p className="text-sm text-muted">Confirmă identitatea pentru acest export. Arhiva ZIP rămâne fără CNP.</p>
      <label className="block text-sm">Parola pentru export<Input type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} disabled={busy} /></label>
      {user?.mfa_enabled && <label className="block text-sm">Cod MFA pentru export<Input autoComplete="one-time-code" maxLength={64} value={mfaCode} onChange={e => setMfaCode(e.target.value)} disabled={busy} /></label>}
    </div>}
    <Button onClick={() => download()} disabled={busy || (includeCnp && (!password || (!!user?.mfa_enabled && !mfaCode)))}>
      <Download size={16} aria-hidden="true" /> {busy ? "Se pregătește exportul…" : native ? "Salvează sau partajează JSON" : "Descarcă dosarul JSON"}
    </Button>
    <Button onClick={() => download(true)} disabled={busy || includeCnp}>Descarcă arhiva cu originale</Button>
    {message && <p role="status" className="text-sm text-brand-green">{message}</p>}
    {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
  </Card>;
}
