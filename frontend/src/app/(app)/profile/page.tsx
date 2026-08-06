"use client";

import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { api, downloadFile } from "@/lib/api";
import type { PatientProfile } from "@/lib/types";
import { Button, Card, Input, Spinner } from "@/components/ui";

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

  async function exportReport(fmt: "pdf" | "docx") {
    const blob = await downloadFile(`/export/report.${fmt}`);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `raport-medical.${fmt}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (loading) return <Spinner />;
  if (!profile) return null;

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold">Profil</h1>

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
              className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm"
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
        <div className="mb-3 font-semibold">Export raport medical</div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => exportReport("pdf")}>
            <Download size={16} /> PDF
          </Button>
          <Button variant="outline" onClick={() => exportReport("docx")}>
            <Download size={16} /> Word
          </Button>
        </div>
      </Card>
    </div>
  );
}
