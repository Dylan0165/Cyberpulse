"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  ShieldCheck, ArrowRight, Check, Minus, Cpu, Sparkles, FileText, Server,
} from "lucide-react";

const BASE_PER_TARGET = 19; // €/systeem/maand
const ADDON_CYBERPULSE = 9; // €/systeem/maand — runpod, EU-only
const ADDON_CLAUDE = 19;    // €/systeem/maand — anthropic
const NIS2_PER_QUARTER = 299;

type AddOn = "none" | "cyberpulse" | "claude";

const COMPARISON: { label: string; deepseek: boolean | string; cyberpulse: boolean | string; claude: boolean | string }[] = [
  { label: "8-fasen geautomatiseerde pentest", deepseek: true, cyberpulse: true, claude: true },
  { label: "15+ professionele Kali-tools", deepseek: true, cyberpulse: true, claude: true },
  { label: "AI-analyse & herstelplan", deepseek: "DeepSeek", cyberpulse: "CyberPulse AI", claude: "Claude" },
  { label: "PDF- & JSON-rapporten", deepseek: true, cyberpulse: true, claude: true },
  { label: "Geplande scans & meldingen", deepseek: true, cyberpulse: true, claude: true },
  { label: "Dataverwerking uitsluitend in de EU", deepseek: false, cyberpulse: true, claude: false },
  { label: "Hoogste analysekwaliteit", deepseek: false, cyberpulse: false, claude: true },
  { label: "Prijs per systeem / maand", deepseek: "€19", cyberpulse: "€28", claude: "€38" },
];

function HeaderBar() {
  return (
    <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
      <Link href="/" className="flex items-center gap-2.5">
        <div className="relative flex h-8 w-8 items-center justify-center">
          <ShieldCheck className="h-7 w-7 text-cyan" style={{ filter: "drop-shadow(0 0 6px #00D4FF88)" }} />
          <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-neon-green animate-pulse-dot" />
        </div>
        <span className="font-display text-[17px] font-bold text-ink">
          Cyber<span className="text-cyan">Pulse</span>
        </span>
      </Link>
      <div className="flex items-center gap-3">
        <Link href="/login" className="font-mono text-[13px] text-ink-muted transition-colors hover:text-cyan">
          Inloggen
        </Link>
        <Link
          href="/register"
          className="rounded-lg bg-cyan px-4 py-2 text-[13px] font-semibold text-black transition-opacity hover:opacity-90 shadow-glow-cyan"
        >
          Gratis starten
        </Link>
      </div>
    </header>
  );
}

function Cell({ value }: { value: boolean | string }) {
  if (value === true) return <Check className="mx-auto h-4 w-4 text-neon-green" />;
  if (value === false) return <Minus className="mx-auto h-4 w-4 text-ink-muted/50" />;
  return <span className="font-mono text-[12px] text-ink">{value}</span>;
}

