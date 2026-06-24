"use client";

import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "@/hooks/useReducedMotion";

interface Scene {
  step: string;
  title: string;
  subtitle: string;
  video: string;
  poster: string;
}

const DEFAULT_SCENES: Scene[] = [
  {
    step: "Stap 1",
    title: "Verkenning",
    subtitle: "Wij scannen elk hoekje van uw infrastructuur.",
    video: "/videos/animatie1.mp4",
    poster: "/videos/posters/poster1.jpg",
  },
  {
    step: "Stap 2",
    title: "Aanval simulatie",
    subtitle: "17 offensieve modules testen uw zwakke plekken.",
    video: "/videos/animatie2.mp4",
    poster: "/videos/posters/poster2.jpg",
  },
  {
    step: "Stap 3",
    title: "Uw rapport",
    subtitle: "Exacte fixes, klaar om uit te voeren.",
    video: "/videos/animatie3.mp4",
    poster: "/videos/posters/poster3.jpg",
  },
];

/**
 * Pinned 3-scene scroll section. The outer wrapper is 300vh tall; an inner
 * sticky panel stays pinned for its full height while the page scrolls. We map
 * scroll position within the pinned range (0..1) to one of three "scenes",
 * cross-fading the videos and sliding the copy in from the left on each change.
 *
 * Reduced-motion / mobile: the videos are replaced by their static poster
 * frames and the copy switches without the slide animation. The scene still
 * advances with scroll (that is layout, not motion).
 */
export function StickyScrollScene({
  scenes = DEFAULT_SCENES,
}: {
  scenes?: Scene[];
}) {
  const reduced = useReducedMotion();
  const wrapRef = useRef<HTMLDivElement>(null);
  const videoRefs = useRef<Array<HTMLVideoElement | null>>([]);
  const [active, setActive] = useState(0);
  const rafRef = useRef<number | null>(null);

  // Map pinned-scroll position to the active scene index.
  useEffect(() => {
    if (typeof window === "undefined") return;

    const compute = () => {
      rafRef.current = null;
      const el = wrapRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const vh = window.innerHeight || 1;
      const scrollable = rect.height - vh;
      const progress = scrollable > 0 ? -rect.top / scrollable : 0;
      const clamped = progress < 0 ? 0 : progress > 1 ? 1 : progress;
      const idx = Math.min(scenes.length - 1, Math.floor(clamped * scenes.length));
      setActive((prev) => (prev === idx ? prev : idx));
    };

    const onScroll = () => {
      if (rafRef.current !== null) return;
      rafRef.current = window.requestAnimationFrame(compute);
    };

    compute();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (rafRef.current !== null) window.cancelAnimationFrame(rafRef.current);
    };
  }, [scenes.length]);

  // Play only the active scene's video; pause the rest.
  useEffect(() => {
    if (reduced) return;
    videoRefs.current.forEach((v, i) => {
      if (!v) return;
      if (i === active) {
        void v.play().catch(() => {
          /* autoplay interruption is non-fatal */
        });
      } else {
        v.pause();
      }
    });
  }, [active, reduced]);

  return (
    <section
      ref={wrapRef}
      aria-label="Hoe het werkt"
      className="relative"
      style={{ height: "300vh" }}
    >
      <div className="sticky top-0 flex h-screen items-center overflow-hidden">
        <div className="mx-auto grid w-full max-w-content items-center gap-8 px-5 md:px-8 lg:grid-cols-2 lg:gap-12">
          {/* Left: copy, slides in on each scene change (keyed remount). */}
          <div className="relative z-10 order-2 lg:order-1">
            <div key={active} className="sxw-scene-copy" data-reduced={reduced ? "1" : "0"}>
              <span className="font-mono text-[13px] uppercase tracking-[0.2em] text-cyan">
                {scenes[active].step}
              </span>
              <h2 className="mt-3 font-display text-4xl font-bold leading-tight tracking-tight text-ink md:text-5xl">
                {scenes[active].title}
              </h2>
              <p className="mt-4 max-w-md text-[18px] leading-relaxed text-ink-muted">
                {scenes[active].subtitle}
              </p>
              <div className="mt-8 flex items-center gap-2" aria-hidden="true">
                {scenes.map((_, i) => (
                  <span
                    key={i}
                    className={`h-1 rounded-full transition-all duration-500 ${
                      i === active ? "w-10 bg-cyan" : "w-4 bg-grid"
                    }`}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Right: cross-fading video stack. */}
          <div className="order-1 lg:order-2">
            <div className="relative aspect-video w-full overflow-hidden rounded-2xl border border-cyan/30 shadow-glow-cyan">
              {scenes.map((scene, i) => (
                <div
                  key={scene.video}
                  className="absolute inset-0 transition-opacity duration-[600ms]"
                  style={{ opacity: i === active ? 1 : 0 }}
                >
                  {reduced ? (
                    <img
                      src={scene.poster}
                      alt=""
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <video
                      ref={(el) => {
                        videoRefs.current[i] = el;
                      }}
                      src={scene.video}
                      poster={scene.poster}
                      muted
                      loop
                      playsInline
                      preload="none"
                      aria-hidden="true"
                      tabIndex={-1}
                      className="hidden h-full w-full object-cover md:block"
                    />
                  )}
                  {/* Mobile static poster (md:hidden) when not reduced. */}
                  {!reduced && (
                    <img
                      src={scene.poster}
                      alt=""
                      className="h-full w-full object-cover md:hidden"
                    />
                  )}
                </div>
              ))}
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-bg/40 to-transparent" />
            </div>
          </div>
        </div>
      </div>

      <style>{`
        .sxw-scene-copy {
          animation: sxw-scene-in 0.55s cubic-bezier(0.16, 1, 0.3, 1) both;
        }
        .sxw-scene-copy[data-reduced="1"] {
          animation: none;
        }
        @keyframes sxw-scene-in {
          from { opacity: 0; transform: translateX(-40px); }
          to   { opacity: 1; transform: translateX(0); }
        }
      `}</style>
    </section>
  );
}
