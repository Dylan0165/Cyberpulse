"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { motion, AnimatePresence } from "framer-motion";
import { Check, X, ArrowRight } from "lucide-react";
import { Link } from "@/lib/navigation";

type Interval = "monthly" | "quarterly" | "yearly";

export function Pricing() {
  const t = useTranslations("pricing");
  const tt = useTranslations("tiers");
  const [interval, setInterval] = useState<Interval>("monthly");

  const intervals: { key: Interval; label: string }[] = [
    { key: "monthly", label: tt("intMonthly") },
    { key: "quarterly", label: tt("intQuarterly") },
    { key: "yearly", label: tt("intYearly") },
  ];

  const starterPrice: Record<Interval, string> = {
    monthly: "€149/mnd",
    quarterly: "€399/kwartaal",
    yearly: "€1.299/jaar",
  };
  const businessPrice: Record<Interval, string> = {
    monthly: "€349/mnd",
    quarterly: "€949/kwartaal",
    yearly: "€2.999/jaar",
  };

  type Feat = { label: string; included: boolean };

  const plans: {
    key: string;
    name: string;
    price: string;
    featured: boolean;
    badge?: string;
    feats: Feat[];
    href: string;
    cta: string;
    note?: string;
  }[] = [
    {
      key: "starter",
      name: tt("starterName"),
      price: starterPrice[interval],
      featured: false,
      feats: [
        { label: tt("fMonitor1"), included: true },
        { label: tt("fScan1"), included: true },
        { label: tt("fPdf"), included: true },
        { label: tt("fNis2"), included: true },
        { label: tt("fSecure"), included: true },
        { label: tt("fModules"), included: false },
        { label: tt("fScheduled"), included: false },
      ],
      href: `https://app.scanix.nl/login?plan=starter&interval=${interval}`,
      cta: tt("planCta"),
      note: tt("loginNote"),
    },
    {
      key: "business",
      name: tt("businessName"),
      price: businessPrice[interval],
      featured: true,
      badge: tt("badgePopular"),
      feats: [
        { label: tt("bMonitor5"), included: true },
        { label: tt("bScansUnlimited"), included: true },
        { label: tt("bAllReports"), included: true },
        { label: tt("bAllModules"), included: true },
        { label: tt("bScheduled"), included: true },
        { label: tt("bCompare"), included: true },
        { label: tt("bEmailSupport"), included: true },
      ],
      href: `https://app.scanix.nl/login?plan=business&interval=${interval}`,
      cta: tt("planCta"),
      note: tt("loginNote"),
    },
    {
      key: "enterprise",
      name: tt("enterpriseName"),
      price: tt("enterpriseFrom"),
      featured: false,
      feats: [
        { label: tt("eSystems20"), included: true },
        { label: tt("eAllBusiness"), included: true },
        { label: tt("eAiUpgrade"), included: true },
        { label: tt("eWhiteLabel"), included: true },
        { label: tt("eQuarterlyCall"), included: true },
        { label: tt("eNis2Audit"), included: true },
        { label: tt("ePrioritySupport"), included: true },
      ],
      href: "/contact",
      cta: tt("contactCta"),
    },
  ];

  const rows: { label: string; cells: (boolean | string)[] }[] = [
    { label: tt("rowSystems"), cells: ["1", "5", "20"] },
    { label: tt("rowScans"), cells: [tt("cellScans1"), tt("cellUnlimited"), tt("cellUnlimited")] },
    { label: tt("rowModules"), cells: [false, true, true] },
    { label: tt("rowScheduled"), cells: [false, true, true] },
    { label: tt("rowAiUpgrade"), cells: [false, false, true] },
    { label: tt("rowWhiteLabel"), cells: [false, false, true] },
    { label: tt("rowSupport"), cells: [tt("cellEmail"), tt("cellEmail"), tt("cellPriority")] },
  ];

  const colHeads = [tt("starterName"), tt("businessName"), tt("enterpriseName")];

  return (
    <section id="pricing" className="relative mx-auto max-w-content px-5 py-20 md:px-8 md:py-28">
      <div className="text-center">
        <h2 className="font-display text-3xl font-bold tracking-tight text-ink md:text-4xl">{t("title")}</h2>
        <p className="mx-auto mt-3 max-w-xl text-[15px] text-ink-muted">{t("subtitle")}</p>
      </div>

      {/* Interval toggle */}
      <div className="mt-10 flex justify-center">
        <div className="inline-flex items-center gap-1 rounded-full border border-grid bg-card p-1">
          {intervals.map((it) => (
            <button
              key={it.key}
              type="button"
              onClick={() => setInterval(it.key)}
              className={`rounded-full px-4 py-2 text-[13px] font-semibold transition-all ${
                interval === it.key
                  ? "bg-cyan text-bg shadow-glow-cyan"
                  : "text-ink-muted hover:text-ink"
              }`}
            >
              {it.label}
            </button>
          ))}
        </div>
      </div>

      {/* Plan cards */}
      <div className="mx-auto mt-12 grid max-w-5xl gap-5 md:grid-cols-3">
        {plans.map((p, i) => (
          <motion.div
            key={p.key}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: i * 0.06 }}
            className={`relative flex flex-col rounded-2xl border bg-card p-7 ${
              p.featured ? "border-cyan/50 shadow-glow-cyan" : "border-grid"
            }`}
          >
            {p.featured && p.badge && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-cyan px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-bg">
                {p.badge}
              </span>
            )}
            <h3 className="font-display text-[18px] font-semibold text-ink">{p.name}</h3>
            <div className="mt-2 h-12 overflow-hidden">
              <AnimatePresence mode="wait">
                <motion.span
                  key={interval + p.key}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.2 }}
                  className="block font-display text-3xl font-bold text-ink"
                >
                  {p.price}
                </motion.span>
              </AnimatePresence>
            </div>
            <ul className="mt-5 flex-1 space-y-2.5">
              {p.feats.map((f) => (
                <li
                  key={f.label}
                  className={`flex items-start gap-2 text-[13.5px] ${
                    f.included ? "text-ink" : "text-ink-muted"
                  }`}
                >
                  {f.included ? (
                    <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-green" strokeWidth={2} />
                  ) : (
                    <X className="mt-0.5 h-4 w-4 flex-shrink-0 text-ink-muted" strokeWidth={2} />
                  )}
                  {f.label}
                </li>
              ))}
            </ul>
            <Link
              href={p.href}
              className={`mt-6 inline-flex w-full items-center justify-center gap-2 rounded-xl px-5 py-3 text-[14px] font-semibold transition-all active:scale-[0.98] ${
                p.featured
                  ? "bg-cyan text-bg hover:shadow-glow-cyan"
                  : "border border-grid text-ink hover:border-cyan/40"
              }`}
            >
              {p.cta} <ArrowRight className="h-4 w-4" strokeWidth={2} />
            </Link>
            {p.note && (
              <p className="mt-3 text-center text-[11px] text-ink-muted">{p.note}</p>
            )}
          </motion.div>
        ))}
      </div>

      {/* Comparison table */}
      <div className="mx-auto mt-14 max-w-4xl overflow-x-auto rounded-2xl border border-grid">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-grid bg-card">
              <th className="px-4 py-3 text-[12px] uppercase tracking-wide text-ink-muted">{tt("tableFeature")}</th>
              {colHeads.map((h, idx) => (
                <th
                  key={h}
                  className={`px-4 py-3 text-center text-[12px] uppercase tracking-wide ${
                    idx === 1 ? "text-cyan" : "text-ink-muted"
                  }`}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={row.label} className={i % 2 ? "bg-bg-secondary/40" : ""}>
                <td className="px-4 py-3 text-[13px] text-ink">{row.label}</td>
                {row.cells.map((cell, ci) => (
                  <td key={ci} className="px-4 py-3 text-center text-[13px]">
                    {typeof cell === "boolean" ? (
                      cell ? (
                        <Check className="mx-auto h-4 w-4 text-green" strokeWidth={2} />
                      ) : (
                        <X className="mx-auto h-4 w-4 text-ink-muted/60" strokeWidth={2} />
                      )
                    ) : (
                      <span className="font-mono text-ink-muted">{cell}</span>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
