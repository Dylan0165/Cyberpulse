"use client";

import { Link } from "@/lib/navigation";
import { ArrowRight } from "lucide-react";
import { VideoBackground } from "./video/VideoBackground";

/**
 * Cinematic "wipe" section that sits just above the footer on the homepage.
 * A high-opacity background video with a radial vignette frames a big CTA whose
 * button breathes subtly. Copy is intentionally hardcoded (default-locale NL)
 * so no next-intl message keys are added/changed.
 */
export function CinematicCta() {
  return (
    <section className="relative overflow-hidden border-t border-grid">
      <VideoBackground
        src="/videos/animatie3.mp4"
        poster="/videos/posters/poster3.jpg"
        overlayClassName="bg-black/55"
        videoOpacityClassName="opacity-70"
      />
      {/* Vignette — black at the edges, transparent in the centre. */}
      <div
        className="pointer-events-none absolute inset-0 z-[1]"
        aria-hidden="true"
        style={{
          background:
            "radial-gradient(ellipse 70% 70% at 50% 50%, transparent 30%, rgba(2,4,8,0.85) 100%)",
        }}
      />

      <div className="relative z-10 mx-auto flex max-w-content flex-col items-center px-5 py-28 text-center md:px-8 md:py-36">
        <h2 className="max-w-3xl font-display text-4xl font-bold leading-tight tracking-tight text-ink md:text-5xl">
          Klaar om uw beveiliging te testen?
        </h2>
        <p className="mt-5 max-w-xl text-[17px] leading-relaxed text-ink-muted">
          Start vandaag nog uw eerste geautomatiseerde penetratietest — exacte
          bevindingen, exacte fixes.
        </p>
        <Link
          href="/contact"
          className="sxw-cta-pulse mt-9 inline-flex items-center gap-2 rounded-xl bg-cyan px-7 py-4 text-[16px] font-semibold text-bg transition-all hover:shadow-glow-cyan active:scale-[0.98]"
        >
          Plan een demo
          <ArrowRight className="h-5 w-5" strokeWidth={2} />
        </Link>
      </div>

      <style>{`
        .sxw-cta-pulse {
          animation: sxw-cta-pulse 2s ease-in-out infinite;
        }
        @keyframes sxw-cta-pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.03); }
        }
        @media (prefers-reduced-motion: reduce) {
          .sxw-cta-pulse { animation: none; }
        }
      `}</style>
    </section>
  );
}
