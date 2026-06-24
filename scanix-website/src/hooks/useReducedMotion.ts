"use client";

import { useEffect, useState } from "react";

/**
 * True when the user prefers reduced motion. Every video/scroll animation in
 * the site checks this and skips (renders a static fallback) when it's true.
 * SSR-safe: returns false until mounted, then syncs with the media query.
 */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  return reduced;
}
