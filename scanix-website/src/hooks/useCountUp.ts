"use client";

import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "./useReducedMotion";

/**
 * Animate a number from 0 to `target` once `active` becomes true.
 * easeOut over `duration` ms, rAF-driven, cleaned up on unmount.
 * Jumps straight to the target when the user prefers reduced motion.
 */
export function useCountUp(
  target: number,
  active: boolean,
  duration = 2000,
): number {
  const reduced = useReducedMotion();
  const [value, setValue] = useState(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (!active) return;
    if (reduced || duration <= 0) {
      setValue(target);
      return;
    }

    let startTs: number | null = null;
    const tick = (ts: number) => {
      if (startTs === null) startTs = ts;
      const p = Math.min(1, (ts - startTs) / duration);
      // easeOutCubic
      const eased = 1 - Math.pow(1 - p, 3);
      setValue(target * eased);
      if (p < 1) rafRef.current = requestAnimationFrame(tick);
      else setValue(target);
    };
    rafRef.current = requestAnimationFrame(tick);

    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, [target, active, duration, reduced]);

  return value;
}
