"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";

/**
 * Lazy step video: nothing downloads (preload="none") until the section scrolls
 * into view, at which point the IntersectionObserver starts playback. Pauses
 * again when scrolled away to save CPU/battery.
 */
function StepVideo({ src }: { src: string }) {
  const ref = useRef<HTMLVideoElement>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.play().catch(() => {});
        } else {
          el.pause();
        }
      },
      { threshold: 0.3 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div className="relative mx-auto aspect-square w-full max-w-[280px] overflow-hidden rounded-2xl border border-cyan-500/30">
      {/* Loading skeleton: shimmer placeholder shown until the first frame is
          ready, then hidden so it never lingers over the playing video. */}
      {!ready && (
        <div className="sxw-how-skeleton pointer-events-none absolute inset-0 bg-grid" />
      )}
      <video
        ref={ref}
        src={src}
        autoPlay
        muted
        loop
        playsInline
        preload="none"
        onCanPlay={() => setReady(true)}
        className="h-full w-full object-cover"
      />
      <style>{`
        @keyframes sxw-how-shimmer {
          0% { background-position: -150% 0; }
          100% { background-position: 250% 0; }
        }
        .sxw-how-skeleton {
          background-image: linear-gradient(
            110deg,
            rgba(13, 31, 53, 0) 20%,
            rgba(0, 180, 216, 0.18) 50%,
            rgba(13, 31, 53, 0) 80%
          );
          background-size: 200% 100%;
          animation: sxw-how-shimmer 1.6s linear infinite;
        }
      `}</style>
    </div>
  );
}

export function HowItWorks() {
  const t = useTranslations("how");

  const steps = [
    { number: "01", video: "/videos/animatie1.mp4", title: t("step1Title"), text: t("step1Text") },
    { number: "02", video: "/videos/animatie3.mp4", title: t("step2Title"), text: t("step2Text") },
    { number: "03", video: "/videos/animatie2.mp4", title: t("step3Title"), text: t("step3Text") },
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

      <div className="mt-12 grid grid-cols-1 gap-8 md:grid-cols-3 md:gap-6">
        {steps.map((step, i) => (
          <motion.div
            key={step.number}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: i * 0.08 }}
            className="relative"
          >
            <StepVideo src={step.video} />

            <p className="mt-5 font-mono text-sm text-ink-muted/40">{step.number}</p>
            <h3 className="mt-1 font-display text-xl font-bold text-ink">{step.title}</h3>
            <p className="mt-2 text-[15px] leading-relaxed text-ink-muted">{step.text}</p>

            {i < steps.length - 1 && (
              <ArrowRight
                className="absolute -right-4 top-[130px] hidden h-5 w-5 text-ink-muted/30 md:block"
                strokeWidth={2}
              />
            )}
          </motion.div>
        ))}
      </div>
    </section>
  );
}
