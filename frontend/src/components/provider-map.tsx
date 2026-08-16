"use client";

import { useEffect, useRef } from "react";
import type { ProviderResult } from "@/lib/types";
import { loadGoogleMaps } from "@/lib/google-maps";

/* eslint-disable @typescript-eslint/no-explicit-any */

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c] as string),
  );
}

interface Props {
  apiKey: string;
  center: { lat: number; lng: number };
  userLocation?: { lat: number; lng: number } | null;
  points: ProviderResult[];
  activeKey?: string | null;
  onSelect?: (key: string) => void;
}

/** Interactive Google map: a pin per provider + the user's location. */
export function ProviderMap({
  apiKey,
  center,
  userLocation,
  points,
  activeKey,
  onSelect,
}: Props) {
  const elRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const markersRef = useRef<Record<string, any>>({});
  const infoRef = useRef<any>(null);

  // Build / rebuild markers whenever the result set changes.
  useEffect(() => {
    let cancelled = false;
    loadGoogleMaps(apiKey)
      .then((maps) => {
        if (cancelled || !elRef.current) return;

        if (!mapRef.current) {
          mapRef.current = new maps.Map(elRef.current, {
            center,
            zoom: 13,
            mapTypeControl: false,
            streetViewControl: false,
            fullscreenControl: false,
            clickableIcons: false,
          });
          infoRef.current = new maps.InfoWindow();
        }

        // Clear previous markers.
        Object.values(markersRef.current).forEach((m: any) => m.setMap(null));
        markersRef.current = {};

        const bounds = new maps.LatLngBounds();

        if (userLocation) {
          new maps.Marker({
            position: userLocation,
            map: mapRef.current,
            title: "Locația ta",
            zIndex: 999,
            icon: {
              path: maps.SymbolPath.CIRCLE,
              scale: 7,
              fillColor: "#2563eb",
              fillOpacity: 1,
              strokeColor: "#ffffff",
              strokeWeight: 2,
            },
          });
          bounds.extend(userLocation);
        }

        points.forEach((p, i) => {
          const key = p.place_id || `${p.lat},${p.lng},${i}`;
          const marker = new maps.Marker({
            position: { lat: p.lat, lng: p.lng },
            map: mapRef.current,
            title: p.name,
          });
          marker.addListener("click", () => {
            const rating =
              p.rating != null ? `★ ${p.rating}${p.ratings_total ? ` (${p.ratings_total})` : ""}` : "";
            infoRef.current.setContent(
              `<div style="font:14px/1.4 system-ui;max-width:220px">
                 <div style="font-weight:600">${escapeHtml(p.name)}</div>
                 <div style="color:#666">${escapeHtml(p.specialty || "")}</div>
                 ${p.address ? `<div style="color:#666">${escapeHtml(p.address)}</div>` : ""}
                 ${rating ? `<div style="color:#b45309">${rating}</div>` : ""}
               </div>`,
            );
            infoRef.current.open(mapRef.current, marker);
            onSelect?.(key);
          });
          markersRef.current[key] = marker;
          bounds.extend({ lat: p.lat, lng: p.lng });
        });

        if (!bounds.isEmpty()) {
          if (points.length + (userLocation ? 1 : 0) === 1) {
            mapRef.current.setCenter(bounds.getCenter());
            mapRef.current.setZoom(15);
          } else {
            mapRef.current.fitBounds(bounds, 48);
          }
        }
      })
      .catch(() => {
        /* key missing/blocked — the list still works */
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKey, points, userLocation?.lat, userLocation?.lng]);

  // Pan to and open the marker selected from the list.
  useEffect(() => {
    const maps = (window as any).google?.maps;
    if (!maps || !mapRef.current || !activeKey) return;
    const marker = markersRef.current[activeKey];
    if (!marker) return;
    mapRef.current.panTo(marker.getPosition());
    maps.event.trigger(marker, "click");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeKey]);

  return <div ref={elRef} className="h-[320px] w-full" />;
}
