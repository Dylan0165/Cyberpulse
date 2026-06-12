"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export function GlowCard({
  children,
  className,
  glowColor = "#00D4FF",
  accentBorder,
  hoverLift = true,
  onClick,
}: {
  children: React.ReactNode;
  className?: string;
  glowColor?: string;
  accentBorder?: string;
  hoverLift?: boolean;
  onClick?: () => void;
}) {
  return (
    <motion.div
      onClick={onClick}
      whileHover={hoverLift ? { y: -2 } : undefined}
      transition={{ type: "spring", stiffness: 300, damping: 24 }}
      className={cn(
        "group relative rounded-lg border bg-card2 transition-colors duration-200",
        onClick && "cursor-pointer",
        className
      )}
      style={{
        borderColor: accentBorder ?? "var(--border)",
        background: "var(--bg-card)",
      }}
    >
      {accentBorder && (
        <span
          className="absolute left-0 top-0 h-full w-[2px] rounded-l-lg"
          style={{ background: accentBorder, boxShadow: `0 0 12px ${accentBorder}` }}
        />
      )}
      {/* Hover glow ring */}
      <span
        className="pointer-events-none absolute inset-0 rounded-lg opacity-0 transition-opacity duration-200 group-hover:opacity-100"
        style={{ boxShadow: `0 0 0 1px ${glowColor}55, 0 0 24px ${glowColor}22` }}
      />
      {children}
    </motion.div>
  );
}
