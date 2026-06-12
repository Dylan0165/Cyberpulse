"use client";

interface RiskGaugeProps {
  score: number;  // 0–100
  size?: number;
}

const getColor = (score: number): string => {
  if (score >= 80) return "#22c55e";   // green — safe
  if (score >= 60) return "#eab308";   // yellow — medium
  if (score >= 40) return "#f97316";   // orange — high
  return "#ef4444";                     // red — critical
};

const getLabel = (score: number): string => {
  if (score >= 80) return "SECURE";
  if (score >= 60) return "AT RISK";
  if (score >= 40) return "HIGH RISK";
  return "CRITICAL";
};

/**
 * SVG semicircle gauge displaying a 0-100 security score.
 * Green (≥80) → Yellow (≥60) → Orange (≥40) → Red (<40).
 */
export function RiskGauge({ score, size = 140 }: RiskGaugeProps) {
  const clamped = Math.max(0, Math.min(100, score ?? 0));
  const color = getColor(clamped);
  const label = getLabel(clamped);

  // Gauge arc spans 180° (π radians) from 180° to 0° (left to right through top)
  const cx = size / 2;
  const cy = size * 0.65;
  const r = size * 0.38;
  const strokeWidth = size * 0.1;

  // Background track arc (full semicircle, 180°)
  const bgStart = polarToCart(cx, cy, r, 180);
  const bgEnd = polarToCart(cx, cy, r, 0);
  const bgArc = `M ${bgStart.x} ${bgStart.y} A ${r} ${r} 0 0 1 ${bgEnd.x} ${bgEnd.y}`;

  // Value arc (portion filled based on score)
  const endAngle = 180 - (clamped / 100) * 180;
  const largeArc = clamped > 50 ? 1 : 0;
  const valEnd = polarToCart(cx, cy, r, endAngle);
  const valArc = `M ${bgStart.x} ${bgStart.y} A ${r} ${r} 0 ${largeArc} 1 ${valEnd.x} ${valEnd.y}`;

  // Needle
  const needleAngle = 180 - (clamped / 100) * 180; // deg
  const needleRad = (needleAngle * Math.PI) / 180;
  const needleLen = r - strokeWidth / 2;
  const nx = cx + needleLen * Math.cos(Math.PI - needleRad);
  const ny = cy - needleLen * Math.sin(Math.PI - needleRad);

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size * 0.7} viewBox={`0 0 ${size} ${size * 0.7}`}>
        {/* Background track */}
        <path
          d={bgArc}
          fill="none"
          stroke="currentColor"
          strokeOpacity={0.15}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Value arc */}
        <path
          d={valArc}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          style={{ transition: "all 0.6s ease" }}
        />
        {/* Needle */}
        <line
          x1={cx}
          y1={cy}
          x2={nx}
          y2={ny}
          stroke={color}
          strokeWidth={size * 0.025}
          strokeLinecap="round"
          style={{ transition: "all 0.6s ease" }}
        />
        <circle cx={cx} cy={cy} r={size * 0.04} fill={color} />

        {/* Score text */}
        <text
          x={cx}
          y={cy - r * 0.2}
          textAnchor="middle"
          fontSize={size * 0.22}
          fontWeight="700"
          fill={color}
        >
          {Math.round(clamped)}
        </text>

        {/* Min / Max labels */}
        <text x={cx - r - strokeWidth / 2} y={cy + size * 0.08} textAnchor="middle" fontSize={size * 0.075} fill="currentColor" opacity={0.4}>0</text>
        <text x={cx + r + strokeWidth / 2} y={cy + size * 0.08} textAnchor="middle" fontSize={size * 0.075} fill="currentColor" opacity={0.4}>100</text>
      </svg>
      <span
        className="text-xs font-bold tracking-widest mt-1"
        style={{ color }}
      >
        {label}
      </span>
    </div>
  );
}

function polarToCart(cx: number, cy: number, r: number, angleDeg: number): { x: number; y: number } {
  const rad = ((angleDeg - 180) * Math.PI) / 180;
  return {
    x: cx + r * Math.cos(rad),
    y: cy + r * Math.sin(rad),
  };
}
