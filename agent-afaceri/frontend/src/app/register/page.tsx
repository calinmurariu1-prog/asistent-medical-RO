"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/lib/auth";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password.length < 6) {
      setError("Parola trebuie să aibă minim 6 caractere.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await register(email, password);
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Înregistrare eșuată");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-sm px-4 py-12">
      <h1 className="mb-6 text-2xl font-bold">Cont nou</h1>
      <form onSubmit={onSubmit} className="space-y-4">
        {error && (
          <p className="rounded-lg bg-red-100 px-3 py-2 text-sm text-red-800 dark:bg-red-950 dark:text-red-200">
            {error}
          </p>
        )}
        <input
          type="email"
          required
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-lg border border-slate-300 bg-transparent p-2 text-sm dark:border-slate-700"
        />
        <input
          type="password"
          required
          placeholder="Parolă (min. 6 caractere)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-lg border border-slate-300 bg-transparent p-2 text-sm dark:border-slate-700"
        />
        <button
          disabled={loading}
          className="w-full rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-light disabled:opacity-50"
        >
          {loading ? "Se creează…" : "Creează cont"}
        </button>
      </form>
      <p className="mt-4 text-sm text-slate-500">
        Ai deja cont?{" "}
        <Link href="/login" className="text-brand hover:underline dark:text-brand-accent">
          Autentifică-te
        </Link>
      </p>
    </main>
  );
}
