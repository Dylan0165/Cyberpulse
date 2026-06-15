"use client";

import { useTranslations } from "next-intl";
import { motion } from "framer-motion";
import { Search, Bug, Globe, KeyRound, Lock, Cpu, ArrowRight } from "lucide-react";

export function WhatWeTest() {
  const t = useTranslations("what");

  const cards = [
    { icon: Search, title: t("card1Title"), text: t("card1Text") },
    { icon: Bug, title: t("card2Title"), text: t("card2Text") },
    { icon: Globe, title: t("card3Title"), text: t("card3Text") },
    { icon: KeyRound, title: t("card4Title"), text: t("card4Text") },
    { icon: Lock, title: t("card5Title"), text: t("card5Text") },
    { icon: Cpu, title: t("card6Title"), text: t("card6Text") },
  ];

  return (
    <section
      id="what-we-test"
      className="relative mx-auto max-w-content px-5 py-20 md:px-8 md:py-28"
    >
      <motion.h2
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.4 }}
        className="font-display text-3xl font-bold tracking-tight text-ink md:text-4xl"
      >
        {t("title")}
      </motion.h2>
      <motion.p
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.4, delay: 0.05 }}
        className="mt-3 text-[17px] text-ink-muted"
      >
        {t("subtitle")}
      </motion.p>

      <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {cards.map((card, i) => {
          const Icon = card.icon;
          return (
            <motion.div
              key={card.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.08 }}
              className="rounded-xl border border-grid bg-card p-6 transition hover:border-cyan/30"
            >
              <Icon className="h-7 w-7 text-cyan" strokeWidth={2} />
              <h3 className="mt-4 font-display text-lg font-bold text-ink">
                {card.title}
              </h3>
              <p className="mt-2 text-[15px] leading-relaxed text-ink-muted">
                {card.text}
              </p>
            </motion.div>
          );
        })}
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.4 }}
        className="mt-10 flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between"
      >
        <p className="text-[15px] text-ink-muted">{t("more")}</p>
        <a
          href="#contact"
          className="inline-flex items-center gap-1.5 text-[15px] font-semibold text-cyan transition-colors hover:text-cyan/80"
        >
          {t("cta")}
          <ArrowRight className="h-4 w-4" strokeWidth={2} />
        </a>
      </motion.div>
    </section>
  );
}
