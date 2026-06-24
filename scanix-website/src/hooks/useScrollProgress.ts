"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Scroll progress (0..1) of a target element relative to the viewport.
 *
 * - `0` while the element's top edge is at/below the bottom of the viewport
 *   (i.e. just about to enter, or the page is at the element's start).
 * - `1` once the element's bottom edge has scrolled past the top of the
 *   viewport (fully passed).
 *
 * When no ref is attached the hook falls back to whole-document progress
 * (scrollY / scrollable height), which is what the hero scrubbing uses.
 *
 * Updates are rAF-throttled so the scroll listener never causes jank.
 */
export function useScrollProgress<T extends HTMLElement = HTMLDivElement>(): [
  React.RefObject<T>,
  number,
] {
  const ref = useRef<T>(null);
  const [progress, setProgress] = useState(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const compute = () => {
      rafRef.current = null;
      const el = ref.current;
      const vh = window.innerHeight || 1;

      if (el) {
        const rect = el.getBoundingClientRect();
        // Distance the element travels from "top entering" to "bottom leaving".
        const total = rect.height + vh;
        const passed = vh - rect.top;
        const p = passed / total;
        setProgress(p < 0 ? 0 : p > 1 ? 1 : p);
      } else {
        const doc = document.documentElement;
        const scrollable = doc.scrollHeight - vh;
        const p = scrollable > 0 ? window.scrollY / scrollable : 0;
        setProgress(p < 0 ? 0 : p > 1 ? 1 : p);
      }
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
  }, []);

  return [ref, progress];
}
