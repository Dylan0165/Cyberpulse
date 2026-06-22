"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Observe whether an element is in the viewport.
 * Returns [ref, inView]. SSR-safe (no observer until mounted).
 */
export function useIntersection<T extends Element = HTMLDivElement>(
  opts: { threshold?: number; rootMargin?: string; once?: boolean } = {},
): [React.RefObject<T>, boolean] {
  const { threshold = 0.3, rootMargin = "0px", once = false } = opts;
  const ref = useRef<T>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          if (once) observer.disconnect();
        } else if (!once) {
          setInView(false);
        }
      },
      { threshold, rootMargin },
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [threshold, rootMargin, once]);

  return [ref, inView];
}
