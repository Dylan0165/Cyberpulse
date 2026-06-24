"use client";

import { useEffect, useRef } from "react";
import { useReducedMotion } from "./useReducedMotion";

interface UseVideoScrubOptions {
  /**
   * Fraction of page scroll progress (0..1) at which the video reaches its
   * final frame. Default 0.6 → at 60% scroll the video is at the end, matching
   * the hero spec (0% = frame 0, 30% = halfway, 60% = near end).
   */
  endAt?: number;
}

/**
 * Scrub a <video> element's currentTime from page scroll instead of playing it.
 * Returns a ref to attach to the video. The video must be muted + playsInline
 * and should NOT autoplay — we drive currentTime ourselves inside a single
 * rAF loop, so scrubbing stays smooth and never blocks the scroll thread.
 *
 * Does nothing when the user prefers reduced motion (the caller shows a static
 * frame / poster instead).
 */
export function useVideoScrub<T extends HTMLVideoElement = HTMLVideoElement>({
  endAt = 0.6,
}: UseVideoScrubOptions = {}): React.RefObject<T> {
  const ref = useRef<T>(null);
  const reduced = useReducedMotion();

  useEffect(() => {
    if (reduced) return;
    if (typeof window === "undefined") return;
    const video = ref.current;
    if (!video) return;

    let rafId: number | null = null;
    let targetTime = 0;

    const computeTarget = () => {
      const doc = document.documentElement;
      const scrollable = doc.scrollHeight - window.innerHeight;
      const scrolled = scrollable > 0 ? window.scrollY / scrollable : 0;
      const norm = Math.min(1, scrolled / Math.max(0.0001, endAt));
      const duration = Number.isFinite(video.duration) ? video.duration : 0;
      targetTime = norm * duration;
    };

    // Smoothly chase the scroll target so fast scrolls don't snap the frame.
    const loop = () => {
      const current = video.currentTime;
      const next = current + (targetTime - current) * 0.18;
      if (Math.abs(next - current) > 0.005 && Number.isFinite(next)) {
        try {
          video.currentTime = next;
        } catch {
          /* seeking not ready yet */
        }
      }
      rafId = window.requestAnimationFrame(loop);
    };

    const onScroll = () => computeTarget();

    const start = () => {
      try {
        video.pause();
      } catch {
        /* ignore */
      }
      computeTarget();
      if (rafId === null) rafId = window.requestAnimationFrame(loop);
    };

    if (video.readyState >= 1) start();
    else video.addEventListener("loadedmetadata", start, { once: true });

    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });

    return () => {
      if (rafId !== null) window.cancelAnimationFrame(rafId);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      video.removeEventListener("loadedmetadata", start);
    };
  }, [reduced, endAt]);

  return ref;
}
