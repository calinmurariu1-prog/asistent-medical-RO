"use client";

import { useRef, useState } from "react";
import { FileText, Upload } from "lucide-react";
import { useFetch } from "@/lib/hooks";
import { api } from "@/lib/api";
import type { DocumentItem } from "@/lib/types";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  PageHeader,
  Spinner,
} from "@/components/ui";

const CATEGORIES = [
  ["lab", "Analize laborator"],
  ["ct", "CT"],
  ["mri", "RMN"],
  ["ultrasound", "Ecografie"],
  ["xray", "Radiografie"],
  ["medical_letter", "Scrisoare medicală"],
  ["discharge", "Bilet externare"],
  ["prescription", "Rețetă"],
  ["other", "Altele"],
];

export default function DocumentsPage() {
  const { data, loading, reload } = useFetch<DocumentItem[]>("/documents");
  const [category, setCategory] = useState("lab");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function onUpload(e: React.FormEvent) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("category", category);
      await api.postForm("/documents", form);
      if (fileRef.current) fileRef.current.value = "";
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Încărcare eșuată");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Documente"
        subtitle="Încarcă analize și scrisori — AI extrage textul și valorile."
        icon={FileText}
      />

      <Card>
        <form onSubmit={onUpload} className="flex flex-wrap items-center gap-3">
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,.dcm"
            className="text-sm"
            required
          />
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm"
          >
            {CATEGORIES.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
          <Button type="submit" disabled={uploading}>
            <Upload size={16} />
            {uploading ? "Se procesează…" : "Încarcă"}
          </Button>
        </form>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
        <p className="mt-2 text-xs text-muted">
          Acceptate: PDF, JPG, PNG, DICOM. AI extrage automat textul și valorile.
        </p>
      </Card>

      {loading ? (
        <Spinner />
      ) : (data || []).length === 0 ? (
        <EmptyState
          icon={FileText}
          title="Niciun document încărcat"
          hint="Încarcă primul tău document (PDF, poză sau DICOM) pentru a începe."
        />
      ) : (
        <div className="space-y-3">
          {(data || []).map((d) => (
            <Card key={d.id}>
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate font-medium">
                    {d.original_filename}
                  </div>
                  <div className="text-xs text-muted">
                    {d.category} ·{" "}
                    {new Date(d.created_at).toLocaleDateString("ro-RO")}
                  </div>
                </div>
                <Badge tone={d.status === "done" ? "green" : "amber"}>
                  {d.status}
                </Badge>
              </div>
              {d.ai_summary && (
                <p className="mt-3 rounded-2xl bg-surface-2 p-3 text-sm text-fg/80">
                  {d.ai_summary}
                </p>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
