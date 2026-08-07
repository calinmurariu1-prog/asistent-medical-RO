"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { Button, Card, Input } from "@/components/ui";
import { LogoMark } from "@/components/logo";

export default function RegisterPage() {
  const { register } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("Parola trebuie să aibă minim 8 caractere.");
      return;
    }
    setLoading(true);
    try {
      await register(email, password, fullName);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Eroare la înregistrare");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <Card className="w-full max-w-md">
        <div className="mb-6 flex items-center gap-2 font-semibold">
          <LogoMark />
          Asistent Medical AI
        </div>
        <h1 className="text-xl font-bold">Creează cont</h1>
        <form onSubmit={onSubmit} className="mt-5 space-y-3">
          <Input
            placeholder="Nume complet"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
          <Input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Input
            type="password"
            placeholder="Parolă (min. 8 caractere)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Se creează…" : "Creează cont"}
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-muted">
          Ai deja cont?{" "}
          <Link href="/login" className="text-brand-blue hover:underline">
            Autentifică-te
          </Link>
        </p>
      </Card>
    </main>
  );
}
