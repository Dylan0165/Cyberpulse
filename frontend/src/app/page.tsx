"use client";

import Link from "next/link";
import Image from "next/image";
import { motion } from "framer-motion";
import {
  ShieldCheck, Radar, FileText, BrainCircuit, Bell, GitCompare,
  ArrowRight, Check,
} from "lucide-react";

const FEATURES = [
  { icon: Radar,        title: "Geautomatiseerde pentests", desc: "8-fasen scan met 15+ professionele Kali-tools — recon, kwetsbaarheden, web, auth, SSL en OSINT." },
  { icon: BrainCircuit, title: "AI-analyse",                desc: "DeepSeek vertaalt ruwe scanresultaten naar een helder rapport met risicoscore en concrete aanbevelingen." },
  { icon: FileText,     title: "NIS2 & PDF-rapporten",      desc: "Download professionele rapporten en een NIS2-compliance overzicht — klaar voor uw klant of auditor." },
  { icon: GitCompare,   title: "Scan-vergelijking",         desc: "Zie per scan wat nieuw, opgelost of ongewijzigd is en volg uw beveiliging over de tijd." },
  { icon: Bell,         title: "Meldingen & planning",      desc: "Plan automatische scans (dagelijks/wekelijks/maandelijks) en ontvang een melding zodra een scan klaar is." },
  { icon: ShieldCheck,  title: "Eigendomsverificatie",      desc: "Scan alleen systemen die u mag testen — verificatie via DNS of bestand beschermt u juridisch." },
];

const PLAN_FEATURES = [
  "4 volledige pentests per jaar",
  "Onbeperkt rapporten (PDF, JSON, NIS2)",
  "AI-analyse en herstelplan",
  "Automatische geplande scans",
  "E-mailnotificaties",
  "Alle 15+ beveiligingstools",
];

export default function LandingPage() {
  return (
    <main className="relative min-h-[100dvh] overflow-hidden bg-app">
      {/* Top bar */}
      <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2.5">
          <div className="relative flex h-8 w-8 items-center justify-center">
            <ShieldCheck className="h-7 w-7 text-cyan" style={{ filter: "drop-shadow(0 0 6px #00D4FF88)" }} />
            <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-neon-green animate-pulse-dot" />
          </div>
          <span className="font-display text-[17px] font-bold text-ink">
            Cyber<span className="text-cyan">Pulse</span>
          </span>
        </div>
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

      {/* Hero */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 pt-12 pb-16 text-center sm:pt-20">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="mx-auto mb-8 w-[140px] sm:w-[180px]"
        >
          <Image src="/logoCyber.png" alt="CyberPulse" width={180} height={180} priority className="mx-auto" />
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.1 }}
          className="font-display text-4xl font-bold leading-tight text-ink sm:text-5xl"
        >
          Geautomatiseerde pentests,
          <br /><span className="text-cyan text-glow-cyan">begrijpelijke resultaten.</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.2 }}
          className="mx-auto mt-5 max-w-2xl text-[15px] leading-relaxed text-ink-muted"
        >
          CyberPulse scant uw systemen zoals een echte aanvaller en levert een helder
          rapport met risicoscore en concrete acties — gemaakt voor het Nederlandse MKB,
          zonder dat u beveiligingsexpert hoeft te zijn.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.3 }}
          className="mt-8 flex flex-wrap items-center justify-center gap-3"
        >
          <Link
            href="/register"
            className="inline-flex items-center gap-2 rounded-lg bg-cyan px-6 py-3 text-[15px] font-semibold text-black transition-opacity hover:opacity-90 shadow-glow-cyan"
          >
            Start uw eerste scan <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/login"
            className="inline-flex items-center gap-2 rounded-lg border border-grid bg-card2 px-6 py-3 text-[15px] font-semibold text-ink transition-colors hover:border-cyan"
          >
            Inloggen
          </Link>
        </motion.div>
      </section>

      {/* Features */}
      <section className="relative z-10 mx-auto max-w-6xl px-6 py-12">
        <h2 className="mb-8 text-center font-display text-2xl font-bold text-ink">
          Alles wat u nodig heeft om veilig te blijven
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.05 }}
              className="rounded-lg border border-grid bg-card2 p-5"
            >
              <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-md" style={{ background: "rgba(0,212,255,0.1)", border: "1px solid rgba(0,212,255,0.2)" }}>
                <f.icon className="h-4.5 w-4.5 text-cyan" />
              </div>
              <h3 className="font-display text-[15px] font-semibold text-ink">{f.title}</h3>
              <p className="mt-1.5 text-[13px] leading-relaxed text-ink-muted">{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section className="relative z-10 mx-auto max-w-md px-6 py-12">
        <div className="rounded-2xl border border-grid bg-card2 p-8 text-center shadow-glow-cyan">
          <p className="font-mono text-[11px] uppercase tracking-widest text-cyan">Eén plan, alles inbegrepen</p>
          <div className="mt-3 flex items-end justify-center gap-1">
            <span className="font-display text-5xl font-bold text-ink">€999</span>
            <span className="mb-1.5 text-[14px] text-ink-muted">/jaar</span>
          </div>
          <ul className="mt-6 space-y-2.5 text-left">
            {PLAN_FEATURES.map((feat) => (
              <li key={feat} className="flex items-center gap-2.5 text-[13px] text-ink">
                <Check className="h-4 w-4 flex-shrink-0 text-neon-green" />
                {feat}
              </li>
            ))}
          </ul>
          <Link
            href="/register"
            className="mt-7 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-cyan px-6 py-3 text-[15px] font-semibold text-black transition-opacity hover:opacity-90"
          >
            Account aanmaken
          </Link>
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
