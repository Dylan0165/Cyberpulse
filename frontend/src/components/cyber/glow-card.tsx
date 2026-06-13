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
      whileHover={hoverLift ? { y: -1 } : undefined}
      transition={{ type: "tween", duration: 0.15, ease: "easeOut" }}
      className={cn(
        "group relative rounded-lg border bg-card2 transition-colors duration-150",
        // idle: subtle border; hover: slightly more visible border, no glow
        "border-grid-subtle hover:border-grid",
        onClick && "cursor-pointer",
        className
      )}
      style={{ background: "var(--bg-card)" }}
    >
      {accentBorder && (
        <span
          className="absolute left-0 top-0 h-full w-[2px] rounded-l-lg"
          style={{ background: accentBorder }}
        />
      )}
      {children}
    </motion.div>
  );
}
