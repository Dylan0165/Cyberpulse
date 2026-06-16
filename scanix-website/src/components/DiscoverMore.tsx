"use client";

import { useTranslations } from "next-intl";
import { motion } from "framer-motion";
import { Radar, ShieldCheck, Tag, ArrowRight } from "lucide-react";
import { Link } from "@/lib/navigation";

export function DiscoverMore() {
  const tp = useTranslations("pages");
  const tn = useTranslations("nav");

  const cards = [
    { href: "/hoe-het-werkt", label: tn("how"), icon: Radar },
    { href: "/wat-we-testen", label: tn("what"), icon: ShieldCheck },
    { href: "/prijzen", label: tn("pricing"), icon: Tag },
  ];

  return (
    <section className="relative mx-auto max-w-content px-5 py-20 md:px-8 md:py-24">
      <h2 className="font-display text-2xl font-bold tracking-tight text-ink md:text-3xl">
        {tp("discover")}
      </h2>
      <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-3">
        {cards.map((c, i) => (
          <motion.div
            key={c.href}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: i * 0.08 }}
          >
            <Link
              href={c.href}
              className="group flex items-center justify-between rounded-xl border border-grid bg-card p-6 transition-colors hover:border-cyan/40"
            >
              <span className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-cyan/10">
                  <c.icon className="h-5 w-5 text-cyan" strokeWidth={2} />
                </span>
                <span className="font-display text-[16px] font-semibold text-ink">{c.label}</span>
              </span>
              <ArrowRight
                className="h-5 w-5 text-ink-muted transition-transform group-hover:translate-x-1 group-hover:text-cyan"
                strokeWidth={2}
              />
            </Link>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
