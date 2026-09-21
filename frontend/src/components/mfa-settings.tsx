"use client";

import { useState } from "react";
import { api, clearTokens } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button, Card, Input } from "@/components/ui";

export function MFASettings() {
  const { user } = useAuth();
  const [secret, setSecret] = useState("");
  const [code, setCode] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [activated, setActivated] = useState(false);

  async function setup() {
    setBusy(true); setError("");
    try {
      const result = await api.post<{secret: string}>("/auth/mfa/setup");
      setSecret(result.secret); setCode(""); setSaved(false);
    } catch (e) { setError(e instanceof Error ? e.message : "Configurarea nu a reușit."); }
    finally { setBusy(false); }
  }
  async function activate(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError("");
    try {
      await api.post("/auth/mfa/activate", {code});
      setSecret(""); setCode(""); setActivated(true);
      await clearTokens();
    } catch (e) { setError(e instanceof Error ? e.message : "Activarea nu a fost confirmată."); }
    finally { setBusy(false); }
  }
  return <Card className="space-y-3" aria-labelledby="mfa-title">
    <h2 id="mfa-title" className="font-semibold">Autentificare în doi pași</h2>
    {activated ? <>
      <p role="status">MFA este activ. Sesiunile anterioare au fost revocate. Autentifică-te din nou cu parola și codul din aplicația de autentificare.</p>
      <a className="inline-flex min-h-11 items-center text-brand-blue underline" href="/login?mfa=enabled">Continuă la autentificare</a>
    </> : user?.mfa_enabled ? <p role="status">MFA este activ pentru contul tău.</p> : <>
      <p className="text-sm text-muted">Adaugă un cod temporar din aplicația ta de autentificare, pe lângă parolă.</p>
      <p className="text-sm text-muted">Păstrează cheia într-un loc sigur. Nu există încă un flux de recuperare MFA; resetarea parolei nu elimină acest pas. Activarea deconectează toate sesiunile.</p>
      {!secret ? <Button disabled={busy || !user} onClick={setup}>{busy ? "Se pregătește…" : "Configurează MFA"}</Button> :
        <form onSubmit={activate} className="space-y-3">
          <p className="text-sm">În aplicația de autentificare, adaugă manual contul {user?.email}, cu cheie și coduri bazate pe timp (TOTP).</p>
          <label className="block text-sm">Cheia de configurare
            <Input className="font-mono" value={secret} readOnly autoComplete="off" spellCheck={false} />
          </label>
          <label className="flex items-start gap-2 text-sm"><input className="mt-1" type="checkbox" checked={saved} disabled={busy} onChange={e => setSaved(e.target.checked)} />Am păstrat cheia în siguranță și am adăugat contul în aplicația de autentificare.</label>
          <label className="block text-sm">Cod de confirmare
            <Input value={code} onChange={e => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))} inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required disabled={busy} />
          </label>
          <Button disabled={busy || !saved || code.length !== 6} type="submit">{busy ? "Se verifică…" : "Activează MFA"}</Button>
          <Button type="button" disabled={busy} onClick={() => {setSecret(""); setCode(""); setSaved(false); setError("");}}>Anulează configurarea</Button>
        </form>}
    </>}
    {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
  </Card>;
}
