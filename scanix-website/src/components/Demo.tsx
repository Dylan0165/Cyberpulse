"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { motion } from "framer-motion";
import { Zap, ShieldCheck, BarChart3 } from "lucide-react";

const VIDEOS = ["/videos/demo1.mp4", "/videos/demo2.mp4"];

export function Demo() {
  const t = useTranslations("demo");
  const [active, setActive] = useState(0);
  const src = VIDEOS[active];

  const tabs = [t("tab1"), t("tab2")];
  const badges = [
    { icon: Zap, label: t("badge1") },
    { icon: ShieldCheck, label: t("badge2") },
    { icon: BarChart3, label: t("badge3") },
  ];

  return (
    <section id="demo" className="relative mx-auto max-w-content px-5 py-20 md:px-8 md:py-28">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.4 }}
        className="text-center"
      >
        <h2 className="font-display text-3xl font-bold tracking-tight text-ink md:text-4xl">
          {t("title")}
        </h2>
        <p className="mx-auto mt-3 max-w-2xl text-[15px] text-ink-muted">{t("subtitle")}</p>
      </motion.div>

      {/* Video player */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.4, delay: 0.05 }}
        className="mx-auto mt-10 w-full max-w-[1000px] overflow-hidden rounded-2xl border border-cyan/30 bg-card shadow-glow-cyan"
      >
        <video
          key={src}
          src={src}
          controls
          preload="metadata"
          playsInline
          className="block h-auto w-full bg-bg"
        />
      </motion.div>

      {/* Tabs */}
      <div className="mt-6 flex justify-center gap-3">
        {tabs.map((label, i) => {
          const isActive = active === i;
          return (
            <button
              key={label}
              onClick={() => setActive(i)}
              aria-pressed={isActive}
              className={`rounded-lg border px-5 py-2.5 text-[14px] font-medium transition-all active:scale-[0.98] ${
                isActive
                  ? "border-cyan/60 bg-cyan/10 text-cyan shadow-glow-cyan"
                  : "border-grid bg-card text-ink-muted hover:border-cyan/30 hover:text-ink"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* Highlight badges */}
      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        {badges.map((b) => (
          <span
            key={b.label}
            className="inline-flex items-center gap-2 rounded-full border border-grid bg-card px-4 py-2 text-[13px] text-ink"
          >
            <b.icon className="h-4 w-4 text-cyan" strokeWidth={2} />
            {b.label}
          </span>
        ))}
      </div>
    </section>
  );
}
