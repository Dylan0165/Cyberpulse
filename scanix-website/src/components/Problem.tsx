"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { motion } from "framer-motion";

type ParsedStat = {
  prefix: string;
  suffix: string;
  target: number;
  /** Whether the original numeric portion used a "." thousands separator. */
  grouped: boolean;
};

/**
 * Split a localized stat string (e.g. "€4.200", "68%", "287") into a numeric
 * target plus the non-numeric prefix/suffix so the count-up can re-format it.
 */
function parseStat(raw: string): ParsedStat {
  const match = raw.match(/[\d.,]*\d/);
  if (!match) {
    return { prefix: raw, suffix: "", target: 0, grouped: false };
  }
  const numericPart = match[0];
  const start = match.index ?? 0;
  const prefix = raw.slice(0, start);
  const suffix = raw.slice(start + numericPart.length);
  const grouped = numericPart.includes(".");
  // Strip the thousands separator to obtain the real integer value.
  const target = parseInt(numericPart.replace(/\./g, ""), 10);
  return {
    prefix,
    suffix,
    target: Number.isNaN(target) ? 0 : target,
    grouped,
  };
}

function formatValue(value: number, grouped: boolean): string {
  const rounded = Math.round(value);
  if (!grouped) return String(rounded);
  return rounded.toLocaleString("de-DE");
}

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

type CountUpProps = {
  raw: string;
  active: boolean;
  className?: string;
};

function CountUp({ raw, active, className }: CountUpProps) {
  const parsed = useRef<ParsedStat>(parseStat(raw));
  const [display, setDisplay] = useState<number>(0);

  useEffect(() => {
    parsed.current = parseStat(raw);
  }, [raw]);

  useEffect(() => {
    if (!active) return;

    const { target } = parsed.current;

    if (prefersReducedMotion()) {
      setDisplay(target);
      return;
    }

    const duration = 2000;
    let startTime: number | null = null;
    let frame = 0;

    const easeOut = (x: number): number => 1 - Math.pow(1 - x, 3);

    const tick = (now: number): void => {
      if (startTime === null) startTime = now;
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      setDisplay(target * easeOut(progress));
      if (progress < 1) {
        frame = requestAnimationFrame(tick);
      } else {
        setDisplay(target);
      }
    };

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [active]);

  const { prefix, suffix, grouped } = parsed.current;

  return (
    <span className={className}>
      {prefix}
      {formatValue(display, grouped)}
      {suffix}
    </span>
  );
}

export function Problem() {
  const t = useTranslations("problem");

  const sectionRef = useRef<HTMLElement | null>(null);
  const [inView, setInView] = useState<boolean>(false);

  useEffect(() => {
    const node = sectionRef.current;
    if (!node) return;

    if (typeof IntersectionObserver === "undefined") {
      setInView(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setInView(true);
            observer.disconnect();
            break;
          }
        }
      },
      { threshold: 0.3 }
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, []);

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
      ref={sectionRef}
      className="relative mx-auto max-w-content overflow-hidden px-5 py-20 md:px-8 md:py-28"
    >
      {/* Low-opacity background video */}
      <video
        src="/videos/demo2.mp4"
        autoPlay
        muted
        loop
        playsInline
        preload="none"
        aria-hidden="true"
        tabIndex={-1}
        className="pointer-events-none absolute inset-0 z-0 h-full w-full object-cover opacity-20"
      />

      {/* CSS-only floating particle overlay */}
      <div className="sxt-particles pointer-events-none absolute inset-0 z-[1]" aria-hidden="true">
        <span className="sxt-dot sxt-dot-1" />
        <span className="sxt-dot sxt-dot-2" />
        <span className="sxt-dot sxt-dot-3" />
        <span className="sxt-dot sxt-dot-4" />
        <span className="sxt-dot sxt-dot-5" />
        <span className="sxt-dot sxt-dot-6" />
      </div>

      <div className="relative z-[2]">
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
              <CountUp
                raw={card.number}
                active={inView}
                className={`font-display text-5xl font-bold ${card.color}`}
              />
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
      </div>

      <style>{`
        .sxt-dot {
          position: absolute;
          width: 6px;
          height: 6px;
          border-radius: 9999px;
          background: rgba(34, 211, 238, 0.35);
          opacity: 0;
          will-change: transform, opacity;
        }
        .sxt-dot-1 { left: 8%;  top: 70%; animation: sxt-drift 9s ease-in-out infinite; animation-delay: 0s; }
        .sxt-dot-2 { left: 24%; top: 85%; animation: sxt-drift 11s ease-in-out infinite; animation-delay: 1.4s; }
        .sxt-dot-3 { left: 45%; top: 78%; animation: sxt-drift 8s ease-in-out infinite; animation-delay: 0.7s; }
        .sxt-dot-4 { left: 63%; top: 88%; animation: sxt-drift 12s ease-in-out infinite; animation-delay: 2.1s; }
        .sxt-dot-5 { left: 80%; top: 72%; animation: sxt-drift 10s ease-in-out infinite; animation-delay: 1s; }
        .sxt-dot-6 { left: 92%; top: 82%; animation: sxt-drift 13s ease-in-out infinite; animation-delay: 3s; }

        @keyframes sxt-drift {
          0%   { transform: translate3d(0, 0, 0) scale(0.8); opacity: 0; }
          15%  { opacity: 0.7; }
          50%  { transform: translate3d(8px, -60px, 0) scale(1.1); opacity: 0.5; }
          85%  { opacity: 0.3; }
          100% { transform: translate3d(-6px, -120px, 0) scale(0.9); opacity: 0; }
        }

        @media (prefers-reduced-motion: reduce) {
          .sxt-dot { animation: none; opacity: 0.3; }
        }
      `}</style>
    </section>
  );
}
