"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button, Card } from "@/components/ui";

export function EmailVerification() {
  const {user} = useAuth();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  async function resend() {
    setBusy(true); setError(""); setMessage("");
    try {
      const result = await api.post<{detail: string}>("/auth/email/resend");
      setMessage(result.detail);
    } catch (e) { setError(e instanceof Error ? e.message : "Mesajul nu a putut fi trimis."); }
    finally { setBusy(false); }
  }
  return <Card className="space-y-3" aria-labelledby="email-verification-title">
    <h2 id="email-verification-title" className="font-semibold">Confirmarea adresei de email</h2>
    <p className="break-all text-sm">{user?.email}</p>
    {user?.is_email_verified ? <p role="status">Adresa de email este confirmată.</p> : <>
      <p className="text-sm text-muted">Dacă linkul a expirat sau nu găsești mesajul, solicită unul nou pentru această adresă.</p>
      <Button disabled={busy || !user} onClick={resend}>{busy ? "Se pregătește mesajul…" : "Trimite un link nou de confirmare"}</Button>
    </>}
    {message && <p role="status" className="text-sm">{message}</p>}
    {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
  </Card>;
}
