"use client";

import { useEffect, useState } from "react";
import { Check, Sparkles } from "lucide-react";
import { useFetch } from "@/lib/hooks";
import { api } from "@/lib/api";
import { iapAvailable, purchasePlan } from "@/lib/iap";
import type { Plan, PlanId, Subscription } from "@/lib/types";
import { Badge, Button, Card, Spinner } from "@/components/ui";

export default function SubscriptionPage() {
  const plans = useFetch<Plan[]>("/billing/plans");
  const sub = useFetch<Subscription>("/billing/subscription");
  const [busy, setBusy] = useState<PlanId | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [iap, setIap] = useState(false);

  useEffect(() => {
    iapAvailable().then(setIap);
  }, []);

  async function choose(plan: PlanId) {
    setBusy(plan);
    setError(null);
    try {
      if (plan !== "free" && iap) {
        // Native app: real store purchase, validated by the backend.
        await purchasePlan(plan);
      } else {
        // Web / downgrade: interim direct plan change (Stripe comes next).
        await api.post("/billing/subscription", { plan });
      }
      sub.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Operațiune eșuată");
    } finally {
      setBusy(null);
    }
  }

  const current = sub.data?.plan;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Abonament</h1>
        <p className="mt-1 text-sm text-muted">
          Alege planul potrivit. Poți schimba oricând.
        </p>
      </div>

      {sub.data && (
        <Card className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted">Planul tău curent</p>
            <p className="text-lg font-semibold">{sub.data.plan_name}</p>
          </div>
          <Badge tone={current === "free" ? "neutral" : "green"}>
            {sub.data.status}
          </Badge>
        </Card>
      )}

      {plans.loading ? (
        <Spinner />
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          {(plans.data || []).map((p) => {
            const active = current === p.plan;
            const highlight = p.plan === "premium";
            return (
              <Card
                key={p.plan}
                className={`flex flex-col ${
                  highlight ? "ring-2 ring-brand-violet" : ""
                }`}
              >
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold">{p.name}</h2>
                  {highlight && (
                    <Badge tone="blue">
                      <Sparkles size={12} /> Popular
                    </Badge>
                  )}
                </div>
                <p className="mt-1 text-sm text-muted">{p.tagline}</p>
                <p className="mt-4 text-3xl font-bold">
                  {p.price_eur_month === 0
                    ? "Gratuit"
                    : `${p.price_eur_month.toFixed(2)}€`}
                  {p.price_eur_month > 0 && (
                    <span className="text-sm font-normal text-muted">/lună</span>
                  )}
                </p>

                <ul className="mt-4 flex-1 space-y-2 text-sm">
                  {p.features.map((f) => (
                    <li key={f} className="flex items-start gap-2">
                      <Check size={16} className="mt-0.5 shrink-0 text-brand-green" />
                      {f}
                    </li>
                  ))}
                </ul>

                <Button
                  className="mt-6 w-full"
                  variant={active ? "outline" : highlight ? "primary" : "outline"}
                  disabled={active || busy !== null}
                  onClick={() => choose(p.plan)}
                >
                  {active
                    ? "Plan curent"
                    : busy === p.plan
                      ? "Se aplică…"
                      : p.price_eur_month === 0
                        ? "Treci la Gratuit"
                        : "Alege planul"}
                </Button>
              </Card>
            );
          })}
        </div>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      <p className="text-xs text-muted">
        {iap
          ? "Abonamentele se achiziționează prin App Store / Google Play și sunt validate securizat pe server."
          : "Pe telefon, abonarea se face prin App Store / Google Play. Pe web, plata cu cardul (Stripe) se activează în curând — momentan schimbarea planului este în modul de testare."}
      </p>
    </div>
  );
}
