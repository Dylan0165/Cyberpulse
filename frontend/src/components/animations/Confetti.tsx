"use client";

import { useEffect, useMemo, useState } from "react";
import { usePrefersReducedMotion } from "@/hooks/useAnimation";

const COLORS = ["#06b6d4", "#FF2D55", "#FF8C00", "#22c55e", "#ffffff"];
const COUNT = 36;

interface Piece {
  left: number;
  delay: number;
  duration: number;
  drift: number;
  rotate: number;
  color: string;
  size: number;
}

export default function Confetti({ trigger }: { trigger: boolean }) {
  const reduced = usePrefersReducedMotion();
  const [run, setRun] = useState(false);

  const pieces = useMemo<Piece[]>(() => {
    return Array.from({ length: COUNT }, () => ({
      left: Math.random() * 100,
      delay: Math.random() * 0.4,
      duration: 1.8 + Math.random() * 0.7,
      drift: (Math.random() - 0.5) * 160,
      rotate: Math.random() * 720,
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
      size: 6 + Math.random() * 6,
    }));
  }, []);

  useEffect(() => {
    if (!trigger || reduced) return;
    setRun(true);
    const t = window.setTimeout(() => setRun(false), 2500);
    return () => window.clearTimeout(t);
  }, [trigger, reduced]);

  if (reduced || !run) return null;

  return (
    <div className="sxd-confetti-root" aria-hidden="true">
      <style>{`
        .sxd-confetti-root {
          position: fixed;
          inset: 0;
          z-index: 9997;
          pointer-events: none;
          overflow: hidden;
        }
        .sxd-confetti-piece {
          position: absolute;
          top: -16px;
          will-change: transform, opacity;
          animation-name: sxd-confetti-fall;
          animation-timing-function: ease-in;
          animation-fill-mode: forwards;
        }
        @keyframes sxd-confetti-fall {
          0% { transform: translate3d(0, 0, 0) rotate(0deg); opacity: 1; }
          100% {
            transform: translate3d(var(--sxd-drift), 105vh, 0) rotate(var(--sxd-rot));
            opacity: 0;
          }
        }
      `}</style>
      {pieces.map((p, i) => (
        <span
          key={i}
          className="sxd-confetti-piece"
          style={{
            left: `${p.left}%`,
            width: `${p.size}px`,
            height: `${p.size}px`,
            background: p.color,
            animationDelay: `${p.delay}s`,
            animationDuration: `${p.duration}s`,
            ["--sxd-drift" as string]: `${p.drift}px`,
            ["--sxd-rot" as string]: `${p.rotate}deg`,
          }}
        />
      ))}
    </div>
  );
}
