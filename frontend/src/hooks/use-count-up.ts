"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Animate a number from 0 (or `from`) to `value` with an ease-out curve.
 * Returns the current animated value. Respects prefers-reduced-motion.
 */
export function useCountUp(value: number, durationMs = 1200, from = 0): number {
  const [display, setDisplay] = useState(from);
  const frame = useRef<number>();
  const startTime = useRef<number>();

  useEffect(() => {
    if (typeof window === "undefined") {
      setDisplay(value);
      return;
    }
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
    if (reduce || !Number.isFinite(value)) {
      setDisplay(value);
      return;
    }

    startTime.current = undefined;
    const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);

    const tick = (now: number) => {
      if (startTime.current === undefined) startTime.current = now;
      const elapsed = now - startTime.current;
      const t = Math.min(elapsed / durationMs, 1);
      setDisplay(from + (value - from) * easeOut(t));
      if (t < 1) frame.current = requestAnimationFrame(tick);
      else setDisplay(value);
    };

    frame.current = requestAnimationFrame(tick);
    return () => {
      if (frame.current) cancelAnimationFrame(frame.current);
    };
  }, [value, durationMs, from]);

  return display;
}
