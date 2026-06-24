"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Zap, ArrowRight, Check, Infinity as InfinityIcon, Star, ShieldCheck,
  Lock, Sparkles, CreditCard,
} from "lucide-react";
import { GlowCard } from "@/components/cyber/glow-card";
import { billingApi, type CreditsBalance, type CreditPurchase } from "@/lib/api";

// ── Credit packages (mirrors backend CREDIT_PACKAGES) ───────────────────────────
type Pkg = {
  key: string;
  name: string;
  credits: number;
  price: number; // eurocents
  perScan: number; // euros
  save?: string;
  popular?: boolean;
};

const PACKAGES: Pkg[] = [
  { key: "kennismaking", name: "Kennismaking", credits: 1, price: 4900, perScan: 49 },
  { key: "starter", name: "Starter", credits: 3, price: 11900, perScan: 40, save: "Bespaar €28" },
  { key: "groei", name: "Groei", credits: 10, price: 34900, perScan: 35, save: "Bespaar €141", popular: true },
  { key: "pro", name: "Pro", credits: 25, price: 74900, perScan: 30, save: "Bespaar €476" },
];

const SUBSCRIPTIONS = [
  { name: "Business", price: "€199/mnd", perks: ["Onbeperkt scans", "5 targets", "Geplande scans"] },
  { name: "Enterprise", price: "€599/mnd", perks: ["Onbeperkt scans", "20 targets", "White-label"] },
];

function euro(cents: number): string {
  return `€${(cents / 100).toLocaleString("nl-NL")}`;
}

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

  const { data: balance } = useQuery<CreditsBalance>({
    queryKey: ["credits-balance"],
    queryFn: () => billingApi.creditsBalance().then((r) => r.data),
    retry: false,
  });

  const { data: history } = useQuery<CreditPurchase[]>({
    queryKey: ["credit-history"],
    queryFn: () => billingApi.history().then((r) => r.data),
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

      {/* ── Sectie 1: huidig saldo ── */}
      <GlowCard glowColor="#00B4D8" className="p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <span className="flex h-12 w-12 items-center justify-center rounded-lg border border-cyan/40 bg-cyan/10">
              <Zap className="h-6 w-6 text-cyan" fill="currentColor" />
            </span>
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-muted">Uw saldo</p>
              {unlimited ? (
                <p className="flex items-center gap-1.5 font-display text-2xl font-bold text-violet-300">
                  <InfinityIcon className="h-6 w-6" /> Onbeperkt
                </p>
              ) : (
                <p className="font-display text-2xl font-bold text-ink">
                  {remaining} <span className="text-base font-medium text-ink-muted">credits</span>
                </p>
              )}
            </div>
          </div>
          <div className="text-right">
            <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-muted">Totaal ooit gekocht</p>
            <p className="font-display text-lg font-semibold text-ink">{total}</p>
          </div>
        </div>

        {!unlimited && remaining <= 0 && (
          <div className="mt-4 flex items-center gap-2 rounded-lg border border-neon-red/50 bg-neon-red/10 px-4 py-3 font-mono text-[12px] text-neon-red">
            <Zap className="h-4 w-4" fill="currentColor" />
            U heeft geen credits meer. Koop hieronder een pakket om verder te gaan.
          </div>
        )}
      </GlowCard>

      {/* ── Sectie 2: credit pakketten ── */}
      <div>
        <h2 className="mb-4 font-display text-lg font-bold text-ink">Koop credits</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {PACKAGES.map((p) => (
            <div
              key={p.key}
              className={`relative flex flex-col rounded-xl border bg-card2 p-5 ${
                p.popular ? "border-cyan/60 shadow-glow-cyan" : "border-grid"
              }`}
            >
              {p.popular && (
                <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 inline-flex items-center gap-1 rounded-full bg-cyan px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-app">
                  <Star className="h-3 w-3" fill="currentColor" /> Meest gekozen
                </span>
              )}
              <p className="font-display text-[15px] font-bold text-ink">{p.name}</p>
              <div className="mt-3 flex items-end gap-1">
                <span className="font-display text-3xl font-bold text-ink">{euro(p.price)}</span>
              </div>
              <div className="mt-3 flex items-center gap-1.5 font-mono text-[13px] text-cyan">
                <Zap className="h-3.5 w-3.5" fill="currentColor" />
                {p.credits} {p.credits === 1 ? "credit" : "credits"}
              </div>
              <p className="mt-1 font-mono text-[11px] text-ink-muted">€{p.perScan} per scan</p>
              {p.save && (
                <p className="mt-2 inline-flex w-fit rounded-md bg-neon-green/10 px-2 py-0.5 font-mono text-[10px] font-semibold text-neon-green">
                  {p.save}
                </p>
              )}
              <p className="mt-2 inline-flex w-fit items-center gap-1 font-mono text-[10px] text-ink-muted">
                <Check className="h-3 w-3 text-neon-green" /> Verlopen nooit
              </p>

              <button
                type="button"
                onClick={() => buy(p.key)}
                disabled={buying !== null}
                className={`mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5 font-display text-[12px] font-bold uppercase tracking-[0.1em] transition-all active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60 ${
                  p.popular
                    ? "bg-cyan text-app shadow-glow-cyan hover:scale-[1.02]"
                    : "border border-grid bg-app text-ink hover:border-cyan/50 hover:text-cyan"
                }`}
              >
                {buying === p.key ? "Bezig…" : <>Koop nu <ArrowRight className="h-4 w-4" /></>}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* ── Sectie 3: abonnementen ── */}
      <div>
        <h2 className="font-display text-lg font-bold text-ink">Abonnementen</h2>
        <p className="mb-4 mt-1 font-mono text-[12px] text-ink-muted">Voor intensieve gebruikers.</p>
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
                href="https://scanix.nl/contact"
                target="_blank"
                rel="noopener noreferrer"
                className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-grid bg-app px-4 py-2.5 font-mono text-[12px] uppercase tracking-[0.1em] text-ink-muted transition-colors hover:border-cyan/50 hover:text-cyan"
              >
                <Sparkles className="h-4 w-4" /> Neem contact op
              </Link>
            </div>
          ))}
        </div>
      </div>

      {/* ── Sectie 4: aankoopgeschiedenis ── */}
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
                    <td className="px-4 py-3 font-mono text-[12px] tabular-nums text-cyan">{h.credits}</td>
                    <td className="px-4 py-3 font-mono text-[12px] tabular-nums text-ink">
                      {h.price_paid > 0 ? euro(h.price_paid) : "Gratis"}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex rounded-full bg-neon-green/10 px-2 py-0.5 font-mono text-[10px] font-semibold uppercase text-neon-green">
                        {h.status}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Trust footer */}
      <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 border-t border-grid pt-6 font-mono text-[11px] text-ink-muted">
        <span className="inline-flex items-center gap-1.5"><ShieldCheck className="h-3.5 w-3.5 text-cyan" /> Veilig via Stripe</span>
        <span className="inline-flex items-center gap-1.5"><Lock className="h-3.5 w-3.5 text-cyan" /> AVG-compliant, data in EU</span>
        <span className="inline-flex items-center gap-1.5"><CreditCard className="h-3.5 w-3.5 text-cyan" /> Geen verborgen kosten</span>
      </div>
    </div>
  );
}
