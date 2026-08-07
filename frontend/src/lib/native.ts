"use client";

import { useEffect } from "react";

/**
 * Native-shell integration for the Capacitor (Android/iOS) build.
 *
 * Everything is guarded by `Capacitor.isNativePlatform()` and dynamically
 * imported, so on the web it does nothing and adds no runtime cost.
 */
export function useNativeShell(): void {
  useEffect(() => {
    let cleanup: (() => void) | undefined;

    (async () => {
      try {
        const { Capacitor } = await import("@capacitor/core");
        if (!Capacitor.isNativePlatform()) return;

        const { StatusBar, Style } = await import("@capacitor/status-bar");
        StatusBar.setStyle({ style: Style.Default }).catch(() => {});

        const { App } = await import("@capacitor/app");
        const handle = await App.addListener("backButton", ({ canGoBack }) => {
          if (canGoBack) window.history.back();
          else App.exitApp();
        });
        cleanup = () => handle.remove();
      } catch {
        /* not running natively, or plugins unavailable */
      }
    })();

    return () => cleanup?.();
  }, []);
}

/** True when running inside the native Capacitor shell (safe on server/web). */
export async function isNative(): Promise<boolean> {
  try {
    const { Capacitor } = await import("@capacitor/core");
    return Capacitor.isNativePlatform();
  } catch {
    return false;
  }
}
