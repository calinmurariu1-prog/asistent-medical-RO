"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { Button, Card, Spinner } from "@/components/ui";

type AIStatus = { provider: string; simulated: boolean; consent_required: boolean };
type Consent = { consent_type: string; granted: boolean; version: string };

export function AIConsent() {
  const status = useFetch<AIStatus>("/ai/status");
  const consents = useFetch<Consent[]>("/gdpr/consents");
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const latest = consents.data?.find(c => c.consent_type === "ai_processing");
  const granted = latest?.granted && latest.version === `ai-v2:${status.data?.provider}`;

  async function save(granted: boolean) {
    setBusy(true); setError(null); setMessage(null);
    try {
      const updated = await api.post<Consent>("/gdpr/consents", {
        consent_type: "ai_processing", granted, provider: status.data?.provider,
      });
      consents.setData(previous => [...(previous || []).filter(c => c.consent_type !== "ai_processing"), updated]);
      setAccepted(false);
      setMessage(granted ? "Acordul a fost salvat." : "Acordul a fost retras. Cererile externe viitoare sunt blocate.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Acordul nu a putut fi salvat.");
    } finally { setBusy(false); }
  }

  return <Card className="space-y-3">
    <h2 className="font-semibold">Confidențialitate și AI</h2>
    {status.loading || consents.loading ? <Spinner /> : status.error || consents.error ? <>
      <p role="alert" className="text-sm text-red-600">Starea acordului nu a putut fi încărcată.</p>
      <Button variant="outline" onClick={() => {status.reload(); consents.reload();}}>Reîncearcă</Button>
    </> : status.data && <>
      <p className="text-sm text-muted">{status.data.simulated
        ? "Mod simulat: procesarea AI se face local, fără trimitere către un furnizor AI extern."
        : `Furnizor AI activ: ${status.data.provider}. Funcțiile AI pot trimite textul documentelor, analizele și întrebările tale către acest furnizor.`}</p>
      <p className="text-sm text-muted">Acordul se aplică furnizorului afișat. Poți să-l retragi oricând; retragerea blochează cererile viitoare, dar nu anulează procesările deja efectuate. Rezultatele AI sunt informative.</p>
      <p className="text-sm">{granted ? "Acord activ pentru furnizorul curent." : "Nu ai un acord activ pentru furnizorul curent."}</p>
      {!granted && <label className="flex items-start gap-2 text-sm">
        <input type="checkbox" className="mt-1 h-4 w-4 accent-brand-blue" checked={accepted}
          onChange={e => setAccepted(e.target.checked)} disabled={busy} />
        Sunt de acord cu procesarea AI a datelor selectate pentru funcțiile pe care le folosesc, prin furnizorul afișat.
      </label>}
      <Button variant="outline" disabled={busy || (!granted && !accepted)} onClick={() => save(!granted)}>
        {busy ? "Se salvează…" : granted ? "Retrage acordul AI" : "Salvează acordul AI"}
      </Button>
    </>}
    {message && <p role="status" className="text-sm text-brand-green">{message}</p>}
    {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
  </Card>;
}
