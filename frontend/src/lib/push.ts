"use client";

import { useEffect } from "react";
import { api } from "@/lib/api";
import { isNative } from "@/lib/native";

/**
 * Register the device for push notifications on the native apps.
 *
 * Uses Capacitor's `@capacitor/push-notifications` plugin, resolved via
 * `registerPlugin` (no hard npm dependency; web build unaffected). On launch it
 * requests permission, registers with FCM/APNs and sends the device token to
 * `POST /notifications/push-token`. No-op on the web.
 */
export function usePushRegistration(): void {
  useEffect(() => {
    let remove: (() => void) | undefined;
    (async () => {
      if (!(await isNative())) return;
      try {
        const { registerPlugin, Capacitor } = await import("@capacitor/core");
        const Push = registerPlugin<any>("PushNotifications");

        const perm = await Push.requestPermissions?.();
        if (perm && perm.receive !== "granted") return;

        const handle = await Push.addListener?.(
          "registration",
          async (t: { value: string }) => {
            try {
              await api.post("/notifications/push-token", {
                token: t.value,
                platform: Capacitor.getPlatform(),
              });
            } catch {
              /* ignore */
            }
          },
        );
        remove = () => handle?.remove?.();
        await Push.register?.();
      } catch {
        /* plugin unavailable */
      }
    })();
    return () => remove?.();
  }, []);
}

/** Send a test push to the current user's registered devices. */
export async function sendTestPush(): Promise<{delivered: number; simulated: number; failed: number; devices: number}> {
  return api.post("/notifications/test-push");
}

export function pushDeliveryMessage(n: {delivered: number; simulated: number; failed: number}): string {
  if (n.simulated > 0) return `Simulare locală pentru ${n.simulated} dispozitiv(e). Nu s-a trimis nicio notificare reală.`;
  if (n.delivered > 0) return `Serviciul a acceptat notificarea pentru ${n.delivered} dispozitiv(e). Afișarea pe telefon nu este confirmată.${n.failed ? ` ${n.failed} încercări au eșuat.` : ""}`;
  if (n.failed > 0) return "Trimiterea nu a reușit. Dispozitivele au fost păstrate pentru reîncercare.";
  return "Niciun dispozitiv înregistrat (deschide aplicația pe telefon și acceptă notificările).";
}
