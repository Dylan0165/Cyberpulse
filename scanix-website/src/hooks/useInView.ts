"use client";

import { useEffect, useRef, useState } from "react";

interface UseInViewOptions {
  threshold?: number;
  rootMargin?: string;
  /** Stop observing after the first time the element enters the viewport. */
  once?: boolean;
}

/**
 * Thin IntersectionObserver wrapper. Returns `[ref, inView]`.
 * SSR-safe (no observer until mounted) and self-cleaning on unmount.
 */
export function useInView<T extends Element = HTMLDivElement>(
  opts: UseInViewOptions = {},
): [React.RefObject<T>, boolean] {
  const { threshold = 0.25, rootMargin = "0px", once = true } = opts;
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
