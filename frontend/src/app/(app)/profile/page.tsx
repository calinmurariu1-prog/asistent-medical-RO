"use client";

import { useEffect, useState } from "react";
import { Bell, Download, User } from "lucide-react";
import { saveExport } from "@/lib/file-export";
import { api, downloadFile } from "@/lib/api";
import { pushDeliveryMessage, sendTestPush } from "@/lib/push";
import type { PatientProfile } from "@/lib/types";
import { Button, Card, Input, PageHeader, Spinner } from "@/components/ui";

export default function ProfilePage() {
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<PatientProfile>("/patients/me")
      .then(setProfile)
      .finally(() => setLoading(false));
  }, []);

  function update<K extends keyof PatientProfile>(
    key: K,
    value: PatientProfile[K],
  ) {
    setProfile((p) => (p ? { ...p, [key]: value } : p));
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!profile) return;
    const updated = await api.put<PatientProfile>("/patients/me", {
      first_name: profile.first_name,
      last_name: profile.last_name,
      birth_date: profile.birth_date,
      sex: profile.sex,
      weight_kg: profile.weight_kg,
      height_cm: profile.height_cm,
      blood_type: profile.blood_type,
      phone: profile.phone,
    });
    setProfile(updated);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  const [pushMsg, setPushMsg] = useState<string | null>(null);
  async function testPush() {
    setPushMsg(null);
    try {
      setPushMsg(pushDeliveryMessage(await sendTestPush()));
    } catch (e) {
      setPushMsg(e instanceof Error ? e.message : "Notificarea nu a putut fi trimisă.");
    }
  }

  const [exporting, setExporting] = useState(false);
  const [exportMessage, setExportMessage] = useState("");
  const [exportError, setExportError] = useState("");
  async function exportReport(fmt: "pdf" | "docx") {
    if (exporting) return;
    setExporting(true); setExportMessage(""); setExportError("");
    try {
      const blob = await downloadFile(`/export/report.${fmt}`);
      setExportMessage(await saveExport(blob, `raport-medical.${fmt}`));
    } catch (e) {
      setExportError(e instanceof Error ? e.message : "Raportul nu a putut fi descărcat.");
    } finally { setExporting(false); }
  }

  if (loading) return <Spinner />;
  if (!profile) return null;

  return (
    <div className="max-w-2xl space-y-6">
      <PageHeader
        title="Profil"
        subtitle="Datele tale de bază și exportul dosarului medical."
        icon={User}
      />

      <Card>
        <form onSubmit={save} className="grid gap-4 sm:grid-cols-2">
          <label className="text-sm">
            Prenume
            <Input
              value={profile.first_name || ""}
              onChange={(e) => update("first_name", e.target.value)}
            />
          </label>
          <label className="text-sm">
            Nume
            <Input
              value={profile.last_name || ""}
              onChange={(e) => update("last_name", e.target.value)}
            />
          </label>
          <label className="text-sm">
            Data nașterii
            <Input
              type="date"
              value={profile.birth_date || ""}
              onChange={(e) => update("birth_date", e.target.value)}
            />
          </label>
          <label className="text-sm">
            Sex
            <select
              value={profile.sex || ""}
              onChange={(e) => update("sex", e.target.value)}
              className="w-full rounded-xl border border-border bg-surface px-4 py-2.5 text-sm"
            >
              <option value="">-</option>
              <option value="male">Masculin</option>
              <option value="female">Feminin</option>
              <option value="other">Altul</option>
            </select>
          </label>
          <label className="text-sm">
            Greutate (kg)
            <Input
              type="number"
              value={profile.weight_kg ?? ""}
              onChange={(e) =>
                update("weight_kg", e.target.value ? Number(e.target.value) : null)
              }
            />
          </label>
          <label className="text-sm">
            Înălțime (cm)
            <Input
              type="number"
              value={profile.height_cm ?? ""}
              onChange={(e) =>
                update("height_cm", e.target.value ? Number(e.target.value) : null)
              }
            />
          </label>
          <div className="sm:col-span-2 flex items-center gap-3">
            <Button type="submit">Salvează</Button>
            {profile.bmi && (
              <span className="text-sm text-muted">IMC: {profile.bmi}</span>
            )}
            {saved && <span className="text-sm text-brand-green">Salvat ✓</span>}
          </div>
        </form>
      </Card>

      <Card>
        <div className="mb-3 flex items-center gap-2 font-semibold">
          <Bell size={18} className="text-brand-violet" /> Notificări push
        </div>
        <p className="mb-3 text-sm text-muted">
          Primește memento-uri pentru medicamente și programări direct pe telefon.
        </p>
        <Button variant="outline" onClick={testPush}>
          <Bell size={16} /> Trimite o notificare de test
        </Button>
        {pushMsg && <p className="mt-2 text-sm text-brand-green">{pushMsg}</p>}
      </Card>

      <Card>
        <div className="mb-3 font-semibold">Export raport medical</div>
        <p className="mb-3 text-sm text-muted">În browser se descarcă fișierul. În aplicația mobilă alegi
          destinația în dialogul sistemului. Raportul conține date medicale; păstrează-l în siguranță.</p>
        {exportMessage && <p role="status" className="mb-3 text-sm">{exportMessage}</p>}
        {exportError && <p role="alert" className="mb-3 text-sm text-red-600">{exportError}</p>}
        <div className="flex gap-3">
          <Button variant="outline" disabled={exporting} onClick={() => exportReport("pdf")}>
            <Download size={16} /> PDF
          </Button>
          <Button variant="outline" disabled={exporting} onClick={() => exportReport("docx")}>
            <Download size={16} /> Word
          </Button>
        </div>
      </Card>
    </div>
  );
}
