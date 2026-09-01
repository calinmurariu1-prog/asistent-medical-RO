"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

export default function Header() {
  const { user, logout } = useAuth();
  return (
    <header className="border-b border-slate-200 bg-white/80 backdrop-blur dark:border-slate-800 dark:bg-slate-950/80">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link href="/" className="font-bold text-brand dark:text-brand-accent">
          ⚖️ Agent Afaceri &amp; Juridic
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          <Link href="/" className="hover:underline">
            Agent
          </Link>
          {user ? (
            <>
              <Link href="/documente" className="hover:underline">
                Documentele mele
              </Link>
              <span className="hidden text-slate-500 sm:inline">{user.email}</span>
              <button
                onClick={logout}
                className="rounded-lg border border-slate-300 px-3 py-1 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
              >
                Ieșire
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="hover:underline">
                Autentificare
              </Link>
              <Link
                href="/register"
                className="rounded-lg bg-brand px-3 py-1 text-white hover:bg-brand-light"
              >
                Cont nou
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
