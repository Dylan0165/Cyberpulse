"use client";

import { useRef } from "react";
import { useTranslations } from "next-intl";
import { motion } from "framer-motion";
import { Search, Bug, Globe, KeyRound, Lock, Cpu, ArrowRight } from "lucide-react";
import { Link } from "@/lib/navigation";

export function WhatWeTest() {
  const t = useTranslations("what");

  const videoRefs = useRef<Array<HTMLVideoElement | null>>([]);

  const cards = [
    { icon: Search, title: t("card1Title"), text: t("card1Text") },
    { icon: Bug, title: t("card2Title"), text: t("card2Text") },
    { icon: Globe, title: t("card3Title"), text: t("card3Text") },
    { icon: KeyRound, title: t("card4Title"), text: t("card4Text") },
    { icon: Lock, title: t("card5Title"), text: t("card5Text") },
    { icon: Cpu, title: t("card6Title"), text: t("card6Text") },
  ];

  const handleEnter = (index: number): void => {
    const video = videoRefs.current[index];
    if (!video) return;
    void video.play().catch(() => {
      /* autoplay/play interruption is non-fatal */
    });
  };

  const handleLeave = (index: number): void => {
    const video = videoRefs.current[index];
    if (!video) return;
    video.pause();
    video.currentTime = 0;
  };

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
              onMouseEnter={() => handleEnter(i)}
              onMouseLeave={() => handleLeave(i)}
              className="sxt-card group relative overflow-hidden rounded-xl border border-grid bg-card p-6 transition hover:border-cyan/30"
            >
              {/* Hover video preview (behind text) */}
              <video
                ref={(el) => {
                  videoRefs.current[i] = el;
                }}
                src="/videos/animatie2.mp4"
                muted
                loop
                playsInline
                preload="none"
                aria-hidden="true"
                tabIndex={-1}
                className="sxt-card-video pointer-events-none absolute inset-0 z-0 h-full w-full rounded-[inherit] object-cover opacity-0 transition-opacity duration-300"
              />
              {/* Dark overlay to keep text readable while video plays */}
              <div className="sxt-card-scrim pointer-events-none absolute inset-0 z-[1] rounded-[inherit] bg-card/55 opacity-0 transition-opacity duration-300" />

              <div className="relative z-[2]">
                <Icon className="h-7 w-7 text-cyan" strokeWidth={2} />
                <h3 className="sxt-card-title mt-4 font-display text-lg font-bold text-ink">
                  {card.title}
                </h3>
                <p className="mt-2 text-[15px] leading-relaxed text-ink-muted">
                  {card.text}
                </p>
              </div>
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
        <Link
          href="/contact"
          className="inline-flex items-center gap-1.5 text-[15px] font-semibold text-cyan transition-colors hover:text-cyan/80"
        >
          {t("cta")}
          <ArrowRight className="h-4 w-4" strokeWidth={2} />
        </Link>
      </motion.div>

      <style>{`
        .sxt-card {
          transition: transform 300ms ease, box-shadow 300ms ease, border-color 300ms ease;
        }
        .sxt-card-title {
          transition: transform 300ms ease;
        }
        .sxt-card:hover {
          transform: scale(1.02);
          box-shadow: 0 0 20px rgba(6, 182, 212, 0.4);
        }
        .sxt-card:hover .sxt-card-video {
          opacity: 0.3;
        }
        .sxt-card:hover .sxt-card-scrim {
          opacity: 1;
        }
        .sxt-card:hover .sxt-card-title {
          transform: translateY(-8px);
        }
        @media (hover: none) {
          /* Mobile: keep only the border glow, no video / no transforms. */
          .sxt-card:hover {
            transform: none;
          }
          .sxt-card:hover .sxt-card-video,
          .sxt-card:hover .sxt-card-scrim {
            opacity: 0;
          }
          .sxt-card:hover .sxt-card-title {
            transform: none;
          }
        }
        @media (prefers-reduced-motion: reduce) {
          .sxt-card,
          .sxt-card-title {
            transition: none;
          }
          .sxt-card:hover {
            transform: none;
          }
          .sxt-card:hover .sxt-card-title {
            transform: none;
          }
        }
      `}</style>
    </section>
  );
}
