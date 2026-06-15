"use client";

import { cn } from "@/lib/utils";
import { SEVERITY } from "@/lib/labels";

type Severity = "critical" | "high" | "medium" | "low" | "info";

const STYLES: Record<Severity, { color: string; bg: string; glow: string }> = {
  critical: { color: "#FF2D55", bg: "rgba(255,45,85,0.12)",  glow: "0 0 14px rgba(255,45,85,0.4)" },
  high:     { color: "#FF8C00", bg: "rgba(255,140,0,0.12)",  glow: "0 0 14px rgba(255,140,0,0.35)" },
  medium:   { color: "#FFD60A", bg: "rgba(255,214,10,0.12)", glow: "0 0 14px rgba(255,214,10,0.3)" },
  low:      { color: "#0A84FF", bg: "rgba(10,132,255,0.12)", glow: "0 0 14px rgba(10,132,255,0.3)" },
  info:     { color: "#4A6880", bg: "rgba(74,104,128,0.12)", glow: "none" },
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
  const meta = SEVERITY[key] ?? SEVERITY.info;
  return (
    <span
      title={meta.tooltip}
      className={cn(
        "inline-flex items-center rounded px-2 py-0.5 text-[11px] font-semibold tracking-wide font-mono",
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
      {children ?? meta.label}
    </span>
  );
}

export function severityColor(severity: string): string {
  const s = STYLES[(severity || "info").toLowerCase() as Severity];
  return s?.color ?? STYLES.info.color;
}
