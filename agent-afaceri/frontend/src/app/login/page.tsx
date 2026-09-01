"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(email, password);
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Autentificare eșuată");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-sm px-4 py-12">
      <h1 className="mb-6 text-2xl font-bold">Autentificare</h1>
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
          placeholder="Parolă"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-lg border border-slate-300 bg-transparent p-2 text-sm dark:border-slate-700"
        />
        <button
          disabled={loading}
          className="w-full rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-light disabled:opacity-50"
        >
          {loading ? "Se autentifică…" : "Intră în cont"}
        </button>
      </form>
      <p className="mt-4 text-sm text-slate-500">
        Nu ai cont?{" "}
        <Link href="/register" className="text-brand hover:underline dark:text-brand-accent">
          Creează unul
        </Link>
      </p>
    </main>
  );
}
