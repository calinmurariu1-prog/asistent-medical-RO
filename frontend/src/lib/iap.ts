"use client";

import { api } from "@/lib/api";
import { isNative } from "@/lib/native";
import type { PlanId, Subscription } from "@/lib/types";

/**
 * In-App Purchase bridge for the native (Capacitor) build.
 *
 * Uses `cordova-plugin-purchase` (v13, exposed as `window.CdvPurchase`) so there
 * is no hard npm dependency and the web bundle is unaffected. On the web this
 * module reports IAP as unavailable. After a native purchase, the store token is
 * sent to `POST /billing/iap/verify`, which validates it with Apple/Google.
 *
 * Install on the native side (see docs/BILLING.md):
 *   npm i cordova-plugin-purchase && npx cap sync
 */

// Store product IDs — must match the backend `IAP_PRODUCTS` mapping.
export const PRODUCT_IDS: Record<Exclude<PlanId, "free">, string> = {
  premium: "premium_monthly",
  family: "family_monthly",
};

type Platform = "apple" | "google";

interface Cdv {
  store: any;
  ProductType: { PAID_SUBSCRIPTION: string };
  Platform: { APPLE_APPSTORE: string; GOOGLE_PLAY: string };
}

function cdv(): Cdv | null {
  return (typeof window !== "undefined" && (window as any).CdvPurchase) || null;
}

async function platform(): Promise<Platform | null> {
  try {
    const { Capacitor } = await import("@capacitor/core");
    const p = Capacitor.getPlatform();
    if (p === "ios") return "apple";
    if (p === "android") return "google";
  } catch {
    /* not native */
  }
  return null;
}

/** True only inside the native shell with the purchase plugin present. */
export async function iapAvailable(): Promise<boolean> {
  return (await isNative()) && cdv() !== null && (await platform()) !== null;
}

/** Extract the store token the backend needs (StoreKit txn id / Play token). */
function extractToken(transaction: any, plat: Platform): string {
  if (plat === "apple") {
    return String(transaction?.transactionId ?? transaction?.purchaseId ?? "");
  }
  const native = transaction?.nativePurchase ?? {};
  return String(native.purchaseToken ?? transaction?.purchaseId ?? "");
}

/**
 * Present the native purchase UI for a plan and, on approval, validate the
 * receipt with the backend. Resolves with the updated subscription.
 */
export async function purchasePlan(
  plan: Exclude<PlanId, "free">,
): Promise<Subscription> {
  const lib = cdv();
  const plat = await platform();
  if (!lib || !plat) {
    throw new Error("Achizițiile în aplicație nu sunt disponibile aici.");
  }

  const productId = PRODUCT_IDS[plan];
  const storePlatform =
    plat === "apple" ? lib.Platform.APPLE_APPSTORE : lib.Platform.GOOGLE_PLAY;
  const { store } = lib;

  return new Promise<Subscription>((resolve, reject) => {
    let settled = false;
    const done = (fn: () => void) => {
      if (settled) return;
      settled = true;
      fn();
    };

    store.register([
      { id: productId, type: lib.ProductType.PAID_SUBSCRIPTION, platform: storePlatform },
    ]);

    store
      .when()
      .approved(async (transaction: any) => {
        try {
          const sub = await api.post<Subscription>("/billing/iap/verify", {
            platform: plat,
            product_id: productId,
            token: extractToken(transaction, plat),
          });
          transaction.finish();
          done(() => resolve(sub));
        } catch (err) {
          done(() => reject(err));
        }
      });

    store
      .initialize([storePlatform])
      .then(() => {
        const offer = store.get(productId, storePlatform)?.getOffer();
        if (!offer) throw new Error("Produsul nu este disponibil în magazin.");
        return store.order(offer);
      })
      .catch((err: unknown) => done(() => reject(err)));
  });
}
