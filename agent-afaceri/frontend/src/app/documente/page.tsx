"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  deleteDocument,
  DocItem,
  exportDocument,
  listDocuments,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function DocumentePage() {
  const { user, loading } = useAuth();
  const [docs, setDocs] = useState<DocItem[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user) return;
    listDocuments()
      .then(setDocs)
      .catch((e) => setError(String(e.message || e)));
  }, [user]);

  if (loading) return <main className="p-8 text-sm text-slate-500">Se încarcă…</main>;

  if (!user) {
    return (
      <main className="mx-auto max-w-2xl px-4 py-12">
        <p className="text-slate-600 dark:text-slate-400">
          Trebuie să fii autentificat pentru a vedea documentele salvate.{" "}
          <Link href="/login" className="text-brand hover:underline dark:text-brand-accent">
            Autentifică-te
          </Link>
          .
        </p>
      </main>
    );
  }

  async function onDelete(id: number) {
    if (!confirm("Ștergi acest document?")) return;
    await deleteDocument(id);
    setDocs((d) => d.filter((x) => x.id !== id));
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold">Documentele mele</h1>
      {error && (
        <div className="mb-4 rounded-lg bg-red-100 px-4 py-2 text-red-800 dark:bg-red-950 dark:text-red-200">
          {error}
        </div>
      )}
      {docs.length === 0 ? (
        <p className="text-slate-500">
          Niciun document salvat încă. Rulează un skill din{" "}
          <Link href="/" className="text-brand hover:underline dark:text-brand-accent">
            pagina agentului
          </Link>{" "}
          și apasă „Salvează".
        </p>
      ) : (
        <ul className="space-y-3">
          {docs.map((d) => (
            <li
              key={d.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
            >
              <div>
                <div className="font-medium">{d.title}</div>
                <div className="text-xs text-slate-500">
                  {d.category} · {new Date(d.created_at).toLocaleString("ro-RO")}
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => exportDocument(d.id, "pdf")}
                  className="rounded-lg border border-slate-300 px-3 py-1 text-sm hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
                >
                  PDF
                </button>
                <button
                  onClick={() => exportDocument(d.id, "docx")}
                  className="rounded-lg border border-slate-300 px-3 py-1 text-sm hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
                >
                  Word
                </button>
                <button
                  onClick={() => onDelete(d.id)}
                  className="rounded-lg border border-red-300 px-3 py-1 text-sm text-red-700 hover:bg-red-50 dark:border-red-800 dark:text-red-300 dark:hover:bg-red-950"
                >
                  Șterge
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
