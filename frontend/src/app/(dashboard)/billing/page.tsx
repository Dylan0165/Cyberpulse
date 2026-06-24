"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Zap, ArrowRight, Check, Infinity as InfinityIcon, Star, ShieldCheck,
  Lock, Sparkles, CreditCard, Crown,
} from "lucide-react";
import { GlowCard } from "@/components/cyber/glow-card";
import { billingApi, type CreditPackage, type CreditPurchase } from "@/lib/api";
import { useCredits, formatEuroCents, formatEuroWhole } from "@/hooks/useCredits";

const SUBSCRIPTIONS = [
  { name: "Business", price: "€199/mnd", perks: ["Onbeperkt scans", "5 targets", "Geplande scans"] },
  { name: "Enterprise", price: "€599/mnd", perks: ["Onbeperkt scans", "20 targets", "White-label"] },
];

function formatDate(value?: string | null): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleDateString("nl-NL", { day: "numeric", month: "short", year: "numeric" });
  } catch {
    return String(value);
  }
}

export default function BillingPage() {
  const qc = useQueryClient();
  const [buying, setBuying] = useState<string | null>(null);
  const { balance } = useCredits();

  const { data: history } = useQuery<CreditPurchase[]>({
    queryKey: ["credit-history"],
    queryFn: () => billingApi.creditsHistory().then((r) => r.data),
    retry: false,
  });

  // Handle Stripe success/cancel redirects (read from the URL, no Suspense needed).
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("success") === "true") {
      toast.success("Credits toegevoegd! Uw saldo is bijgewerkt.");
      qc.invalidateQueries({ queryKey: ["credits-balance"] });
      qc.invalidateQueries({ queryKey: ["credit-history"] });
      window.history.replaceState({}, "", "/billing");
    } else if (params.get("cancelled") === "true") {
      toast("Betaling geannuleerd");
      window.history.replaceState({}, "", "/billing");
    }
  }, [qc]);

  const unlimited = !!balance?.is_unlimited;
  const remaining = unlimited ? Infinity : Number(balance?.credits_remaining ?? 0);
  const total = Number(balance?.credits_total ?? 0);
  const packages: CreditPackage[] = balance?.packages ?? [];
  const progress = total > 0 && !unlimited ? Math.min(100, Math.round((remaining / total) * 100)) : 0;

  // Balance colour-coding: green 3+, orange 1-2, red 0, purple unlimited.
  const balanceTone = unlimited
    ? "text-violet-300"
    : remaining >= 3
    ? "text-neon-green"
    : remaining >= 1
    ? "text-neon-orange"
    : "text-neon-red";

  const buy = async (pkg: string) => {
    if (buying) return;
    setBuying(pkg);
    try {
      const { data } = await billingApi.buyCredits(pkg);
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
        return;
      }
      toast.error("Betaling kon niet worden gestart.");
    } catch (err: any) {
      const status = err?.response?.status;
      if (status === 503) {
        toast.error("Betalingen zijn nog niet geconfigureerd — mail info@scanix.nl");
      } else {
        toast.error("Er ging iets mis bij het starten van de betaling.");
      }
    } finally {
      setBuying(null);
    }
  };

  return (
    <div className="mx-auto w-full max-w-5xl space-y-8">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-bold uppercase tracking-[0.06em] text-ink">
          Scan <span className="text-cyan">credits</span>
        </h1>
        <p className="mt-1 font-mono text-[12px] text-ink-muted">
          Betaal per scan. 1 credit = 1 scan. Credits verlopen nooit.
        </p>
      </div>

      {/* Rode banner bij 0 credits */}
      {!unlimited && remaining <= 0 && (
        <div className="flex items-center gap-2 rounded-lg border border-neon-red/50 bg-neon-red/10 px-4 py-3 font-mono text-[12px] font-semibold text-neon-red">
          <Zap className="h-4 w-4" fill="currentColor" />
          U heeft geen credits meer. Koop credits om door te gaan met scannen.
        </div>
      )}

      {/* ── Sectie 1: huidig saldo (sticky) ── */}
      <div className="sticky top-2 z-10">
        <GlowCard glowColor={remaining <= 0 && !unlimited ? "#FF3B5C" : "#00B4D8"} className="p-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <span className={`flex h-12 w-12 items-center justify-center rounded-lg border ${
                unlimited ? "border-violet-400/40 bg-violet-400/10" : "border-cyan/40 bg-cyan/10"
              } ${remaining <= 0 && !unlimited ? "animate-pulse" : ""}`}>
                {unlimited ? <InfinityIcon className="h-6 w-6 text-violet-300" /> : <Zap className="h-6 w-6 text-cyan" fill="currentColor" />}
              </span>
              <div>
                <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-muted">Beschikbaar</p>
                {unlimited ? (
                  <p className="flex items-center gap-1.5 font-display text-2xl font-bold text-violet-300">
                    <InfinityIcon className="h-6 w-6" /> Onbeperkt
                  </p>
                ) : (
                  <p className={`font-display text-2xl font-bold ${balanceTone} ${remaining <= 0 ? "animate-pulse" : ""}`}>
                    {remaining} <span className="text-base font-medium text-ink-muted">credits</span>
                  </p>
                )}
              </div>
            </div>
            <div className="text-right">
              <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-muted">Totaal ooit gekocht</p>
              <p className="font-display text-lg font-semibold text-ink">{total} credits</p>
            </div>
          </div>

          {/* Progressiebalk */}
          {!unlimited && total > 0 && (
            <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-card2">
              <div
                className={`h-full rounded-full transition-all ${remaining >= 3 ? "bg-neon-green" : remaining >= 1 ? "bg-neon-orange" : "bg-neon-red"}`}
                style={{ width: `${progress}%` }}
              />
            </div>
          )}
        </GlowCard>
      </div>

      {/* ── Sectie 2: credits bijkopen ── */}
      <div>
        <h2 className="font-display text-lg font-bold text-ink">Credits bijkopen</h2>
        <p className="mb-4 mt-1 font-mono text-[12px] text-ink-muted">
          Eenmalige betaling — credits verlopen nooit.
        </p>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {packages.map((p) => {
            const isGold = p.key === "expert";
            const isPopular = p.popular;
            return (
              <div
                key={p.key}
                className={`relative flex flex-col rounded-xl border p-5 ${
                  isPopular
                    ? "border-cyan/60 bg-cyan/[0.04] shadow-glow-cyan"
                    : isGold
                    ? "border-amber-400/50 bg-amber-400/[0.03]"
                    : "border-grid bg-card2"
                }`}
              >
                {isPopular && (
                  <span className="absolute -top-2.5 left-1/2 inline-flex -translate-x-1/2 items-center gap-1 rounded-full bg-cyan px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-app">
                    <Star className="h-3 w-3" fill="currentColor" /> Meest gekozen
                  </span>
                )}
                {isGold && (
                  <span className="absolute -top-2.5 left-1/2 inline-flex -translate-x-1/2 items-center gap-1 rounded-full bg-amber-400 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-app">
                    <Crown className="h-3 w-3" fill="currentColor" /> Beste waarde
                  </span>
                )}
                <p className="font-display text-[15px] font-bold text-ink">{p.label}</p>
                <div className="mt-3 flex items-center gap-1.5 font-mono text-[13px] text-cyan">
                  <Zap className="h-3.5 w-3.5" fill="currentColor" />
                  {p.credits} {p.credits === 1 ? "credit" : "credits"}
                </div>
                <div className="mt-3">
                  <span className="font-display text-3xl font-bold text-ink">{formatEuroWhole(p.price)}</span>
                </div>
                <p className="mt-1 font-mono text-[11px] text-ink-muted">{formatEuroWhole(p.price_per_scan)} per scan</p>
                {p.savings > 0 ? (
                  <p className="mt-2 inline-flex w-fit rounded-md bg-neon-green/10 px-2 py-0.5 font-mono text-[10px] font-semibold text-neon-green">
                    Bespaar {formatEuroWhole(p.savings)}
                  </p>
                ) : (
                  <p className="mt-2 inline-flex w-fit items-center gap-1 font-mono text-[10px] text-ink-muted">
                    <Check className="h-3 w-3 text-neon-green" /> Verlopen nooit
                  </p>
                )}

                <button
                  type="button"
                  onClick={() => buy(p.key)}
                  disabled={buying !== null}
                  className={`mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5 font-display text-[12px] font-bold uppercase tracking-[0.1em] transition-all active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60 ${
                    isPopular
                      ? "bg-cyan text-app shadow-glow-cyan hover:scale-[1.02]"
                      : isGold
                      ? "bg-amber-400 text-app hover:scale-[1.02]"
                      : "border border-grid bg-app text-ink hover:border-cyan/50 hover:text-cyan"
                  }`}
                >
                  {buying === p.key ? "Bezig…" : <>Koop nu <ArrowRight className="h-4 w-4" /></>}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Sectie 3: aankoopgeschiedenis ── */}
      <div>
        <h2 className="mb-4 font-display text-lg font-bold text-ink">Aankoopgeschiedenis</h2>
        <div className="overflow-x-auto rounded-xl border border-grid">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-grid bg-card2">
                {["Datum", "Pakket", "Credits", "Bedrag", "Status"].map((h) => (
                  <th key={h} className="px-4 py-3 font-mono text-[10px] uppercase tracking-wider text-ink-muted">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(history ?? []).length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center font-mono text-[12px] text-ink-muted">
                    Nog geen aankopen.
                  </td>
                </tr>
              ) : (
                (history ?? []).map((h) => (
                  <tr key={h.id} className="border-b border-grid/60">
                    <td className="px-4 py-3 font-mono text-[12px] text-ink-muted">{formatDate(h.created_at)}</td>
                    <td className="px-4 py-3 font-mono text-[12px] text-ink">{h.package_name}</td>
                    <td className="px-4 py-3 font-mono text-[12px] tabular-nums text-cyan">{h.credits_purchased}</td>
                    <td className="px-4 py-3 font-mono text-[12px] tabular-nums text-ink">
                      {h.price_paid > 0 ? formatEuroCents(h.price_paid) : "Gratis"}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex rounded-full bg-neon-green/10 px-2 py-0.5 font-mono text-[10px] font-semibold uppercase text-neon-green">
                        Voltooid
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Sectie 4: abonnementen (klein) ── */}
      <div>
        <h2 className="font-display text-base font-bold text-ink">Voor intensieve gebruikers</h2>
        <p className="mb-4 mt-1 font-mono text-[12px] text-ink-muted">Dagelijks scannen? Kijk naar onze abonnementen.</p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {SUBSCRIPTIONS.map((s) => (
            <div key={s.name} className="flex flex-col rounded-xl border border-grid bg-card2 p-5">
              <div className="flex items-center justify-between">
                <p className="font-display text-[15px] font-bold text-ink">{s.name}</p>
                <span className="font-display text-lg font-bold text-cyan">{s.price}</span>
              </div>
              <ul className="mt-3 space-y-1.5">
                {s.perks.map((perk) => (
                  <li key={perk} className="flex items-center gap-2 font-mono text-[12px] text-ink-muted">
                    <Check className="h-3.5 w-3.5 text-neon-green" /> {perk}
                  </li>
                ))}
              </ul>
              <Link
                href="mailto:info@scanix.nl"
                className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-grid bg-app px-4 py-2.5 font-mono text-[12px] uppercase tracking-[0.1em] text-ink-muted transition-colors hover:border-cyan/50 hover:text-cyan"
              >
                <Sparkles className="h-4 w-4" /> Neem contact op
              </Link>
            </div>
          ))}
        </div>
      </div>

      {/* Trust footer */}
      <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 border-t border-grid pt-6 font-mono text-[11px] text-ink-muted">
        <span className="inline-flex items-center gap-1.5"><ShieldCheck className="h-3.5 w-3.5 text-cyan" /> Veilig via Stripe (iDEAL &amp; kaart)</span>
        <span className="inline-flex items-center gap-1.5"><Lock className="h-3.5 w-3.5 text-cyan" /> AVG-compliant, data in EU</span>
        <span className="inline-flex items-center gap-1.5"><CreditCard className="h-3.5 w-3.5 text-cyan" /> Geen verborgen kosten</span>
      </div>
    </div>
  );
}
