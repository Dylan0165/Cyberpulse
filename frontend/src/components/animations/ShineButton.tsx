"use client";

import { usePrefersReducedMotion } from "@/hooks/useAnimation";

interface ShineButtonProps {
  onClick?: () => void;
  className?: string;
  children: React.ReactNode;
  disabled?: boolean;
}

export default function ShineButton({
  onClick,
  className,
  children,
  disabled,
}: ShineButtonProps) {
  const reduced = usePrefersReducedMotion();

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`sxd-shine-btn ${className ?? ""}`}
      data-reduced={reduced ? "1" : "0"}
    >
      <style>{`
        .sxd-shine-btn {
          position: relative;
          overflow: hidden;
          isolation: isolate;
        }
        .sxd-shine-btn::after {
          content: "";
          position: absolute;
          top: 0;
          left: -150%;
          width: 75%;
          height: 100%;
          background: linear-gradient(
            115deg,
            transparent 0%,
            rgba(255, 255, 255, 0.28) 50%,
            transparent 100%
          );
          transform: skewX(-20deg);
          animation: sxd-shine 2.6s ease-in-out infinite;
          pointer-events: none;
        }
        .sxd-shine-btn:hover::after { animation-play-state: paused; }
        .sxd-shine-btn[data-reduced="1"]::after,
        .sxd-shine-btn:disabled::after { animation: none; display: none; }
        @keyframes sxd-shine {
          0% { left: -150%; }
          60%, 100% { left: 150%; }
        }
      `}</style>
      {children}
    </button>
  );
}
