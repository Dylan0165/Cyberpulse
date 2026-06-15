"use client";

import { useTranslations } from "next-intl";
import { motion } from "framer-motion";

export function Problem() {
  const t = useTranslations("problem");

  const cards = [
    {
      number: t("card1Number"),
      label: t("card1Label"),
      subtext: t("card1Subtext"),
      color: "text-red",
    },
    {
      number: t("card2Number"),
      label: t("card2Label"),
      subtext: t("card2Subtext"),
      color: "text-orange",
    },
    {
      number: t("card3Number"),
      label: t("card3Label"),
      subtext: t("card3Subtext"),
      color: "text-cyan",
    },
  ];

  return (
    <section
      id="problem"
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

      <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
        {cards.map((card, i) => (
          <motion.div
            key={card.label}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: i * 0.08 }}
            className="rounded-xl border border-grid bg-card p-6"
          >
            <p className={`font-display text-5xl font-bold ${card.color}`}>
              {card.number}
            </p>
            <p className="mt-4 text-[15px] font-medium text-ink">{card.label}</p>
            <p className="mt-1.5 text-sm text-ink-muted">{card.subtext}</p>
          </motion.div>
        ))}
      </div>

      <motion.p
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.4 }}
        className="mt-12 max-w-3xl text-[17px] leading-relaxed text-ink-muted"
      >
        {t("paragraph")}
      </motion.p>
    </section>
  );
}
