"use client";

import { useRef, useState } from "react";
import { FileText, Upload } from "lucide-react";
import { useFetch } from "@/lib/hooks";
import { saveExport } from "@/lib/file-export";
import { api, downloadFile } from "@/lib/api";
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
  const [documentDate, setDocumentDate] = useState("");
  const [editingDate, setEditingDate] = useState<number | null>(null);
  const [dateValue, setDateValue] = useState("");
  const [savingDate, setSavingDate] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [retrying, setRetrying] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<number | null>(null);
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
      if (documentDate) form.append("document_date", documentDate);
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
        subtitle="Încarcă analize și scrisori — Extragem textul și valorile disponibile."
        icon={FileText}
      />

      <Card>
        <form onSubmit={onUpload} className="flex flex-wrap items-center gap-3">
          <input
            ref={fileRef}
            type="file"
            aria-label="Document medical"
            accept=".pdf,.jpg,.jpeg,.png,.docx,.dcm"
            className="text-sm"
            required
          />
          <select
            aria-label="Categorie document"
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
          <label className="text-sm">
            Data documentului (opțional)
            <input type="date" value={documentDate} onChange={e=>setDocumentDate(e.target.value)}
              className="block min-h-12 rounded-xl border border-border bg-surface px-3 text-fg" />
          </label>
          <Button type="submit" disabled={uploading}>
            <Upload size={16} />
            {uploading ? "Se procesează…" : "Încarcă"}
          </Button>
        </form>
        {error && <p role="alert" className="mt-2 text-sm text-red-600">{error}</p>}
        {notice && <p role="status" className="mt-2 text-sm">{notice}</p>}
        <p className="mt-2 text-xs text-muted">
          Acceptate: PDF, JPG, PNG, DOCX, DICOM. Scanările necesită OCR disponibil.
          La descărcare, aplicația mobilă deschide dialogul sistemului pentru salvare sau partajare.
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
                  <Button disabled={downloading !== null} onClick={async () => {
                    if (downloading !== null) return;
                    setDownloading(d.id); setError(null); setNotice(null);
                    try {
                      const blob = await downloadFile(`/documents/${d.id}/original`);
                      setNotice(await saveExport(blob, d.original_filename));
                    } catch (e) {
                      setError(e instanceof Error ? e.message : "Descărcare eșuată");
                    } finally { setDownloading(null); }
                  }}>{downloading === d.id ? "Se pregătește…" : "Descarcă originalul"}</Button>
                  <div className="truncate font-medium">
                    {d.original_filename}
                  </div>
                  <div className="text-xs text-muted">
                    {d.category} ·{" "}
                    {new Date(d.created_at).toLocaleDateString("ro-RO")}
                  </div>
                </div>
                <Badge tone={d.status === "done" ? "green" : "amber"}>
                  {{done:"Procesat",failed:"Necesită verificare",processing:"Se procesează",pending:"În așteptare"}[d.status] || d.status}
                </Badge>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
                <span>{d.document_date ? `Data documentului: ${d.document_date}` : "Data documentului nu este completată."}</span>
                <Button variant="outline" disabled={savingDate || d.status === "processing"} onClick={()=>{setEditingDate(d.id);setDateValue(d.document_date || "");setError(null);setNotice(null);}}>Corectează data</Button>
              </div>
              {editingDate === d.id && <form className="mt-3 space-y-3 rounded-xl border border-border p-3" onSubmit={async e=>{
                e.preventDefault();setSavingDate(true);setError(null);
                try {
                  await api.put(`/documents/${d.id}/date`,{document_date:dateValue || null});
                  setEditingDate(null);setNotice("Data documentului și a analizelor asociate a fost actualizată.");reload();
                } catch(e) {setError(e instanceof Error ? e.message : "Data nu a putut fi salvată.");}
                finally {setSavingDate(false);}
              }}>
                <label className="block text-sm">Data corectată
                  <input type="date" value={dateValue} onChange={e=>setDateValue(e.target.value)} disabled={savingDate}
                    className="block min-h-12 rounded-xl border border-border bg-surface px-3 text-fg" />
                </label>
                <p className="text-sm text-muted">Data se aplică tuturor analizelor extrase din acest document. Lasă câmpul gol dacă data nu este cunoscută.</p>
                <div className="flex flex-wrap gap-3"><Button type="submit" disabled={savingDate}>Salvează data</Button>
                  <Button type="button" variant="outline" disabled={savingDate} onClick={()=>setEditingDate(null)}>Anulează</Button></div>
              </form>}
              {<Button disabled={retrying === d.id} onClick={async () => {
                setRetrying(d.id); setError(null);
                try { await api.post(`/documents/${d.id}/reprocess`); reload(); }
                catch (e) { setError(e instanceof Error ? e.message : "Reprocesare eșuată"); }
                finally { setRetrying(null); }
              }}>{retrying === d.id ? "Se procesează…" : d.status === "done" ? "Reprocesează documentul" : "Reîncearcă procesarea"}</Button>}
              {d.status === "processing" && <p className="mt-2 text-sm text-muted">O procesare întreruptă poate fi reîncercată după 20 de minute. Originalul este păstrat.</p>}
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
