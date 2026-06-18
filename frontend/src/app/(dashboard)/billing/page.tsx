"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  CreditCard, ArrowRight, ExternalLink, Sparkles, Calendar, Infinity as InfinityIcon,
} from "lucide-react";
import { GlowCard } from "@/components/cyber/glow-card";
import { useAuth } from "@/contexts/auth-context";
import { billingApi } from "@/lib/api";

function formatDate(value?: string | null): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleDateString("nl-NL", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  } catch {
    return String(value);
  }
}

const INTERVAL_LABEL: Record<string, string> = {
  month: "Maandelijks",
  monthly: "Maandelijks",
  year: "Jaarlijks",
  yearly: "Jaarlijks",
};

export default function BillingPage() {
  const { planInfo } = useAuth();
  const [loadingPortal, setLoadingPortal] = useState(false);

  const planName = String(planInfo?.plan ?? "—").toUpperCase();
  const interval = planInfo?.plan_interval
    ? INTERVAL_LABEL[planInfo.plan_interval] ?? planInfo.plan_interval
    : null;
  const unlimited = !!planInfo?.unlimited_scans;
  const used = Number(planInfo?.scans_this_month ?? 0);
  const max = Number(planInfo?.max_scans_per_month ?? 0);
  const pct = max > 0 ? Math.min(100, Math.round((used / max) * 100)) : 0;

  const openPortal = async () => {
    setLoadingPortal(true);
    try {
      const res: any = await billingApi.portal();
      const url = res?.data?.portal_url;
      if (url) {
        window.location.href = url;
        return;
      }
      toast.error(
        "Geen actief abonnement of betalingen niet geconfigureerd — neem contact op via info@scanix.nl"
      );
    } catch (err: any) {
      const status = err?.response?.status;
      if (status === 404 || status === 503) {
        toast.error(
          "Geen actief abonnement of betalingen niet geconfigureerd — neem contact op via info@scanix.nl"
        );
      } else {
        toast.error("Er ging iets mis bij het openen van het abonnementbeheer.");
      }
    } finally {
      setLoadingPortal(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-bold uppercase tracking-[0.06em] text-ink">
          Uw <span className="text-cyan">abonnement</span>
        </h1>
        <p className="mt-1 font-mono text-[12px] text-ink-muted">
          Bekijk uw huidige pakket en beheer uw betalingsgegevens.
        </p>
      </div>

      {/* Current plan card */}
      <GlowCard glowColor="#00B4D8" accentBorder="#00B4D8" className="p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-grid bg-app">
              <CreditCard className="h-5 w-5 text-cyan" />
            </span>
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-muted">
                Huidig pakket
              </p>
              <p className="font-display text-xl font-bold text-ink">{planName}</p>
            </div>
          </div>
          {interval && (
            <span className="flex items-center gap-1.5 rounded-md border border-grid bg-app px-3 py-1.5 font-mono text-[11px] text-ink-muted">
              <Calendar className="h-3.5 w-3.5" />
              {interval}
            </span>
          )}
        </div>

        <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {/* Expiry */}
          <div className="rounded-lg border border-grid bg-app p-4">
            <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-muted">
              Verloopt op
            </p>
            <p className="mt-1 font-display text-[14px] font-semibold text-ink">
              {formatDate(planInfo?.plan_expires_at)}
            </p>
          </div>

          {/* Scans usage */}
          <div className="rounded-lg border border-grid bg-app p-4">
            <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-muted">
              Scans deze maand
            </p>
            {unlimited ? (
              <p className="mt-1 flex items-center gap-1.5 font-display text-[14px] font-semibold text-neon-green">
                <InfinityIcon className="h-4 w-4" /> Onbeperkt
              </p>
            ) : (
              <>
                <p className="mt-1 font-display text-[14px] font-semibold text-ink">
                  {used} van {max} gebruikt
                </p>
                <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-grid">
                  <div
                    className="h-full rounded-full bg-cyan transition-all duration-300"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </>
            )}
          </div>
        </div>

        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <motion.button
            type="button"
            onClick={openPortal}
            disabled={loadingPortal}
            whileHover={{ scale: loadingPortal ? 1 : 1.02 }}
            whileTap={{ scale: loadingPortal ? 1 : 0.98 }}
            className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-cyan px-4 py-2.5 font-display text-[12px] font-bold uppercase tracking-[0.1em] text-app shadow-glow-cyan transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {loadingPortal ? "Bezig..." : "Beheer abonnement"}
            {!loadingPortal && <ExternalLink className="h-4 w-4" />}
          </motion.button>

          <Link
            href="https://scanix.nl/prijzen"
            target="_blank"
            rel="noopener noreferrer"
            className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-grid bg-card2 px-4 py-2.5 font-mono text-[12px] uppercase tracking-[0.1em] text-ink-muted transition-colors duration-150 hover:border-cyan/50 hover:text-cyan"
          >
            <Sparkles className="h-4 w-4" /> Upgrade pakket <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </GlowCard>

      <p className="text-center font-mono text-[11px] text-ink-muted">
        Vragen over uw abonnement? Mail naar{" "}
        <a href="mailto:info@scanix.nl" className="text-cyan hover:underline">
          info@scanix.nl
        </a>
      </p>
    </div>
  );
}