export default function PricingPage() {
  const [targets, setTargets] = useState(3);
  const [addon, setAddon] = useState<AddOn>("none");
  const [nis2, setNis2] = useState(false);

  const monthly = useMemo(() => {
    const addonRate = addon === "cyberpulse" ? ADDON_CYBERPULSE : addon === "claude" ? ADDON_CLAUDE : 0;
    const perTarget = BASE_PER_TARGET + addonRate;
    const subscription = perTarget * targets;
    const nis2Monthly = nis2 ? NIS2_PER_QUARTER / 3 : 0;
    return { subscription, nis2Monthly, total: subscription + nis2Monthly, perTarget };
  }, [targets, addon, nis2]);

  return (
    <main className="relative min-h-[100dvh] overflow-hidden bg-app">
      <HeaderBar />

      {/* Hero */}
      <section className="relative z-10 mx-auto max-w-4xl px-6 pt-10 pb-10 text-center sm:pt-16">
        <motion.h1
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
          className="font-display text-4xl font-bold leading-tight text-ink sm:text-5xl"
        >
          Eerlijke prijzen,
          <br /><span className="text-cyan text-glow-cyan">betaal per systeem.</span>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.1 }}
          className="mx-auto mt-5 max-w-2xl text-[15px] leading-relaxed text-ink-muted"
        >
          Geen verrassingen. U betaalt per systeem dat u laat scannen, en kiest zelf welke
          AI uw rapporten maakt. Upgrade of stop wanneer u wilt.
        </motion.p>
      </section>

      {/* Pricing tiers */}
      <section className="relative z-10 mx-auto grid max-w-6xl gap-4 px-6 py-8 md:grid-cols-3">
        {[
          {
            key: "deepseek", icon: Cpu, title: "Standaard", badge: "Inbegrepen", badgeColor: "#00FF88",
            price: BASE_PER_TARGET, per: "/systeem/maand",
            desc: "AI-analyse met DeepSeek. Alles wat u nodig heeft om te starten.",
            feats: ["8-fasen pentest", "15+ Kali-tools", "DeepSeek AI-analyse", "PDF & NIS2-rapporten", "Geplande scans"],
            featured: false,
          },
          {
            key: "cyberpulse", icon: Server, title: "CyberPulse AI", badge: "EU-only", badgeColor: "#00B4D8",
            price: BASE_PER_TARGET + ADDON_CYBERPULSE, per: "/systeem/maand",
            desc: "Zelf-gehost model volledig binnen de EU. Maximale dataprivacy.",
            feats: ["Alles uit Standaard", "Dataverwerking in de EU", "Eigen CyberPulse-model", "+€9 per systeem"],
            featured: true,
          },
          {
            key: "claude", icon: Sparkles, title: "Claude", badge: "Premium", badgeColor: "#FF8C00",
            price: BASE_PER_TARGET + ADDON_CLAUDE, per: "/systeem/maand",
            desc: "Hoogste analysekwaliteit met Claude (Anthropic) voor kritieke systemen.",
            feats: ["Alles uit Standaard", "Claude-analyse (Anthropic)", "Diepgaande rapporten", "+€19 per systeem"],
            featured: false,
          },
        ].map((tier, i) => (
          <motion.div
            key={tier.key}
            initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
            transition={{ duration: 0.4, delay: i * 0.05 }}
            className={`relative flex flex-col rounded-2xl border bg-card2 p-6 ${
              tier.featured ? "border-cyan/50 shadow-glow-cyan" : "border-grid"
            }`}
          >
            {tier.featured && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-cyan px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-black">
                Aanbevolen
              </span>
            )}
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <tier.icon className="h-5 w-5 text-cyan" />
                <h3 className="font-display text-[16px] font-semibold text-ink">{tier.title}</h3>
              </div>
              <span
                className="rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.08em]"
                style={{ color: tier.badgeColor, borderColor: `${tier.badgeColor}66`, backgroundColor: `${tier.badgeColor}1a` }}
              >
                {tier.badge}
              </span>
            </div>
            <div className="flex items-end gap-1">
              <span className="font-display text-4xl font-bold text-ink">€{tier.price}</span>
              <span className="mb-1.5 text-[12px] text-ink-muted">{tier.per}</span>
            </div>
            <p className="mt-2 text-[13px] leading-relaxed text-ink-muted">{tier.desc}</p>
            <ul className="mt-5 flex-1 space-y-2">
              {tier.feats.map((f) => (
                <li key={f} className="flex items-center gap-2 text-[13px] text-ink">
                  <Check className="h-4 w-4 flex-shrink-0 text-neon-green" />
                  {f}
                </li>
              ))}
            </ul>
            <Link
              href="/register"
              className={`mt-6 inline-flex w-full items-center justify-center gap-2 rounded-lg px-5 py-2.5 text-[14px] font-semibold transition-all ${
                tier.featured
                  ? "bg-cyan text-black hover:opacity-90 shadow-glow-cyan"
                  : "border border-grid bg-app text-ink hover:border-cyan"
              }`}
            >
              Kies {tier.title} <ArrowRight className="h-4 w-4" />
            </Link>
          </motion.div>
        ))}
      </section>

      {/* NIS2 add-on */}
      <section className="relative z-10 mx-auto max-w-6xl px-6 py-4">
        <div className="flex flex-col items-start justify-between gap-4 rounded-2xl border border-grid bg-card2 p-6 sm:flex-row sm:items-center">
          <div className="flex items-start gap-3">
            <FileText className="mt-0.5 h-5 w-5 flex-shrink-0 text-cyan" />
            <div>
              <h3 className="font-display text-[15px] font-semibold text-ink">NIS2-compliancerapport</h3>
              <p className="mt-1 text-[13px] text-ink-muted">
                Volledig auditklaar NIS2-overzicht, opgesteld per kwartaal. Klaar voor uw auditor of toezichthouder.
              </p>
            </div>
          </div>
          <div className="flex items-end gap-1 whitespace-nowrap">
            <span className="font-display text-3xl font-bold text-ink">€{NIS2_PER_QUARTER}</span>
            <span className="mb-1 text-[12px] text-ink-muted">/kwartaal</span>
          </div>
        </div>
      </section>

      {/* Calculator */}
      <section className="relative z-10 mx-auto max-w-3xl px-6 py-12">
        <div className="rounded-2xl border border-grid bg-card2 p-7">
          <h2 className="font-display text-xl font-bold text-ink">Bereken uw maandprijs</h2>
          <p className="mt-1 text-[13px] text-ink-muted">Schuif het aantal systemen en kies uw opties.</p>

          {/* Targets slider */}
          <div className="mt-7">
            <div className="mb-2 flex items-center justify-between">
              <label className="text-[12px] uppercase tracking-[0.1em] text-ink-muted">Aantal systemen</label>
              <span className="font-mono text-[15px] font-semibold text-cyan">{targets}</span>
            </div>
            <input
              type="range" min={1} max={50} value={targets}
              onChange={(e) => setTargets(Number(e.target.value))}
              className="w-full accent-cyan"
            />
            <div className="mt-1 flex justify-between font-mono text-[10px] text-ink-muted">
              <span>1</span><span>50</span>
            </div>
          </div>

          {/* AI add-on */}
          <div className="mt-7">
            <label className="mb-2 block text-[12px] uppercase tracking-[0.1em] text-ink-muted">AI-model</label>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              {([
                { value: "none", label: "DeepSeek", note: "inbegrepen" },
                { value: "cyberpulse", label: "CyberPulse AI", note: "+€9" },
                { value: "claude", label: "Claude", note: "+€19" },
              ] as { value: AddOn; label: string; note: string }[]).map((o) => {
                const active = addon === o.value;
                return (
                  <button
                    key={o.value}
                    type="button"
                    onClick={() => setAddon(o.value)}
                    className={`rounded-lg border-2 px-3 py-2.5 text-left transition-colors ${
                      active ? "border-cyan bg-cyan/5" : "border-grid hover:border-cyan/30"
                    }`}
                  >
                    <div className="text-[13px] font-semibold text-ink">{o.label}</div>
                    <div className="font-mono text-[11px] text-ink-muted">{o.note}</div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* NIS2 toggle */}
          <div className="mt-6 flex items-center justify-between rounded-lg border border-grid bg-app px-4 py-3">
            <div>
              <div className="text-[13px] text-ink">NIS2-compliancerapport toevoegen</div>
              <div className="text-[11px] text-ink-muted">€{NIS2_PER_QUARTER}/kwartaal (≈ €{Math.round(NIS2_PER_QUARTER / 3)}/maand)</div>
            </div>
            <button
              role="switch"
              aria-checked={nis2}
              onClick={() => setNis2((v) => !v)}
              className={`relative h-6 w-11 rounded-full border transition-colors ${
                nis2 ? "border-cyan bg-cyan/30" : "border-grid bg-card2"
              }`}
            >
              <span
                className={`absolute top-1/2 h-4 w-4 -translate-y-1/2 rounded-full transition-all ${
                  nis2 ? "right-1 bg-cyan shadow-glow-cyan" : "left-1 bg-ink-muted"
                }`}
              />
            </button>
          </div>

          {/* Total */}
          <div className="mt-7 rounded-xl border border-cyan/30 bg-cyan/5 p-5">
            <div className="flex items-center justify-between text-[13px] text-ink-muted">
              <span>{targets} systeem{targets === 1 ? "" : "en"} × €{monthly.perTarget}</span>
              <span className="font-mono text-ink">€{monthly.subscription.toFixed(0)}</span>
            </div>
            {nis2 && (
              <div className="mt-1 flex items-center justify-between text-[13px] text-ink-muted">
                <span>NIS2-rapport (per maand)</span>
                <span className="font-mono text-ink">€{monthly.nis2Monthly.toFixed(0)}</span>
              </div>
            )}
            <div className="mt-3 flex items-end justify-between border-t border-grid pt-3">
              <span className="text-[13px] font-semibold uppercase tracking-[0.08em] text-ink">Totaal per maand</span>
              <span className="font-display text-3xl font-bold text-cyan">€{monthly.total.toFixed(0)}</span>
            </div>
          </div>

          <Link
            href="/register"
            className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-cyan px-6 py-3 text-[15px] font-semibold text-black transition-opacity hover:opacity-90 shadow-glow-cyan"
          >
            Start nu <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      {/* Comparison table */}
      <section className="relative z-10 mx-auto max-w-4xl px-6 py-12">
        <h2 className="mb-6 text-center font-display text-2xl font-bold text-ink">Vergelijk de modellen</h2>
        <div className="overflow-x-auto rounded-2xl border border-grid bg-card2">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-grid">
                <th className="px-4 py-3 text-[12px] uppercase tracking-[0.08em] text-ink-muted">Functie</th>
                <th className="px-4 py-3 text-center text-[12px] uppercase tracking-[0.08em] text-ink-muted">Standaard</th>
                <th className="px-4 py-3 text-center text-[12px] uppercase tracking-[0.08em] text-cyan">CyberPulse AI</th>
                <th className="px-4 py-3 text-center text-[12px] uppercase tracking-[0.08em] text-ink-muted">Claude</th>
              </tr>
            </thead>
            <tbody>
              {COMPARISON.map((row, i) => (
                <tr key={row.label} className={i % 2 === 1 ? "bg-app/40" : ""}>
                  <td className="px-4 py-3 text-[13px] text-ink">{row.label}</td>
                  <td className="px-4 py-3 text-center"><Cell value={row.deepseek} /></td>
                  <td className="px-4 py-3 text-center"><Cell value={row.cyberpulse} /></td>
                  <td className="px-4 py-3 text-center"><Cell value={row.claude} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 mx-auto max-w-6xl border-t border-grid px-6 py-8 text-center">
        <p className="font-mono text-[11px] text-ink-muted">
          CyberPulse — Geautomatiseerd pentesten voor het MKB ·{" "}
          <Link href="/terms" className="text-cyan hover:underline">Gebruiksvoorwaarden</Link>
        </p>
      </footer>
    </main>
  );
}
