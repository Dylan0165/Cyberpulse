"use client";

import { useEffect, useRef } from "react";
import { usePrefersReducedMotion } from "@/hooks/useAnimation";

interface TiltCardProps {
  className?: string;
  children: React.ReactNode;
}

const MAX_TILT = 8; // degrees

export default function TiltCard({ className, children }: TiltCardProps) {
  const ref = useRef<HTMLDivElement>(null);
  const reduced = usePrefersReducedMotion();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const isTouch =
      typeof window !== "undefined" &&
      window.matchMedia("(pointer: coarse)").matches;

    if (reduced || isTouch) return;

    el.style.transition = "transform 0.15s ease-out";
    el.style.transformStyle = "preserve-3d";
    el.style.willChange = "transform";

    const handleMove = (e: MouseEvent) => {
      const rect = el.getBoundingClientRect();
      const px = (e.clientX - rect.left) / rect.width; // 0..1
      const py = (e.clientY - rect.top) / rect.height; // 0..1
      const rotateY = (px - 0.5) * 2 * MAX_TILT;
      const rotateX = -(py - 0.5) * 2 * MAX_TILT;
      el.style.transform = `perspective(900px) rotateX(${rotateX.toFixed(
        2,
      )}deg) rotateY(${rotateY.toFixed(2)}deg)`;
    };

    const handleLeave = () => {
      el.style.transform = "perspective(900px) rotateX(0deg) rotateY(0deg)";
    };

    el.addEventListener("mousemove", handleMove);
    el.addEventListener("mouseleave", handleLeave);

    return () => {
      el.removeEventListener("mousemove", handleMove);
      el.removeEventListener("mouseleave", handleLeave);
    };
  }, [reduced]);

  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}
