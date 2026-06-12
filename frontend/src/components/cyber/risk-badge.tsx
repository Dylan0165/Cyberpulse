"use client";

import { cn } from "@/lib/utils";

type Severity = "critical" | "high" | "medium" | "low" | "info";

const STYLES: Record<Severity, { label: string; color: string; bg: string; glow: string }> = {
  critical: { label: "CRITICAL", color: "#FF2D55", bg: "rgba(255,45,85,0.12)",  glow: "0 0 14px rgba(255,45,85,0.4)" },
  high:     { label: "HIGH",     color: "#FF8C00", bg: "rgba(255,140,0,0.12)",  glow: "0 0 14px rgba(255,140,0,0.35)" },
  medium:   { label: "MEDIUM",   color: "#FFD60A", bg: "rgba(255,214,10,0.12)", glow: "0 0 14px rgba(255,214,10,0.3)" },
  low:      { label: "LOW",      color: "#0A84FF", bg: "rgba(10,132,255,0.12)", glow: "0 0 14px rgba(10,132,255,0.3)" },
  info:     { label: "INFO",     color: "#4A6880", bg: "rgba(74,104,128,0.12)", glow: "none" },
};

export function RiskBadge({
  severity,
  className,
  withGlow = true,
  children,
}: {
  severity: string;
  className?: string;
  withGlow?: boolean;
  children?: React.ReactNode;
}) {
  const key = (severity || "info").toLowerCase() as Severity;
  const s = STYLES[key] ?? STYLES.info;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider font-mono",
        "transition-shadow duration-200",
        className
      )}
      style={{
        color: s.color,
        background: s.bg,
        border: `1px solid ${s.color}55`,
        boxShadow: withGlow ? s.glow : "none",
      }}
    >
      {children ?? s.label}
    </span>
  );
}

export function severityColor(severity: string): string {
  const s = STYLES[(severity || "info").toLowerCase() as Severity];
  return s?.color ?? STYLES.info.color;
}
