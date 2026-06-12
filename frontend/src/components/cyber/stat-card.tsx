"use client";

import { motion } from "framer-motion";
import { useCountUp } from "@/hooks/use-count-up";
import { GlowCard } from "./glow-card";
import type { LucideIcon } from "lucide-react";

export function StatCard({
  label,
  value,
  icon: Icon,
  color = "#00D4FF",
  trend,
  index = 0,
  suffix = "",
}: {
  label: string;
  value: number;
  icon: LucideIcon;
  color?: string;
  trend?: string;
  index?: number;
  suffix?: string;
}) {
  const animated = useCountUp(value, 1200);
  const display = Number.isInteger(value) ? Math.round(animated) : animated.toFixed(1);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4, ease: "easeOut" }}
    >
      <GlowCard glowColor={color} className="p-5">
        <div className="flex items-start justify-between">
          <span className="text-[11px] font-medium uppercase tracking-wider text-ink-muted">
            {label}
          </span>
          <div
            className="flex h-8 w-8 items-center justify-center rounded-md"
            style={{ background: `${color}14`, border: `1px solid ${color}33` }}
          >
            <Icon className="h-4 w-4" style={{ color }} />
          </div>
        </div>
        <div
          className="mt-3 font-display text-[34px] font-bold leading-none tabular-nums"
          style={{ color }}
        >
          {display}
          {suffix}
        </div>
        {trend && (
          <div className="mt-2 text-[11px] font-medium text-ink-muted">{trend}</div>
        )}
      </GlowCard>
    </motion.div>
  );
}
