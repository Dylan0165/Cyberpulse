"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { motion, useInView } from "framer-motion";
import { Lock, ArrowRight, ArrowDown, Check } from "lucide-react";
import { Link } from "@/lib/navigation";
import { useVideoScrub } from "@/hooks/useVideoScrub";
import { useReducedMotion } from "@/hooks/useReducedMotion";

const APP_URL = "https://app.scanix.nl";

function useCountUp(target: number, run: boolean, duration = 1400) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!run) return;
    let raf = 0;
    let start: number | null = null;
    const tick = (ts: number) => {
      if (start === null) start = ts;
      const p = Math.min((ts - start) / duration, 1);
      // easeOutCubic
      const eased = 1 - Math.pow(1 - p, 3);
      setValue(Math.round(eased * target));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, run, duration]);
  return value;
}

function MockGauge({ run }: { run: boolean }) {
  const score = useCountUp(72, run);
  const size = 132;
  const stroke = 11;
  const r = (size - stroke) / 2;
  const c = size / 2;
  const circ = 2 * Math.PI * r;
  const sweep = 270;
  const arc = (sweep / 360) * circ;
  const progress = (score / 100) * arc;

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(135deg)" }}>
        <circle cx={c} cy={c} r={r} fill="none" stroke="#0D1F35" strokeWidth={stroke} strokeDasharray={`${arc} ${circ}`} strokeLinecap="round" />
        <circle cx={c} cy={c} r={r} fill="none" stroke="#FF2D55" strokeWidth={stroke} strokeDasharray={`${progress} ${circ}`} strokeLinecap="round" style={{ transition: "stroke-dasharray 0.1s linear" }} />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="font-display text-[40px] font-bold leading-none text-red">{score}</span>
        <span className="mt-1 font-mono text-[9px] uppercase tracking-[0.18em] text-ink-muted">score</span>
      </div>
    </div>
  );
}

