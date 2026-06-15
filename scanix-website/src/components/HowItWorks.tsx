"use client";

import { useTranslations } from "next-intl";
import { motion } from "framer-motion";
import { Crosshair, Radar, FileCheck, ArrowRight } from "lucide-react";

export function HowItWorks() {
  const t = useTranslations("how");

  const steps = [
    {
      number: "01",
      icon: Crosshair,
      title: t("step1Title"),
      text: t("step1Text"),
    },
    {
      number: "02",
      icon: Radar,
      title: t("step2Title"),
      text: t("step2Text"),
    },
    {
      number: "03",
      icon: FileCheck,
      title: t("step3Title"),
      text: t("step3Text"),
    },
  ];

  return (
    <section
      id="how-it-works"
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
        {steps.map((step, i) => {
          const Icon = step.icon;
          return (
            <motion.div
              key={step.number}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.08 }}
              className="relative"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-cyan/20 bg-cyan/10">
                <Icon className="h-6 w-6 text-cyan" strokeWidth={2} />
              </div>
              <p className="mt-5 font-mono text-sm text-ink-muted/40">
                {step.number}
              </p>
              <h3 className="mt-1 font-display text-xl font-bold text-ink">
                {step.title}
              </h3>
              <p className="mt-2 text-[15px] leading-relaxed text-ink-muted">
                {step.text}
              </p>

              {i < steps.length - 1 && (
                <ArrowRight
                  className="absolute -right-4 top-3 hidden h-5 w-5 text-ink-muted/30 md:block"
                  strokeWidth={2}
                />
              )}
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
