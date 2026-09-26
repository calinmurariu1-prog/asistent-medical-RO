"use client";

import { useEffect } from "react";
import { api } from "@/lib/api";
import { isNative } from "@/lib/native";
import type { HealthImportResult } from "@/lib/types";

/**
 * Native health integration: reads on-device data from **HealthKit** (iOS) and
 * **Health Connect** (Android), auto-detects the wearable that produced it
 * (e.g. Apple Watch), and pushes both to the backend — no file upload.
 *
 * Sync runs automatically when the app opens/resumes (`useHealthAutoSync`),
 * gated by a user preference. The native plugin is resolved via Capacitor's
 * `registerPlugin`, so there is no hard npm dependency (web build unaffected).
 * Install on the native side (see docs/MOBILE.md), e.g. `capacitor-health`.
 *
 * `readData()` is the single seam that talks to the plugin — adapt its
 * method/field names to the plugin you pick.
 */

const AUTOSYNC_KEY = "health_autosync_enabled";

// Our canonical metric -> the native plugin's data-type identifier.
const METRIC_DATATYPES: Record<string, string> = {
  steps: "steps",
  heart_rate: "heart-rate",
  resting_heart_rate: "resting-heart-rate",
  body_weight: "weight",
  active_energy: "active-calories",
  distance: "distance",
  sleep: "sleep",
  oxygen_saturation: "oxygen-saturation",
  blood_glucose: "blood-glucose",
};

interface NativeSample {
  type: string;
  value: number;
  unit?: string;
  recorded_at: string;
}

interface DeviceInfo {
  name: string;
  model?: string;
  metrics: string[];
}

async function plugin(): Promise<any | null> {
  try {
    const { registerPlugin, Capacitor } = await import("@capacitor/core");
    if (!Capacitor.isNativePlatform() || !Capacitor.isPluginAvailable("HealthPlugin")) return null;
    // A Capacitor proxy exposes arbitrary method names, including then. Wrap it
    // so resolving this async function does not invoke a fictitious then().
    return { instance: registerPlugin("HealthPlugin") };
  } catch {
    return null;
  }
}

async function platformSource(): Promise<"apple_health" | "google_health" | null> {
  try {
    const { Capacitor } = await import("@capacitor/core");
    const p = Capacitor.getPlatform();
    if (p === "ios") return "apple_health";
    if (p === "android") return "google_health";
  } catch {
    /* not native */
  }
  return null;
}

/** True only inside the native shell where a health plugin is present. */
export async function healthNativeAvailable(): Promise<boolean> {
  if (!(await isNative())) return false;
  const p = (await plugin())?.instance;
  if (!p) return false;
  try {
    const res = await p.isHealthAvailable?.();
    return res?.available === true;
  } catch {
    return false;
  }
}

/** Ask the user for read access to the health data types we sync. */
export async function requestHealthPermissions(): Promise<boolean> {
  const p = (await plugin())?.instance;
  if (!p) return false;
  const permissions = Object.keys(METRIC_DATATYPES).map(
    (m) => `READ_${m.toUpperCase()}`,
  );
  try {
    await p.requestHealthPermissions?.({ permissions });
    return true;
  } catch {
    return false;
  }
}

/**
 * Read metrics + the source device for the last `daysBack` days.
 * Plugin-specific seam — adjust to your plugin's query API and field names.
 */
async function readData(
  daysBack: number,
): Promise<{ samples: NativeSample[]; devices: DeviceInfo[] }> {
  const p = (await plugin())?.instance;
  if (!p) return { samples: [], devices: [] };

  const end = new Date();
  const start = new Date(end.getTime() - daysBack * 24 * 60 * 60 * 1000);
  const samples: NativeSample[] = [];
  const deviceMetrics = new Map<string, Set<string>>();

  for (const [metric, dataType] of Object.entries(METRIC_DATATYPES)) {
    try {
      const res = await p.queryAggregated?.({
        startDate: start.toISOString(),
        endDate: end.toISOString(),
        dataType,
        bucket: "day",
      });
      for (const row of res?.aggregatedData ?? res?.data ?? []) {
        const value = Number(row.value ?? row.total ?? row.sum);
        const when = row.startDate ?? row.date ?? row.startTime;
        if (Number.isFinite(value) && when) {
          samples.push({
            type: metric,
            value,
            unit: row.unit,
            recorded_at: new Date(when).toISOString(),
          });
          // Source device off the sample metadata (name varies by plugin).
          const dev = row.sourceName ?? row.device ?? row.source ?? row.sourceBundleId;
          if (dev) {
            if (!deviceMetrics.has(dev)) deviceMetrics.set(dev, new Set());
            deviceMetrics.get(dev)!.add(metric);
          }
        }
      }
    } catch {
      /* metric unsupported / no permission — skip */
    }
  }

  const devices: DeviceInfo[] = [...deviceMetrics.entries()].map(
    ([name, metrics]) => ({ name, metrics: [...metrics] }),
  );
  return { samples, devices };
}

/**
 * Full native sync: request permissions, read samples + devices, push to the
 * backend. Returns the import result, or throws with a user-friendly message.
 */
export async function syncNativeHealth(
  daysBack = 30,
): Promise<HealthImportResult> {
  const source = await platformSource();
  if (!source) throw new Error("Sincronizarea nativă nu este disponibilă aici.");

  if (!(await requestHealthPermissions())) {
    throw new Error("Accesul la datele de sănătate nu a fost acordat.");
  }
  const { samples, devices } = await readData(daysBack);
  if (samples.length === 0) {
    throw new Error(
      "Nicio valoare de citit. Verifică permisiunile pentru aplicațiile de sănătate.",
    );
  }
  return api.post<HealthImportResult>(`/health-data/import-json/${source}`, {
    samples,
    devices,
  });
}

// ---------------------------------------------------------------------------
// Auto-sync preference + on-open/resume trigger
// ---------------------------------------------------------------------------
async function prefs(): Promise<any | null> {
  try {
    return await import("@capacitor/preferences");
  } catch {
    return null;
  }
}

export async function isAutoSyncEnabled(): Promise<boolean> {
  const P = (await prefs())?.Preferences;
  if (!P) return true; // default on when preferences unavailable
  try {
    const { value } = await P.get({ key: AUTOSYNC_KEY });
    return value !== "false";
  } catch {
    return true;
  }
}

export async function setAutoSyncEnabled(enabled: boolean): Promise<void> {
  const P = (await prefs())?.Preferences;
  if (!P) return;
  try {
    await P.set({ key: AUTOSYNC_KEY, value: enabled ? "true" : "false" });
  } catch {
    /* ignore */
  }
}

/**
 * Automatically sync health data when the app opens and every time it resumes
 * from the background — no manual action, no file upload. No-op on web or when
 * auto-sync is disabled.
 */
export function useHealthAutoSync(onResult?: (r: HealthImportResult) => void): void {
  useEffect(() => {
    let removeListener: (() => void) | undefined;
    let cancelled = false;

    (async () => {
      if (!(await healthNativeAvailable())) return;
      if (!(await isAutoSyncEnabled())) return;

      const run = async () => {
        try {
          const r = await syncNativeHealth(30);
          if (!cancelled) onResult?.(r);
        } catch {
          /* silent: background sync shouldn't interrupt the user */
        }
      };

      await run(); // initial sync on open

      try {
        const { App } = await import("@capacitor/app");
        const handle = await App.addListener("resume", run);
        removeListener = () => handle.remove();
      } catch {
        /* App plugin unavailable */
      }
    })();

    return () => {
      cancelled = true;
      removeListener?.();
    };
  }, [onResult]);
}
