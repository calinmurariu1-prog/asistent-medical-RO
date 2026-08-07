"use client";

import { api } from "@/lib/api";
import { isNative } from "@/lib/native";
import type { HealthImportResult } from "@/lib/types";

/**
 * Native health integration: reads on-device data from **HealthKit** (iOS) and
 * **Health Connect** (Android), maps it to our canonical metric types, and pushes
 * it to `POST /health-data/import-json/{source}` — the same normalized pipeline
 * as the file import.
 *
 * The native plugin is resolved via Capacitor's `registerPlugin`, so there is no
 * hard npm dependency and the web build is unaffected. Install the plugin on the
 * native side (see docs/MOBILE.md), e.g. `capacitor-health`:
 *   npm i capacitor-health && npx cap sync
 *
 * `readSamples()` is the single seam that talks to the plugin — adapt its method
 * names/shape to the plugin you pick.
 */

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
  type: string; // canonical metric type
  value: number;
  unit?: string;
  recorded_at: string; // ISO 8601
}

async function plugin(): Promise<any | null> {
  try {
    const { registerPlugin } = await import("@capacitor/core");
    return registerPlugin("HealthPlugin");
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
  const p = await plugin();
  if (!p) return false;
  try {
    const res = await p.isHealthAvailable?.();
    return res ? res.available !== false : true;
  } catch {
    return false;
  }
}

/** Ask the user for read access to the health data types we sync. */
export async function requestHealthPermissions(): Promise<boolean> {
  const p = await plugin();
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
 * Read the requested metrics from the device for the last `daysBack` days.
 *
 * This is the plugin-specific seam. It queries a daily aggregate per metric and
 * returns normalized samples; adjust the call to match your plugin's API.
 */
async function readSamples(daysBack: number): Promise<NativeSample[]> {
  const p = await plugin();
  if (!p) return [];

  const end = new Date();
  const start = new Date(end.getTime() - daysBack * 24 * 60 * 60 * 1000);
  const out: NativeSample[] = [];

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
          out.push({
            type: metric,
            value,
            unit: row.unit,
            recorded_at: new Date(when).toISOString(),
          });
        }
      }
    } catch {
      /* metric unsupported by the plugin / no permission — skip */
    }
  }
  return out;
}

/**
 * Full native sync: request permissions, read samples, push to the backend.
 * Returns the import result, or throws with a user-friendly message.
 */
export async function syncNativeHealth(
  daysBack = 30,
): Promise<HealthImportResult> {
  const source = await platformSource();
  if (!source) throw new Error("Sincronizarea nativă nu este disponibilă aici.");

  await requestHealthPermissions();
  const samples = await readSamples(daysBack);
  if (samples.length === 0) {
    throw new Error(
      "Nicio valoare de citit. Verifică permisiunile pentru aplicațiile de sănătate.",
    );
  }
  return api.post<HealthImportResult>(`/health-data/import-json/${source}`, {
    samples,
  });
}
