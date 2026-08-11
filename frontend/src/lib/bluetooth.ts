"use client";

import { api } from "@/lib/api";
import { isNative } from "@/lib/native";
import type { HealthImportResult } from "@/lib/types";

/**
 * Bluetooth Low Energy health devices (blood-pressure monitors, glucometers,
 * scales, oximeters, heart-rate straps…) via `@capacitor-community/bluetooth-le`.
 *
 * A reading is normalized to a `HealthMetricType` and pushed to
 * `/health-data/import-json/bluetooth`, so BLE devices flow into the same
 * pipeline and appear under "Dispozitive detectate".
 *
 * Heart Rate (0x2A37) is parsed here as the reference profile; the other
 * standard GATT profiles (Blood Pressure 0x2A35, Glucose 0x2A18, Weight 0x2A9D,
 * PLX 0x2A5E — all IEEE-11073 SFLOAT) are added and validated on real hardware.
 * BLE only runs inside the native app.
 */

const HEART_RATE_SERVICE = "0000180d-0000-1000-8000-00805f9b34fb";
const HEART_RATE_MEASUREMENT = "00002a37-0000-1000-8000-00805f9b34fb";

// Standard health services we surface in the device picker.
const HEALTH_SERVICES = [
  HEART_RATE_SERVICE,
  "00001810-0000-1000-8000-00805f9b34fb", // Blood Pressure
  "00001808-0000-1000-8000-00805f9b34fb", // Glucose
  "0000181d-0000-1000-8000-00805f9b34fb", // Weight Scale
  "00001822-0000-1000-8000-00805f9b34fb", // Pulse Oximeter
];

async function ble() {
  const mod = await import("@capacitor-community/bluetooth-le");
  return mod.BleClient;
}

/** True only inside the native app with BLE support initialized. */
export async function bluetoothAvailable(): Promise<boolean> {
  if (!(await isNative())) return false;
  try {
    const BleClient = await ble();
    await BleClient.initialize({ androidNeverForLocation: true });
    return true;
  } catch {
    return false;
  }
}

function parseHeartRate(v: DataView): number | null {
  const flags = v.getUint8(0);
  const value = flags & 0x1 ? v.getUint16(1, true) : v.getUint8(1);
  return Number.isFinite(value) ? value : null;
}

/**
 * Show the native device picker, connect to the chosen health device, read one
 * measurement, and push it to the backend. Resolves with the import result.
 */
export async function connectHealthDevice(): Promise<HealthImportResult> {
  const BleClient = await ble();
  await BleClient.initialize({ androidNeverForLocation: true });

  const device = await BleClient.requestDevice({
    services: [HEART_RATE_SERVICE],
    optionalServices: HEALTH_SERVICES,
  });
  await BleClient.connect(device.deviceId);

  try {
    const bpm = await new Promise<number | null>((resolve) => {
      let done = false;
      const finish = (val: number | null) => {
        if (done) return;
        done = true;
        resolve(val);
      };
      const timer = setTimeout(() => finish(null), 8000);
      BleClient.startNotifications(
        device.deviceId,
        HEART_RATE_SERVICE,
        HEART_RATE_MEASUREMENT,
        (v: DataView) => {
          clearTimeout(timer);
          finish(parseHeartRate(v));
        },
      ).catch(() => {
        clearTimeout(timer);
        finish(null);
      });
    });

    if (bpm == null) {
      throw new Error("Nu am putut citi o măsurătoare de la dispozitiv.");
    }

    return await api.post<HealthImportResult>(
      "/health-data/import-json/bluetooth",
      {
        samples: [
          {
            type: "heart_rate",
            value: bpm,
            unit: "bpm",
            recorded_at: new Date().toISOString(),
          },
        ],
        devices: [
          {
            name: device.name || "Dispozitiv Bluetooth",
            metrics: ["heart_rate"],
          },
        ],
      },
    );
  } finally {
    try {
      await BleClient.stopNotifications(
        device.deviceId,
        HEART_RATE_SERVICE,
        HEART_RATE_MEASUREMENT,
      );
    } catch {
      /* ignore */
    }
    try {
      await BleClient.disconnect(device.deviceId);
    } catch {
      /* ignore */
    }
  }
}
