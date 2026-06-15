"use client";

import { useTranslations } from "next-intl";
import { motion } from "framer-motion";
import { MapPin, Lock, Zap, Languages } from "lucide-react";

const TOOLS = [
  "nmap",
  "nuclei",
  "nikto",
  "hydra",
  "sqlmap",
  "testssl.sh",
  "ffuf",
  "gitleaks",
  "theHarvester",
];

export function Trust() {
  const t = useTranslations("trust");

  const statements = [
    { icon: MapPin, text: t("builtNL") },
    { icon: Lock, text: t("dataEU") },
    { icon: Zap, text: t("fast") },
    { icon: Languages, text: t("languages") },
  ];

  return (
    <section className="relative mx-auto max-w-content px-5 py-20 md:px-8 md:py-28">
      <motion.h2
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.4 }}
        className="font-display text-3xl font-bold tracking-tight text-ink md:text-4xl"
      >
        {t("title")}
      </motion.h2>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.4 }}
        className="mt-8 flex flex-wrap gap-2"
      >
        {TOOLS.map((tool) => (
          <span
            key={tool}
            className="rounded-md border border-grid bg-card px-3 py-1.5 font-mono text-[12px] text-ink-muted"
          >
            {tool}
          </span>
        ))}
        <span className="rounded-md border border-grid bg-card px-3 py-1.5 font-mono text-[12px] text-ink-muted">
          {t("toolsMore")}
        </span>
      </motion.div>

      <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-4">
        {statements.map((item, i) => {
          const Icon = item.icon;
          return (
            <motion.div
              key={item.text}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.08 }}
            >
              <Icon className="h-6 w-6 text-cyan" strokeWidth={2} />
              <p className="mt-3 text-[15px] leading-relaxed text-ink-muted">
                {item.text}
              </p>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
