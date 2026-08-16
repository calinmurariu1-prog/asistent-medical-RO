"use client";

// Loads the Google Maps JavaScript API once and resolves when ready.
// Uses a public browser key (NEXT_PUBLIC_GOOGLE_MAPS_KEY) restricted by
// HTTP referrer (web) / app package (Android). Distinct from the server key.

/* eslint-disable @typescript-eslint/no-explicit-any */
type GMaps = any;

let loadPromise: Promise<GMaps> | null = null;

export function loadGoogleMaps(apiKey: string): Promise<GMaps> {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("Google Maps needs a browser"));
  }
  const w = window as any;
  if (w.google?.maps) return Promise.resolve(w.google.maps);
  if (loadPromise) return loadPromise;

  loadPromise = new Promise<GMaps>((resolve, reject) => {
    const cbName = "__amGmapsInit";
    w[cbName] = () => resolve(w.google.maps);
    const s = document.createElement("script");
    s.src =
      `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}` +
      `&callback=${cbName}&language=ro&region=RO`;
    s.async = true;
    s.defer = true;
    s.onerror = () => {
      loadPromise = null;
      reject(new Error("Google Maps failed to load"));
    };
    document.head.appendChild(s);
  });
  return loadPromise;
}
