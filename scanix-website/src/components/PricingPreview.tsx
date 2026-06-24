"use client";

import { useTranslations } from "next-intl";
import { motion } from "framer-motion";
import { Zap, ArrowRight } from "lucide-react";
import { Link } from "@/lib/navigation";

/**
 * Compact homepage teaser for the credits pricing — price points + a link
 * through to the full /prijzen page. Reuses the `pricing` i18n namespace.
 */
const PREVIEW = [
  { key: "losse_scan", nameKey: "pkgLosseScan", price: "€100", credits: 1 },
  { key: "starter", nameKey: "pkgStarter", price: "€250", credits: 3 },
  { key: "groei", nameKey: "pkgGroei", price: "€375", credits: 5, popular: true },
  { key: "pro", nameKey: "pkgPro", price: "€650", credits: 10 },
  { key: "expert", nameKey: "pkgExpert", price: "€1.250", credits: 25 },
] as const;

export function PricingPreview() {
  const t = useTranslations("pricing");

  return (
    <section className="relative mx-auto max-w-content px-5 py-20 md:px-8 md:py-28">
      <div className="text-center">
        <h2 className="font-display text-3xl font-bold tracking-tight text-ink md:text-4xl">{t("title")}</h2>
        <p className="mx-auto mt-3 max-w-xl text-[15px] text-ink-muted">{t("subtitle")}</p>
      </div>

      <div className="mx-auto mt-12 grid max-w-5xl gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {PREVIEW.map((p, i) => (
          <motion.div
            key={p.key}
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.45, delay: i * 0.08, ease: [0.16, 1, 0.3, 1] }}
            className={`flex flex-col items-center rounded-2xl border bg-card p-5 text-center ${
              "popular" in p && p.popular ? "border-cyan/50 shadow-glow-cyan" : "border-grid"
            }`}
          >
            <span className="font-display text-[15px] font-semibold text-ink">{t(p.nameKey)}</span>
            <span className="mt-2 font-display text-2xl font-bold text-ink">{p.price}</span>
            <span className="mt-2 inline-flex items-center gap-1.5 font-mono text-[12px] text-cyan">
              <Zap className="h-3.5 w-3.5" fill="currentColor" strokeWidth={2} />
              {p.credits} {p.credits === 1 ? t("credit") : t("credits")}
            </span>
          </motion.div>
        ))}
      </div>

      <div className="mt-10 flex justify-center">
        <Link
          href="/prijzen"
          className="inline-flex items-center gap-2 rounded-xl bg-cyan px-6 py-3 text-[14px] font-semibold text-bg transition-all hover:shadow-glow-cyan active:scale-[0.98]"
        >
          {t("headline")} <ArrowRight className="h-4 w-4" strokeWidth={2} />
        </Link>
      </div>

      <p className="mt-4 text-center text-[12px] text-ink-muted">{t("neverExpire")}</p>
    </section>
  );
}
