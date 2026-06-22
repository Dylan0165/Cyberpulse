"use client";

import { usePrefersReducedMotion } from "@/hooks/useAnimation";

export default function AnimatedCheckmark({ size = 64 }: { size?: number }) {
  const reduced = usePrefersReducedMotion();

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 52 52"
      fill="none"
      aria-hidden="true"
      className="sxd-check"
      data-reduced={reduced ? "1" : "0"}
    >
      <style>{`
        .sxd-check .sxd-check-circle {
          stroke-dasharray: 166;
          stroke-dashoffset: 166;
          animation: sxd-check-draw 0.6s ease forwards;
        }
        .sxd-check .sxd-check-tick {
          stroke-dasharray: 48;
          stroke-dashoffset: 48;
          animation: sxd-check-draw 0.35s ease 0.5s forwards;
        }
        .sxd-check[data-reduced="1"] .sxd-check-circle,
        .sxd-check[data-reduced="1"] .sxd-check-tick {
          stroke-dashoffset: 0;
          animation: none;
        }
        @keyframes sxd-check-draw {
          to { stroke-dashoffset: 0; }
        }
      `}</style>
      <circle
        className="sxd-check-circle"
        cx="26"
        cy="26"
        r="25"
        stroke="#22c55e"
        strokeWidth="2"
      />
      <path
        className="sxd-check-tick"
        d="M14 27l8 8 16-16"
        stroke="#22c55e"
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
