"use client";

import { motion } from "framer-motion";
import { Check, ArrowRight, Cpu, Server, Sparkles } from "lucide-react";
import { GlowCard } from "@/components/cyber/glow-card";

const MAIL_CYBERPULSE =
  "mailto:info@scanix.nl?subject=Upgrade%20Scanix%20AI";
const MAIL_CLAUDE =
  "mailto:info@scanix.nl?subject=Upgrade%20Claude%20Anthropic";

export default function UpgradePage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-bold tracking-[0.02em] text-ink">
          AI Analyse Upgraden
        </h1>
        <p className="mt-2 max-w-2xl text-[14px] leading-relaxed text-ink-muted">
          Standaard analyseren wij uw scan met DeepSeek AI. Wilt u meer privacy
          of een betere analyse? Kies een upgrade.
        </p>
      </div>

      {/* Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        {/* Card 1 — DeepSeek (included) */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <GlowCard className="flex h-full flex-col p-6">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cpu className="h-5 w-5 text-cyan" />
                <h2 className="font-display text-[16px] font-semibold text-ink">
                  DeepSeek
                </h2>
              </div>
              <span
                className="rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.08em]"
                style={{
                  color: "#00FF88",
                  borderColor: "#00FF8866",
                  backgroundColor: "#00FF881a",
                }}
              >
                Inbegrepen
              </span>
            </div>
            <div className="mb-3 flex items-center gap-2 text-[13px] text-neon-green">
              <Check className="h-4 w-4 flex-shrink-0" />
              Actief op uw account
            </div>
            <p className="flex-1 text-[13px] leading-relaxed text-ink-muted">
              Snelle en nauwkeurige analyse. Standaard voor alle accounts.
            </p>
            <div className="mt-6 rounded-lg border border-grid bg-app px-4 py-2.5 text-center text-[12px] text-ink-muted">
              Dit heeft iedereen al
            </div>
          </GlowCard>
        </motion.div>

        {/* Card 2 — Scanix AI */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.05 }}
        >
          <GlowCard className="flex h-full flex-col p-6">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Server className="h-5 w-5 text-cyan" />
                <h2 className="font-display text-[16px] font-semibold text-ink">
                  Scanix AI
                </h2>
              </div>
              <span
                className="rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.08em]"
                style={{
                  color: "#00B4D8",
                  borderColor: "#00B4D866",
                  backgroundColor: "#00B4D81a",
                }}
              >
                Privacy-first · EU-only
              </span>
            </div>
            <div className="mb-3 flex items-end gap-1">
              <span className="font-display text-2xl font-bold text-ink">+ €9</span>
              <span className="mb-1 text-[12px] text-ink-muted">
                per systeem per maand
              </span>
            </div>
            <p className="flex-1 text-[13px] leading-relaxed text-ink-muted">
              Ons eigen AI-model draait volledig op onze eigen servers in
              Europa. Uw scandata verlaat nooit ons platform. Ideaal voor zorg,
              overheid en financiële sector.
            </p>
            <a
              href={MAIL_CYBERPULSE}
              className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-cyan px-5 py-2.5 text-[14px] font-semibold text-black transition-opacity hover:opacity-90 shadow-glow-cyan"
            >
              Upgrade aanvragen <ArrowRight className="h-4 w-4" />
            </a>
          </GlowCard>
        </motion.div>

        {/* Card 3 — Claude (Anthropic) */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          <GlowCard className="flex h-full flex-col p-6">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-cyan" />
                <h2 className="font-display text-[16px] font-semibold text-ink">
                  Claude (Anthropic)
                </h2>
              </div>
              <span
                className="rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.08em]"
                style={{
                  color: "#FF8C00",
                  borderColor: "#FF8C0066",
                  backgroundColor: "#FF8C001a",
                }}
              >
                Meest geavanceerd
              </span>
            </div>
            <div className="mb-3 flex items-end gap-1">
              <span className="font-display text-2xl font-bold text-ink">+ €19</span>
              <span className="mb-1 text-[12px] text-ink-muted">
                per systeem per maand
              </span>
            </div>
            <p className="flex-1 text-[13px] leading-relaxed text-ink-muted">
              De meest geavanceerde AI-analyse beschikbaar. Beste kwaliteit voor
              compliance rapporten en auditvoorbereiding.
            </p>
            <a
              href={MAIL_CLAUDE}
              className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-cyan px-5 py-2.5 text-[14px] font-semibold text-ink transition-colors hover:bg-cyan/10"
            >
              Upgrade aanvragen <ArrowRight className="h-4 w-4" />
            </a>
          </GlowCard>
        </motion.div>
      </div>

      {/* Note below cards */}
      <p className="text-center text-[13px] text-ink-muted">
        Na uw aanvraag activeren wij de upgrade binnen 1 werkdag op uw account.
        Vragen? Mail ons op{" "}
        <a
          href="mailto:info@scanix.nl"
          className="text-cyan hover:underline"
        >
          info@scanix.nl
        </a>
      </p>
    </div>
  );
}
