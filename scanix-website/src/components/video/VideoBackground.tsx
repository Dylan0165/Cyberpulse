"use client";

import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "@/hooks/useReducedMotion";

type VideoBackgroundProps = {
  src: string;
  /** Static frame shown on mobile, on reduced-motion and on error. */
  poster?: string;
  className?: string;
  overlayClassName?: string;
  /** Tailwind opacity class for the video/poster, e.g. "opacity-100" or "opacity-25". */
  videoOpacityClassName?: string;
};

/**
 * Reusable full-bleed background video.
 *
 * - Lazy: `preload="none"` and the <video> only mounts once the section nears
 *   the viewport (IntersectionObserver), so off-screen sections never fetch it.
 * - Mobile (< 768px) and reduced-motion: renders the static `poster` image
 *   instead of the video (no autoplay, no decode cost).
 * - Fades in when the browser can render a frame; on any load error it falls
 *   back to the poster / gradient so the section never renders empty.
 *
 * Everything is pointer-events-none so it sits purely behind real content.
 */
export function VideoBackground({
  src,
  poster,
  className,
  overlayClassName,
  videoOpacityClassName = "opacity-100",
}: VideoBackgroundProps) {
  const reduced = useReducedMotion();
  const containerRef = useRef<HTMLDivElement>(null);
  const [inView, setInView] = useState(false);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);

  // Only mount the video element once the section is near/in the viewport.
  useEffect(() => {
    const el = containerRef.current;
    if (!el || typeof IntersectionObserver === "undefined") {
      setInView(true);
      return;
    }
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          obs.disconnect();
        }
      },
      { rootMargin: "200px" },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const showVideo = inView && !reduced && !failed;

  return (
    <div
      ref={containerRef}
      aria-hidden
      className={`pointer-events-none absolute inset-0 overflow-hidden ${className ?? ""}`}
    >
      {/* Gradient base — there is never an empty frame behind the poster/video. */}
      <div className="absolute inset-0 bg-gradient-to-b from-bg via-bg-secondary to-bg" />

      {/* Static poster: always on mobile; on md+ only when the video is absent. */}
      {poster && (
        <img
          src={poster}
          alt=""
          className={`absolute inset-0 h-full w-full object-cover ${videoOpacityClassName} ${
            reduced || failed ? "" : "md:hidden"
          }`}
        />
      )}

      {/* Video: md+ only, lazily mounted. */}
      {showVideo && (
        <video
          autoPlay
          muted
          loop
          playsInline
          preload="none"
          poster={poster}
          onCanPlay={() => setReady(true)}
          onLoadedData={() => setReady(true)}
          onError={() => setFailed(true)}
          className={`absolute inset-0 hidden h-full w-full object-cover transition-opacity duration-[1500ms] md:block ${videoOpacityClassName} ${
            ready ? "opacity-100" : "opacity-0"
          }`}
        >
          <source src={src} type="video/mp4" />
        </video>
      )}

      <div className={`absolute inset-0 ${overlayClassName ?? "bg-black/60"}`} />
    </div>
  );
}
