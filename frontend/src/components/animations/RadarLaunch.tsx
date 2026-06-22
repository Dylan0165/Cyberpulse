"use client";

import { useEffect } from "react";
import { usePrefersReducedMotion } from "@/hooks/useAnimation";

export default function RadarLaunch({
  active,
  onDone,
}: {
  active: boolean;
  onDone: () => void;
}) {
  const reduced = usePrefersReducedMotion();

  useEffect(() => {
    if (!active) return;
    const delay = reduced ? 30 : 1500;
    const t = window.setTimeout(() => onDone(), delay);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, reduced]);

  if (!active) return null;

  return (
    <div className="sxd-radar-overlay" aria-hidden="true">
      <style>{`
        .sxd-radar-overlay {
          position: fixed;
          inset: 0;
          z-index: 9998;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #000;
        }
        .sxd-radar-stage {
          position: relative;
          width: 280px;
          height: 280px;
        }
        .sxd-radar-ring {
          position: absolute;
          inset: 0;
          margin: auto;
          width: 80px;
          height: 80px;
          border: 2px solid #06b6d4;
          border-radius: 50%;
          opacity: 0;
          animation: sxd-radar-expand 1.5s ease-out infinite;
        }
        .sxd-radar-ring.sxd-radar-ring-2 { animation-delay: 0.5s; }
        .sxd-radar-ring.sxd-radar-ring-3 { animation-delay: 1s; }
        .sxd-radar-sweep {
          position: absolute;
          inset: 0;
          border-radius: 50%;
          background: conic-gradient(
            from 0deg,
            rgba(6, 182, 212, 0) 0deg,
            rgba(6, 182, 212, 0) 300deg,
            rgba(6, 182, 212, 0.55) 360deg
          );
          mask: radial-gradient(circle, transparent 0, #000 0);
          animation: sxd-radar-spin 1.5s linear infinite;
        }
        .sxd-radar-core {
          position: absolute;
          inset: 0;
          margin: auto;
          width: 10px;
          height: 10px;
          border-radius: 50%;
          background: #06b6d4;
          box-shadow: 0 0 18px 4px rgba(6, 182, 212, 0.7);
        }
        @keyframes sxd-radar-expand {
          0% { opacity: 0.8; transform: scale(0.3); }
          100% { opacity: 0; transform: scale(2.6); }
        }
        @keyframes sxd-radar-spin {
          to { transform: rotate(360deg); }
        }
        @media (prefers-reduced-motion: reduce) {
          .sxd-radar-ring,
          .sxd-radar-sweep { animation: none; opacity: 0.4; }
        }
      `}</style>
      <div className="sxd-radar-stage">
        <div className="sxd-radar-sweep" />
        <div className="sxd-radar-ring sxd-radar-ring-1" />
        <div className="sxd-radar-ring sxd-radar-ring-2" />
        <div className="sxd-radar-ring sxd-radar-ring-3" />
        <div className="sxd-radar-core" />
      </div>
    </div>
  );
}
