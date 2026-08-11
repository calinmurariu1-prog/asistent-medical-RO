"use client";

import { useEffect, useState } from "react";
import { Check, CreditCard, Sparkles } from "lucide-react";
import { useFetch } from "@/lib/hooks";
import { api } from "@/lib/api";
import { iapAvailable, purchasePlan } from "@/lib/iap";
import type { Plan, PlanId, Subscription } from "@/lib/types";
import { Badge, Button, Card, PageHeader, Spinner } from "@/components/ui";

export default function SubscriptionPage() {
  const plans = useFetch<Plan[]>("/billing/plans");
  const sub = useFetch<Subscription>("/billing/subscription");
  const [busy, setBusy] = useState<PlanId | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [iap, setIap] = useState(false);

  useEffect(() => {
    iapAvailable().then(setIap);
    // Returning from Stripe Checkout — refresh the subscription.
    const params = new URLSearchParams(window.location.search);
    if (params.get("status") === "success") {
      sub.reload();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function choose(plan: PlanId) {
    setBusy(plan);
    setError(null);
    try {
      if (plan === "free") {
        // Downgrade / cancel — direct change (real cancel goes via the portal).
        await api.post("/billing/subscription", { plan });
        sub.reload();
      } else if (iap) {
        // Native app: real store purchase, validated by the backend.
        await purchasePlan(plan);
        sub.reload();
      } else {
        // Web: Stripe Checkout.
        const { url } = await api.post<{ url: string }>(
          "/billing/stripe/checkout",
          { plan },
        );
        if (url.includes("mock=1")) {
          // Stripe not configured yet — apply directly so the demo works.
          await api.post("/billing/subscription", { plan });
          sub.reload();
        } else {
          window.location.href = url; // redirect to Stripe-hosted checkout
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Operațiune eșuată");
    } finally {
      setBusy(null);
    }
  }

  async function openPortal() {
    setError(null);
    try {
      const { url } = await api.post<{ url: string }>("/billing/stripe/portal");
      if (url.includes("mock=portal")) {
        setError("Portalul de facturare se activează după configurarea Stripe.");
        return;
      }
      window.location.href = url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nu am putut deschide portalul");
    }
  }

  const current = sub.data?.plan;
  const isStripe = sub.data?.provider === "stripe";

  return (
    <div className="space-y-6">
      <PageHeader
        title="Abonament"
        subtitle="Alege planul potrivit. Poți schimba oricând."
        icon={CreditCard}
      />

      {sub.data && (
        <Card className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm text-muted">Planul tău curent</p>
            <p className="text-lg font-semibold">{sub.data.plan_name}</p>
          </div>
          <div className="flex items-center gap-3">
            {current !== "free" && isStripe && (
              <Button variant="outline" onClick={openPortal}>
                Gestionează / anulează
              </Button>
            )}
            <Badge tone={current === "free" ? "neutral" : "green"}>
              {sub.data.status}
            </Badge>
          </div>
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
          : "Pe web, plata cu cardul se face securizat prin Stripe. Pe telefon, abonarea se face prin App Store / Google Play."}
      </p>
    </div>
  );
}
