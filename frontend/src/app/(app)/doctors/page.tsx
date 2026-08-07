"use client";

import { useEffect, useState } from "react";
import { MapPin, Navigation, Phone, Star } from "lucide-react";
import { api } from "@/lib/api";
import type { NearbyProviders, SpecialtySuggestion } from "@/lib/types";
import { Badge, Button, Card, Input, Spinner } from "@/components/ui";

export default function DoctorsPage() {
  const [specialties, setSpecialties] = useState<SpecialtySuggestion[]>([]);
  const [specialty, setSpecialty] = useState<string>("");
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [city, setCity] = useState("");
  const [radius, setRadius] = useState(5000);
  const [sort, setSort] = useState<"distance" | "score">("distance");
  const [data, setData] = useState<NearbyProviders | null>(null);
  const [loading, setLoading] = useState(false);
  const [geoState, setGeoState] = useState<"idle" | "asking" | "denied" | "ok">("idle");

  const mapsKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY;

  function scoreTone(score: number | null): "green" | "blue" | "amber" | "neutral" {
    if (score == null) return "neutral";
    if (score >= 85) return "green";
    if (score >= 70) return "blue";
    if (score >= 55) return "amber";
    return "neutral";
  }

  useEffect(() => {
    api
      .get<SpecialtySuggestion[]>("/providers/suggested-specialties")
      .then((s) => {
        setSpecialties(s);
        if (s.length) setSpecialty(s[0].specialty);
      })
      .catch(() => {});
  }, []);

  function useMyLocation() {
    if (!navigator.geolocation) {
      setGeoState("denied");
      return;
    }
    setGeoState("asking");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        setGeoState("ok");
      },
      () => setGeoState("denied"),
      { enableHighAccuracy: true, timeout: 8000 },
    );
  }

  async function search(sortArg: "distance" | "score" = sort) {
    if (!coords && !city.trim()) return;
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (coords) {
        params.set("lat", String(coords.lat));
        params.set("lng", String(coords.lng));
      } else {
        params.set("city", city.trim());
      }
      if (specialty) params.set("specialty", specialty);
      params.set("radius_m", String(radius));
      params.set("sort", sortArg);
      setData(await api.get<NearbyProviders>(`/providers/nearby?${params}`));
    } finally {
      setLoading(false);
    }
  }

  function changeSort(s: "distance" | "score") {
    setSort(s);
    if (data) search(s);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Găsește medici în apropiere</h1>
      <p className="text-muted -mt-3 text-sm">
        Pe baza problemelor detectate în dosarul tău, îți sugerăm specialitatea
        potrivită și medici din raza aleasă.
      </p>

      <Card className="space-y-4">
        {specialties.length > 0 && (
          <div>
            <div className="mb-2 text-sm font-medium">Specialitate sugerată</div>
            <div className="flex flex-wrap gap-2">
              {specialties.map((s) => (
                <button
                  key={s.specialty}
                  onClick={() => setSpecialty(s.specialty)}
                  className={`rounded-full border px-3 py-1 text-sm transition ${
                    specialty === s.specialty
                      ? "brand-gradient border-transparent text-white"
                      : "border-border hover:bg-bg"
                  }`}
                  title={s.reasons.join(" ")}
                >
                  {s.specialty}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="flex flex-wrap items-end gap-3">
          <div>
            <div className="mb-1 text-sm font-medium">Locație</div>
            <Button variant="outline" onClick={useMyLocation}>
              <Navigation size={16} />
              {geoState === "ok" ? "Locație obținută ✓" : "Folosește locația mea"}
            </Button>
          </div>
          <div className="flex-1 min-w-[180px]">
            <div className="mb-1 text-sm font-medium text-muted">sau oraș</div>
            <Input
              placeholder="ex. București"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              disabled={!!coords}
            />
          </div>
          <label className="text-sm">
            <div className="mb-1 font-medium">Rază</div>
            <select
              value={radius}
              onChange={(e) => setRadius(Number(e.target.value))}
              className="rounded-lg border border-border bg-surface px-3 py-2 text-sm"
            >
              <option value={2000}>2 km</option>
              <option value={5000}>5 km</option>
              <option value={10000}>10 km</option>
              <option value={25000}>25 km</option>
            </select>
          </label>
          <Button onClick={() => search()} disabled={loading || (!coords && !city.trim())}>
            <MapPin size={16} /> Caută
          </Button>
        </div>
        {geoState === "denied" && (
          <p className="text-sm text-amber-600">
            Nu am putut accesa locația. Scrie orașul manual.
          </p>
        )}
        <p className="text-xs text-muted">
          🔒 Locația ta este folosită doar pentru această căutare și nu este
          stocată.
        </p>
      </Card>

      {loading && <Spinner />}

      {data && !loading && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-sm text-muted">
              {data.results.length} rezultate pentru{" "}
              <strong className="text-fg">{data.specialty}</strong>
            </div>
            <div className="flex items-center gap-1 text-sm">
              <span className="text-muted">Sortează:</span>
              <button
                onClick={() => changeSort("distance")}
                className={`rounded-md px-2 py-1 ${sort === "distance" ? "brand-gradient text-white" : "text-muted hover:bg-bg"}`}
              >
                Distanță
              </button>
              <button
                onClick={() => changeSort("score")}
                className={`rounded-md px-2 py-1 ${sort === "score" ? "brand-gradient text-white" : "text-muted hover:bg-bg"}`}
              >
                Scor
              </button>
            </div>
          </div>

          {mapsKey && (
            <div className="overflow-hidden rounded-2xl border border-border">
              <iframe
                title="Hartă medici"
                width="100%"
                height="320"
                style={{ border: 0 }}
                loading="lazy"
                referrerPolicy="no-referrer-when-downgrade"
                src={`https://www.google.com/maps/embed/v1/search?key=${mapsKey}&q=${encodeURIComponent(
                  data.specialty,
                )}&center=${data.center.lat},${data.center.lng}&zoom=13`}
              />
            </div>
          )}

          {data.results.map((p, i) => (
            <Card key={p.place_id || i} className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-start gap-4">
                {p.score != null && (
                  <div className="text-center">
                    <div className="text-2xl font-bold brand-text-gradient tnum">
                      {p.score}%
                    </div>
                    <Badge tone={scoreTone(p.score)}>{p.score_label}</Badge>
                  </div>
                )}
                <div>
                  <div className="font-semibold">{p.name}</div>
                  <div className="text-sm text-muted">{p.address}</div>
                  <div className="mt-1 flex items-center gap-3 text-sm">
                    {p.distance_km != null && (
                      <Badge tone="blue">{p.distance_km} km</Badge>
                    )}
                    {p.rating != null && (
                      <span className="inline-flex items-center gap-1 text-amber-500">
                        <Star size={14} fill="currentColor" /> {p.rating}
                        {p.ratings_total != null && (
                          <span className="text-muted"> ({p.ratings_total})</span>
                        )}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                {p.phone && (
                  <a href={`tel:${p.phone}`}>
                    <Button variant="outline">
                      <Phone size={16} /> Sună
                    </Button>
                  </a>
                )}
                {p.maps_url && (
                  <a href={p.maps_url} target="_blank" rel="noopener noreferrer">
                    <Button variant="outline">
                      <MapPin size={16} /> Hartă
                    </Button>
                  </a>
                )}
              </div>
            </Card>
          ))}
          <p className="text-xs text-muted">
            Scorul (0–100%) combină ratingul cu numărul de recenzii — este un
            ajutor de orientare, nu o garanție medicală. {data.disclaimer}
          </p>
        </div>
      )}
    </div>
  );
}
