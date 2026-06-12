"use client";

import { useCountUp } from "@/hooks/use-count-up";

function gaugeColor(score: number): string {
  if (score >= 60) return "#FF2D55";
  if (score >= 30) return "#FFD60A";
  return "#00FF88";
}

/**
 * SVG arc gauge, 0–100. Animates from 0 on mount. Outer ring pulses if score > 60.
 */
export function RiskGauge({ score, size = 180 }: { score: number; size?: number }) {
  const animated = useCountUp(score, 1500);
  const color = gaugeColor(score);

  const stroke = 12;
  const r = (size - stroke) / 2;
  const cx = size / 2;
  const cy = size / 2;
  // 270° arc (from -225° to 45°)
  const startAngle = 135;
  const sweep = 270;
  const circumference = 2 * Math.PI * r;
  const arcLen = (sweep / 360) * circumference;
  const progress = Math.max(0, Math.min(animated, 100)) / 100;

  return (
    <div
      className="relative flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      <svg
        width={size}
        height={size}
        className={score > 60 ? "animate-pulse-ring rounded-full" : ""}
        style={{ transform: `rotate(${startAngle}deg)` }}
      >
        {/* Track */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="#0A2035"
          strokeWidth={stroke}
          strokeDasharray={`${arcLen} ${circumference}`}
          strokeLinecap="round"
        />
        {/* Progress */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={`${arcLen * progress} ${circumference}`}
          strokeLinecap="round"
          style={{ filter: `drop-shadow(0 0 8px ${color}aa)`, transition: "stroke 0.4s ease" }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span
          className="font-display text-[44px] font-bold leading-none tabular-nums"
          style={{ color, textShadow: `0 0 18px ${color}66` }}
        >
          {Math.round(animated)}
        </span>
        <span className="mt-1 font-mono text-[10px] uppercase tracking-widest text-ink-muted">
          risk score
        </span>
      </div>
    </div>
  );
}
