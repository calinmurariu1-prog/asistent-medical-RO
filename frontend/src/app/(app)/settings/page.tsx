"use client";

import { useEffect, useState } from "react";
import {
  Bell,
  Bluetooth,
  HeartPulse,
  LogOut,
  Settings as SettingsIcon,
  Smartphone,
  Trash2,
  Watch,
} from "lucide-react";
import { useFetch } from "@/lib/hooks";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  healthNativeAvailable,
  isAutoSyncEnabled,
  setAutoSyncEnabled,
  syncNativeHealth,
} from "@/lib/health-native";
import { bluetoothAvailable, connectHealthDevice } from "@/lib/bluetooth";
import { sendTestPush } from "@/lib/push";
import type { HealthDevice } from "@/lib/types";
import { Badge, Button, Card, Input, PageHeader, Spinner } from "@/components/ui";

function Section({
  icon: Icon,
  title,
  desc,
  children,
}: {
  icon: typeof Bell;
  title: string;
  desc?: string;
  children: React.ReactNode;
}) {
  return (
    <Card className="space-y-3">
      <div className="flex items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-surface-2 text-brand-blue">
          <Icon size={18} />
        </span>
        <div>
          <h2 className="font-semibold">{title}</h2>
          {desc && <p className="text-sm text-muted">{desc}</p>}
        </div>
      </div>
      {children}
    </Card>
  );
}

export default function SettingsPage() {
  const { logout } = useAuth();
  const devices = useFetch<HealthDevice[]>("/health-data/devices");
  const [native, setNative] = useState(false);
  const [ble, setBle] = useState(false);
  const [autoSync, setAutoSync] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    healthNativeAvailable().then(setNative);
    bluetoothAvailable().then(setBle);
    isAutoSyncEnabled().then(setAutoSync);
  }, []);

  function flash(setter: (v: string | null) => void, text: string) {
    setter(text);
    setTimeout(() => setter(null), 4000);
  }

  async function run(id: string, fn: () => Promise<string>) {
    setBusy(id);
    setMsg(null);
    setErr(null);
    try {
      flash(setMsg, await fn());
      devices.reload();
    } catch (e) {
      flash(setErr, e instanceof Error ? e.message : "Operațiune eșuată");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <PageHeader
        title="Setări"
        subtitle="Conexiuni, dispozitive, notificări și cont."
        icon={SettingsIcon}
      />

      {msg && <p className="text-sm text-brand-green">{msg}</p>}
      {err && <p className="text-sm text-red-600">{err}</p>}

      {/* Watch / health apps */}
      <Section
        icon={Watch}
        title="Ceas & aplicații de sănătate"
        desc="Sincronizează automat din Sănătate (HealthKit) / Health Connect — pași, puls, somn, SpO₂."
      >
        {native ? (
          <>
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={() =>
                  run("sync", async () => (await syncNativeHealth(30)).message)
                }
                disabled={busy === "sync"}
              >
                <HeartPulse size={16} />
                {busy === "sync" ? "Se sincronizează…" : "Sincronizează acum"}
              </Button>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={autoSync}
                onChange={async (e) => {
                  setAutoSync(e.target.checked);
                  await setAutoSyncEnabled(e.target.checked);
                }}
                className="h-4 w-4 accent-brand-blue"
              />
              Sincronizare automată la deschiderea aplicației
            </label>
          </>
        ) : (
          <p className="flex items-center gap-2 text-sm text-muted">
            <Smartphone size={15} /> Disponibil în aplicația mobilă (Android/iOS).
          </p>
        )}
      </Section>

      {/* Bluetooth */}
      <Section
        icon={Bluetooth}
        title="Dispozitive Bluetooth"
        desc="Conectează tensiometre, glucometre, oximetre, cântare sau centuri de puls (BLE)."
      >
        {ble ? (
          <Button
            onClick={() =>
              run("ble", async () => (await connectHealthDevice()).message)
            }
            disabled={busy === "ble"}
          >
            <Bluetooth size={16} />
            {busy === "ble" ? "Se conectează…" : "Caută & conectează"}
          </Button>
        ) : (
          <p className="flex items-center gap-2 text-sm text-muted">
            <Smartphone size={15} /> Conectarea Bluetooth funcționează în aplicația
            mobilă.
          </p>
        )}
      </Section>

      {/* Detected devices */}
      {(devices.data || []).length > 0 && (
        <Section icon={Watch} title="Dispozitive conectate">
          <div className="grid gap-2 sm:grid-cols-2">
            {(devices.data || []).map((d) => (
              <div
                key={`${d.source}-${d.name}`}
                className="flex items-center justify-between rounded-2xl border border-border/70 p-3"
              >
                <div>
                  <p className="text-sm font-medium">{d.name}</p>
                  <p className="text-xs text-muted">
                    {d.vendor ? `${d.vendor} · ` : ""}
                    {d.metrics.length} metrici
                  </p>
                </div>
                <Badge tone="green">activ</Badge>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Notifications */}
      <Section
        icon={Bell}
        title="Notificări"
        desc="Memento-uri pentru medicamente și programări, pe telefon."
      >
        <Button
          variant="outline"
          onClick={() =>
            run("push", async () => {
              const n = await sendTestPush();
              return n > 0
                ? `Notificare trimisă către ${n} dispozitiv(e).`
                : "Niciun dispozitiv înregistrat (deschide aplicația pe telefon și acceptă notificările).";
            })
          }
          disabled={busy === "push"}
        >
          <Bell size={16} /> Trimite o notificare de test
        </Button>
      </Section>

      {/* Account */}
      <AccountSection logout={logout} />
    </div>
  );
}

function AccountSection({ logout }: { logout: () => void }) {
  const [confirming, setConfirming] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  async function deleteAccount() {
    setDeleting(true);
    setError(null);
    try {
      await api.post("/gdpr/delete-account", { password, confirm: true });
      logout();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ștergere eșuată");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Section icon={LogOut} title="Cont">
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" onClick={logout}>
          <LogOut size={16} /> Deconectare
        </Button>
        {!confirming && (
          <Button variant="danger" onClick={() => setConfirming(true)}>
            <Trash2 size={16} /> Șterge contul
          </Button>
        )}
      </div>

      {confirming && (
        <div className="space-y-2 rounded-2xl border border-red-500/30 bg-red-500/5 p-3">
          <p className="text-sm">
            Această acțiune șterge definitiv contul și toate datele tale medicale.
            Introdu parola pentru a confirma.
          </p>
          <Input
            type="password"
            placeholder="Parola"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex gap-2">
            <Button
              variant="danger"
              onClick={deleteAccount}
              disabled={deleting || !password}
            >
              {deleting ? "Se șterge…" : "Confirmă ștergerea"}
            </Button>
            <Button variant="outline" onClick={() => setConfirming(false)}>
              Anulează
            </Button>
          </div>
        </div>
      )}
    </Section>
  );
}
