"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { Button, Card, Input } from "@/components/ui";
import { LogoMark } from "@/components/logo";
import { GradientBlobs } from "@/components/decor";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [mfaNeeded, setMfaNeeded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("logout") === "unconfirmed")
      setError("Serverul nu a confirmat deconectarea. Unele sesiuni pot fi încă active. Reconectează-te pentru a reîncerca.");
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password, mfaCode);
    } catch (err) {
      if (err instanceof ApiError && err.message.includes("MFA")) {
        setMfaNeeded(true);
        setError("Introdu codul MFA.");
      } else {
        setError(err instanceof ApiError ? err.message : "Eroare la autentificare");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-[100dvh] items-center justify-center p-6">
      <GradientBlobs />
      <Card className="w-full max-w-md">
        <div className="mb-6 flex flex-col items-center gap-3 text-center">
          <LogoMark size={56} />
          <div>
            <div className="text-lg font-bold">Asistent Medical AI</div>
            <p className="text-sm text-muted">
              Dosarul tău medical, înțeles pe limba ta.
            </p>
          </div>
        </div>
        <h1 className="text-xl font-bold">Bine ai revenit</h1>
        <form onSubmit={onSubmit} className="mt-5 space-y-3">
          <Input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Input
            type="password"
            placeholder="Parolă"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {mfaNeeded && (
            <Input
              placeholder="Cod MFA"
              value={mfaCode}
              onChange={(e) => setMfaCode(e.target.value)}
            />
          )}
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Se conectează…" : "Intră în cont"}
          </Button>
        </form>
        <Link href="/forgot-password" className="mt-4 block text-brand-blue">Am uitat parola</Link>
        <p className="mt-4 text-center text-sm text-muted">
          Nu ai cont?{" "}
          <Link href="/register" className="text-brand-blue hover:underline">
            Înregistrează-te
          </Link>
        </p>
      </Card>
    </main>
  );
}
