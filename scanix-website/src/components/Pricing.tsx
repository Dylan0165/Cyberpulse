"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { motion } from "framer-motion";
import {
  Check, ArrowRight, Zap, Star, ShieldCheck, Plus, Minus,
} from "lucide-react";
import { Link } from "@/lib/navigation";
import { useReducedMotion } from "@/hooks/useReducedMotion";
import { useScrollProgress } from "@/hooks/useScrollProgress";
import { APP_URL } from "@/lib/appUrl";

const APP_BILLING = `${APP_URL}/billing`;

type Pkg = {
  key: string;
  name: string;
  credits: number;
  price: string; // display euros
  perScan: string; // display euros
  save?: string;
  popular?: boolean;
  gold?: boolean; // best-value (Expert) — gold border
};

export function Pricing() {
  const t = useTranslations("pricing");
  const tf = useTranslations("faq");

  const reduced = useReducedMotion();
  const [bannerRef, bannerProgress] = useScrollProgress<HTMLDivElement>();

  const headline = t("headline");

  // Typewriter for the banner headline on mount.
  const [typed, setTyped] = useState(0);
  useEffect(() => {
    if (reduced) {
      setTyped(headline.length);
      return;
    }
    setTyped(0);
    let i = 0;
    const id = window.setInterval(() => {
      i += 1;
      setTyped(i);
      if (i >= headline.length) window.clearInterval(id);
    }, 75);
    return () => window.clearInterval(id);
  }, [reduced, headline]);

  const bannerShift = reduced ? 0 : bannerProgress * -40;

  const packages: Pkg[] = [
    { key: "losse_scan", name: t("pkgLosseScan"), credits: 1, price: "€100", perScan: "€100" },
    { key: "starter", name: t("pkgStarter"), credits: 3, price: "€250", perScan: "€83", save: t("saveStarter") },
    { key: "groei", name: t("pkgGroei"), credits: 5, price: "€375", perScan: "€75", save: t("saveGroei"), popular: true },
    { key: "pro", name: t("pkgPro"), credits: 10, price: "€650", perScan: "€65", save: t("savePro") },
    { key: "expert", name: t("pkgExpert"), credits: 25, price: "€1.250", perScan: "€50", save: t("saveExpert"), gold: true },
  ];

  const subscriptions = [
    {
      name: t("businessName"),
      price: t("businessPrice"),
      feats: [t("businessF1"), t("businessF2"), t("businessF3")],
    },
    {
      name: t("enterpriseName"),
      price: t("enterprisePrice"),
      feats: [t("enterpriseF1"), t("enterpriseF2"), t("enterpriseF3")],
    },
  ];

  const trust = [t("trust1"), t("trust2"), t("trust3"), t("trust4"), t("trust5")];

  const faqs = [
    { q: tf("q1"), a: tf("a1") },
    { q: tf("q2"), a: tf("a2") },
    { q: tf("q3"), a: tf("a3") },
    { q: tf("q4"), a: tf("a4") },
    { q: tf("q5"), a: tf("a5") },
  ];

  const [open, setOpen] = useState<number | null>(0);

  return (
    <section id="pricing" className="relative mx-auto max-w-content px-5 py-20 md:px-8 md:py-28">
      {/* Cinematic banner: demo1 with a parallax drift + typewriter headline. */}
      <div
        ref={bannerRef}
        className="relative mb-14 h-40 overflow-hidden rounded-2xl border border-grid md:h-48"
      >
        {!reduced && (
          <video
            src="/videos/demo1.mp4"
            autoPlay
            muted
            loop
            playsInline
            preload="none"
            aria-hidden="true"
            tabIndex={-1}
            style={{ transform: `translateY(${bannerShift}px) scale(1.12)` }}
            className="absolute inset-0 hidden h-full w-full object-cover opacity-40 md:block"
          />
        )}
        <img
          src="/videos/posters/poster-demo1.jpg"
          alt=""
          style={reduced ? undefined : { transform: `translateY(${bannerShift}px) scale(1.12)` }}
          className={`absolute inset-0 h-full w-full object-cover opacity-40 ${
            reduced ? "" : "md:hidden"
          }`}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-bg via-bg/60 to-bg/30" />
        <div className="relative z-10 flex h-full items-center justify-center px-5">
          <span className="font-display text-3xl font-bold tracking-tight text-ink md:text-4xl">
            {headline.slice(0, typed)}
            <span className="sxw-caret text-cyan" aria-hidden="true">
              |
            </span>
          </span>
        </div>
      </div>

      <div className="text-center">
        <h2 className="font-display text-3xl font-bold tracking-tight text-ink md:text-4xl">{t("title")}</h2>
        <p className="mx-auto mt-3 max-w-xl text-[15px] text-ink-muted">{t("subtitle")}</p>
      </div>

      {/* Credit package cards */}
      <div className="mx-auto mt-12 grid max-w-5xl gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {packages.map((p, i) => (
          <motion.div
            key={p.key}
            initial={{ opacity: 0, y: 60 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{
              duration: 0.5,
              delay: i * 0.08,
              ease: [0.16, 1, 0.3, 1],
            }}
            className={`relative flex flex-col rounded-2xl border bg-card p-6 ${
              p.popular
                ? "sxw-grad-border border-transparent shadow-glow-cyan"
                : p.gold
                ? "border-amber-400/60 bg-amber-400/[0.03]"
                : "border-grid"
            }`}
          >
            {p.popular && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 inline-flex items-center gap-1 whitespace-nowrap rounded-full bg-cyan px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-bg">
                <Star className="h-3 w-3" fill="currentColor" /> {t("popular")}
              </span>
            )}
            {p.gold && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 inline-flex items-center gap-1 whitespace-nowrap rounded-full bg-amber-400 px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-bg">
                <Star className="h-3 w-3" fill="currentColor" /> {t("bestValue")}
              </span>
            )}
            <h3 className="font-display text-[17px] font-semibold text-ink">{p.name}</h3>

            <div className="mt-3 flex items-baseline gap-1">
              <span className="font-display text-3xl font-bold text-ink">{p.price}</span>
            </div>

            <div className="mt-3 flex items-center gap-2 text-cyan">
              <Zap className="h-4 w-4" fill="currentColor" strokeWidth={2} />
              <span className="font-mono text-[14px] font-semibold">
                {p.credits} {p.credits === 1 ? t("credit") : t("credits")}
              </span>
            </div>

            <p className="mt-1.5 font-mono text-[12px] text-ink-muted">
              {p.perScan} {t("perScan")}
            </p>

            {p.save && (
              <span className="mt-3 inline-flex w-fit rounded-full bg-green/10 px-2.5 py-1 text-[11px] font-semibold text-green">
                {p.save}
              </span>
            )}

            <div className="mt-4 flex items-center gap-1.5 text-[12px] text-ink-muted">
              <Check className="h-3.5 w-3.5 flex-shrink-0 text-green" strokeWidth={2.5} />
              {t("neverExpire")}
            </div>

            <Link
              href={`${APP_BILLING}?package=${p.key}`}
              className={`mt-6 inline-flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-[13.5px] font-semibold transition-all active:scale-[0.98] ${
                p.popular
                  ? "bg-cyan text-bg hover:shadow-glow-cyan"
                  : p.gold
                  ? "bg-amber-400 text-bg hover:brightness-110"
                  : "border border-grid text-ink hover:border-cyan/40"
              }`}
            >
              {t("buyCta")} <ArrowRight className="h-4 w-4" strokeWidth={2} />
            </Link>
          </motion.div>
        ))}
      </div>

      <p className="mt-4 text-center text-[11px] text-ink-muted">{t("loginNote")}</p>

      {/* Trust badges */}
      <div className="mx-auto mt-10 flex max-w-4xl flex-wrap items-center justify-center gap-x-6 gap-y-2.5">
        {trust.map((item) => (
          <span key={item} className="inline-flex items-center gap-1.5 text-[12.5px] text-ink-muted">
            <Check className="h-4 w-4 flex-shrink-0 text-cyan" strokeWidth={2.5} />
            {item}
          </span>
        ))}
      </div>

      {/* Subscriptions — for heavy users */}
      <div className="mx-auto mt-20 max-w-3xl text-center">
        <h3 className="font-display text-2xl font-bold tracking-tight text-ink">{t("subsTitle")}</h3>
        <p className="mx-auto mt-2 max-w-lg text-[14px] text-ink-muted">{t("subsSubtitle")}</p>
      </div>

      <div className="mx-auto mt-8 grid max-w-3xl gap-5 md:grid-cols-2">
        {subscriptions.map((s) => (
          <div key={s.name} className="flex flex-col rounded-2xl border border-grid bg-card p-6">
            <div className="flex items-baseline justify-between">
              <h4 className="font-display text-[17px] font-semibold text-ink">{s.name}</h4>
              <span className="font-display text-xl font-bold text-ink">{s.price}</span>
            </div>
            <ul className="mt-4 flex-1 space-y-2">
              {s.feats.map((f) => (
                <li key={f} className="flex items-start gap-2 text-[13.5px] text-ink">
                  <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-green" strokeWidth={2} />
                  {f}
                </li>
              ))}
            </ul>
            <Link
              href="/contact"
              className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-grid px-4 py-2.5 text-[13.5px] font-semibold text-ink transition-all hover:border-cyan/40 active:scale-[0.98]"
            >
              {t("subsCta")} <ArrowRight className="h-4 w-4" strokeWidth={2} />
            </Link>
          </div>
        ))}
      </div>

      {/* FAQ */}
      <div className="mx-auto mt-20 max-w-3xl">
        <h3 className="text-center font-display text-2xl font-bold tracking-tight text-ink">
          {tf("title")}
        </h3>
        <div className="mt-8 divide-y divide-grid overflow-hidden rounded-2xl border border-grid">
          {faqs.map((f, i) => {
            const isOpen = open === i;
            return (
              <div key={f.q} className="bg-card">
                <button
                  type="button"
                  onClick={() => setOpen(isOpen ? null : i)}
                  aria-expanded={isOpen}
                  className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
                >
                  <span className="text-[14.5px] font-semibold text-ink">{f.q}</span>
                  {isOpen ? (
                    <Minus className="h-4 w-4 flex-shrink-0 text-cyan" strokeWidth={2.5} />
                  ) : (
                    <Plus className="h-4 w-4 flex-shrink-0 text-ink-muted" strokeWidth={2.5} />
                  )}
                </button>
                {isOpen && (
                  <motion.p
                    initial={reduced ? false : { opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    className="px-5 pb-4 text-[13.5px] leading-relaxed text-ink-muted"
                  >
                    {f.a}
                  </motion.p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <style>{`
        @property --sxw-angle {
          syntax: "<angle>";
          inherits: false;
          initial-value: 0deg;
        }
        .sxw-grad-border::before {
          content: "";
          position: absolute;
          inset: 0;
          border-radius: inherit;
          padding: 1.5px;
          background: conic-gradient(
            from var(--sxw-angle),
            #00B4D8,
            #00FF88,
            #0A84FF,
            #00B4D8
          );
          -webkit-mask:
            linear-gradient(#000 0 0) content-box,
            linear-gradient(#000 0 0);
          -webkit-mask-composite: xor;
                  mask-composite: exclude;
          animation: sxw-rotate-border 3s linear infinite;
          pointer-events: none;
        }
        @keyframes sxw-rotate-border {
          to { --sxw-angle: 360deg; }
        }
        .sxw-caret {
          margin-left: 2px;
          animation: sxw-caret-blink 1s step-end infinite;
        }
        @keyframes sxw-caret-blink {
          50% { opacity: 0; }
        }
        @media (prefers-reduced-motion: reduce) {
          .sxw-grad-border::before { animation: none; }
          .sxw-caret { animation: none; opacity: 0; }
        }
      `}</style>
    </section>
  );
}