function MockCard() {
  const t = useTranslations("hero");
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });

  const findings = [
    { label: t("mockCritical"), count: 2, color: "#FF2D55" },
    { label: t("mockHigh"), count: 1, color: "#FF8C00" },
    { label: t("mockMedium"), count: 2, color: "#FFD60A" },
  ];

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 24, rotateX: 8 }}
      animate={inView ? { opacity: 1, y: 0, rotateX: 0 } : {}}
      transition={{ type: "spring", stiffness: 90, damping: 18 }}
      className="relative w-full max-w-[400px] rounded-2xl border border-grid bg-card/90 p-6 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.7)] backdrop-blur-sm"
    >
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-widest text-ink-muted">target</p>
          <p className="mt-0.5 font-mono text-[14px] text-ink">{t("mockTarget")}</p>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-green/30 bg-green/10 px-2.5 py-1 text-[11px] font-medium text-green">
          <Check className="h-3 w-3" strokeWidth={2.5} />
          {t("mockStatus")}
        </span>
      </div>

      <div className="flex items-center gap-5">
        <MockGauge run={inView} />
        <div className="flex-1 space-y-2">
          <p className="font-mono text-[10px] uppercase tracking-widest text-ink-muted">{t("mockFindingsLabel")}</p>
          {findings.map((f, i) => (
            <motion.div
              key={f.label}
              initial={{ opacity: 0, x: 12 }}
              animate={inView ? { opacity: 1, x: 0 } : {}}
              transition={{ delay: 0.6 + i * 0.18, type: "spring", stiffness: 200, damping: 22 }}
              className="flex items-center justify-between rounded-lg border border-grid bg-bg-secondary px-3 py-1.5"
            >
              <span className="flex items-center gap-2 text-[12px] text-ink">
                <span className="h-2 w-2 rounded-full" style={{ background: f.color }} />
                {f.label}
              </span>
              <span className="font-mono text-[13px] font-semibold" style={{ color: f.color }}>{f.count}</span>
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

export function Hero() {
  const t = useTranslations("hero");
  const trust = [t("trust1"), t("trust2"), t("trust3")];

  const reduced = useReducedMotion();
  // animatie1 is scrubbed by scroll (0% = frame 0, ~60% = end), not played.
  const scrubRef = useVideoScrub<HTMLVideoElement>({ endAt: 0.6 });
  // Parallax: hero copy drifts slower than the background video as you scroll.
  const [parallax, setParallax] = useState(0);
  useEffect(() => {
    if (reduced) return;
    let raf = 0;
    const onScroll = () => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = 0;
        setParallax(window.scrollY * 0.25);
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [reduced]);

  // If the visitor already has a valid dashboard session (cookie on app.scanix.nl),
  // swap the primary CTA for a "go to dashboard" link. Cross-domain, so we ask the
  // app via a credentialed ping rather than reading localStorage. Fails silently.
  const [loggedIn, setLoggedIn] = useState(false);
  useEffect(() => {
    let active = true;
    fetch(`${APP_URL}/api/auth/me`, { credentials: "include" })
      .then((r) => {
        if (active && r.ok) setLoggedIn(true);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="relative min-h-[100dvh] overflow-hidden pt-10">
      {/* Scroll-scrubbed background video (animatie1) on md+, static poster on mobile. */}
      <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-bg via-bg-secondary to-bg" />
        {!reduced && (
          <video
            ref={scrubRef}
            src="/videos/animatie1.mp4"
            poster="/videos/posters/poster1.jpg"
            muted
            playsInline
            preload="metadata"
            tabIndex={-1}
            className="absolute inset-0 hidden h-full w-full object-cover md:block"
          />
        )}
        <img
          src="/videos/posters/poster1.jpg"
          alt=""
          className={`absolute inset-0 h-full w-full object-cover ${reduced ? "" : "md:hidden"}`}
        />
      </div>
      {/* Spec overlay: top→bottom darken so the hero copy stays readable. */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-black/70 via-black/40 to-black/80" />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-bg/80 via-bg/40 to-transparent" />

      <div className="glow-accent left-[-10%] top-[-5%] h-[420px] w-[420px] bg-cyan" />
      <div
        style={{ transform: `translateY(${parallax}px)` }}
        className="relative z-10 mx-auto grid max-w-content items-center gap-12 px-5 py-16 md:px-8 lg:grid-cols-2 lg:gap-8 lg:py-24"
      >
        {/* Left: content */}
        <div>
          <motion.span
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="inline-flex items-center gap-2 rounded-full border border-cyan/25 bg-cyan/5 px-3 py-1.5 text-[12px] font-medium text-cyan"
          >
            <Lock className="h-3.5 w-3.5" strokeWidth={2} />
            {t("badge")}
          </motion.span>

          <motion.h1
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.05 }}
            className="mt-5 font-display text-4xl font-bold leading-[1.05] tracking-tight text-ink sm:text-5xl lg:text-6xl"
          >
            {t("h1Line1")}
            <br />
            <span className="text-cyan">{t("h1Line2")}</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.12 }}
            className="mt-6 max-w-[600px] text-[17px] leading-relaxed text-ink-muted"
          >
            {t("subtitle")}
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="mt-8 flex flex-wrap gap-3"
          >
            {loggedIn ? (
              <a
                href={`${APP_URL}/dashboard`}
                className="inline-flex items-center gap-2 rounded-xl bg-cyan px-6 py-3.5 text-[15px] font-semibold text-bg transition-all hover:shadow-glow-cyan active:scale-[0.98]"
              >
                {t("ctaDashboard")}
                <ArrowRight className="h-4.5 w-4.5" strokeWidth={2} />
              </a>
            ) : (
              <Link
                href="/contact"
                className="inline-flex items-center gap-2 rounded-xl bg-cyan px-6 py-3.5 text-[15px] font-semibold text-bg transition-all hover:shadow-glow-cyan active:scale-[0.98]"
              >
                {t("ctaPrimary")}
                <ArrowRight className="h-4.5 w-4.5" strokeWidth={2} />
              </Link>
            )}
            <Link
              href="/demo"
              className="inline-flex items-center gap-2 rounded-xl border border-cyan/40 bg-cyan/5 px-6 py-3.5 text-[15px] font-semibold text-cyan transition-colors hover:border-cyan/60 active:scale-[0.98]"
            >
              {t("ctaDemo")}
            </Link>
            <Link
              href="/hoe-het-werkt"
              className="inline-flex items-center gap-2 rounded-xl border border-grid bg-card px-6 py-3.5 text-[15px] font-semibold text-ink transition-colors hover:border-cyan/40 active:scale-[0.98]"
            >
              {t("ctaSecondary")}
              <ArrowDown className="h-4.5 w-4.5" strokeWidth={2} />
            </Link>
          </motion.div>

          <motion.ul
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.32 }}
            className="mt-9 flex flex-col gap-2.5"
          >
            {trust.map((item) => (
              <li key={item} className="flex items-center gap-2.5 text-[14px] text-ink-muted">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-green/10">
                  <Check className="h-3 w-3 text-green" strokeWidth={3} />
                </span>
                {item}
              </li>
            ))}
          </motion.ul>
        </div>

        {/* Right: mock card */}
        <div className="flex justify-center lg:justify-end">
          <MockCard />
        </div>
      </div>
    </section>
  );
}
