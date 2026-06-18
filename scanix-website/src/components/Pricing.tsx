"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { motion } from "framer-motion";
import { Check, ArrowRight, Server, Sparkles, FileText, Minus } from "lucide-react";
import { Link } from "@/lib/navigation";

const PRICE = 19;

export function Pricing() {
  const t = useTranslations("pricing");
  const [systems, setSystems] = useState(3);
  const total = useMemo(() => systems * PRICE, [systems]);

  const features = [
    t("feature1"), t("feature2"), t("feature3"), t("feature4"),
    t("feature5"), t("feature6"), t("feature7"), t("feature8"),
    t("feature9"),
  ];

  const rows = [
    { f: t("tablePrice"), a: t("tablePriceScanix"), b: t("tablePriceManual") },
    { f: t("tableTime"), a: t("tableTimeScanix"), b: t("tableTimeManual") },
    { f: t("tableFreq"), a: t("tableFreqScanix"), b: t("tableFreqManual") },
    { f: t("tableNis2"), a: t("tableNis2Scanix"), b: t("tableNis2Manual"), aGood: true },
    { f: t("tableExploit"), a: t("tableExploitScanix"), b: t("tableExploitManual"), aGood: true },
    { f: t("tableLang"), a: t("tableLangScanix"), b: t("tableLangManual"), aGood: true },
  ];

  return (
    <section id="pricing" className="relative mx-auto max-w-content px-5 py-20 md:px-8 md:py-28">
      <div className="text-center">
        <h2 className="font-display text-3xl font-bold tracking-tight text-ink md:text-4xl">{t("title")}</h2>
        <p className="mx-auto mt-3 max-w-xl text-[15px] text-ink-muted">{t("subtitle")}</p>
      </div>

      {/* Main card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.4 }}
        className="mx-auto mt-12 max-w-lg rounded-2xl border border-cyan/30 bg-card p-8 shadow-glow-cyan"
      >
        <p className="font-mono text-[12px] uppercase tracking-[0.18em] text-cyan">{t("base")}</p>
        <div className="mt-3 flex items-end gap-2">
          <span className="font-display text-6xl font-bold text-ink">{t("price")}</span>
          <span className="mb-2 text-[14px] text-ink-muted">{t("per")}</span>
        </div>
        <ul className="mt-7 grid gap-2.5 sm:grid-cols-2">
          {features.map((f) => (
            <li key={f} className="flex items-start gap-2 text-[13.5px] text-ink">
              <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-green" strokeWidth={2.5} />
              {f}
            </li>
          ))}
        </ul>
        <Link
          href="/contact"
          className="mt-8 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-cyan px-6 py-3.5 text-[15px] font-semibold text-bg transition-all hover:shadow-glow-cyan active:scale-[0.98]"
        >
          {t("cta")}
          <ArrowRight className="h-4.5 w-4.5" strokeWidth={2} />
        </Link>
      </motion.div>

      {/* Calculator */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.4 }}
        className="mx-auto mt-8 max-w-lg rounded-2xl border border-grid bg-card/60 p-7"
      >
        <p className="font-display text-[16px] font-semibold text-ink">{t("calcTitle")}</p>
        <div className="mt-5 flex items-center justify-between">
          <span className="font-mono text-[13px] text-ink-muted">
            {systems} {t("calcSystems")}
          </span>
          <span className="font-mono text-[15px] font-semibold text-cyan">
            {systems} × €{PRICE} = €{total} {t("calcPerMonth")}
          </span>
        </div>
        <input
          type="range"
          min={1}
          max={50}
          value={systems}
          onChange={(e) => setSystems(Number(e.target.value))}
          className="mt-3 w-full"
          aria-label={t("calcSystems")}
        />
        <p className="mt-4 text-center text-[13px] text-ink-muted">
          {t("calcCoffee", { count: systems })}
        </p>
      </motion.div>

      {/* AI upgrades */}
      <div className="mx-auto mt-14 max-w-3xl">
        <p className="mb-4 text-center font-display text-[15px] font-semibold uppercase tracking-wide text-ink-muted">{t("aiTitle")}</p>
        <div className="grid gap-4 md:grid-cols-2">
          {[
            { icon: Server, name: t("scanixAiName"), price: t("scanixAiPrice"), badge: t("scanixAiBadge"), desc: t("scanixAiDesc"), color: "#00B4D8" },
            { icon: Sparkles, name: t("claudeName"), price: t("claudePrice"), badge: t("claudeBadge"), desc: t("claudeDesc"), color: "#FF8C00" },
          ].map((c) => (
            <div key={c.name} className="flex flex-col rounded-xl border border-grid bg-card p-6">
              <div className="mb-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <c.icon className="h-5 w-5 text-cyan" strokeWidth={2} />
                  <span className="font-display text-[15px] font-semibold text-ink">{c.name}</span>
                </div>
                <span className="rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide" style={{ color: c.color, borderColor: `${c.color}55`, background: `${c.color}14` }}>
                  {c.badge}
                </span>
              </div>
              <p className="text-[14px] font-semibold text-ink">{c.price}</p>
              <p className="mt-2 flex-1 text-[13px] leading-relaxed text-ink-muted">{c.desc}</p>
              <Link href="/contact" className="mt-4 inline-flex items-center gap-1.5 text-[13px] font-medium text-cyan hover:underline">
                {t("moreInfo")} <ArrowRight className="h-3.5 w-3.5" strokeWidth={2} />
              </Link>
            </div>
          ))}
        </div>
      </div>

      {/* NIS2 add-on */}
      <div className="mx-auto mt-6 max-w-3xl">
        <div className="flex flex-col items-start justify-between gap-4 rounded-xl border border-grid bg-card/60 p-6 sm:flex-row sm:items-center">
          <div className="flex items-start gap-3">
            <FileText className="mt-0.5 h-5 w-5 flex-shrink-0 text-cyan" strokeWidth={2} />
            <div>
              <p className="font-display text-[15px] font-semibold text-ink">{t("nis2Title")}</p>
              <p className="mt-1 text-[13px] text-ink-muted">{t("nis2Desc")}</p>
            </div>
          </div>
          <Link href="/contact" className="inline-flex flex-shrink-0 items-center gap-1.5 rounded-lg border border-cyan/40 px-4 py-2 text-[13px] font-semibold text-cyan transition-colors hover:bg-cyan/10">
            {t("nis2Cta")} <ArrowRight className="h-3.5 w-3.5" strokeWidth={2} />
          </Link>
        </div>
      </div>

      {/* Comparison table */}
      <div className="mx-auto mt-14 max-w-3xl overflow-x-auto rounded-2xl border border-grid">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-grid bg-card">
              <th className="px-4 py-3 text-[12px] uppercase tracking-wide text-ink-muted">{t("tableFeature")}</th>
              <th className="px-4 py-3 text-center text-[12px] uppercase tracking-wide text-cyan">{t("tableScanix")}</th>
              <th className="px-4 py-3 text-center text-[12px] uppercase tracking-wide text-ink-muted">{t("tableManual")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={row.f} className={i % 2 ? "bg-bg-secondary/40" : ""}>
                <td className="px-4 py-3 text-[13px] text-ink">{row.f}</td>
                <td className="px-4 py-3 text-center text-[13px]">
                  {row.aGood ? (
                    <span className="inline-flex items-center gap-1.5 font-medium text-green">
                      <Check className="h-4 w-4" strokeWidth={2.5} /> {row.a}
                    </span>
                  ) : (
                    <span className="font-mono text-ink">{row.a}</span>
                  )}
                </td>
                <td className="px-4 py-3 text-center font-mono text-[13px] text-ink-muted">
                  <span className="inline-flex items-center gap-1.5">
                    <Minus className="h-3.5 w-3.5 text-ink-muted/50" /> {row.b}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
