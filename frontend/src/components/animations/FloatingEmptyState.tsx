"use client";

import type { LucideIcon } from "lucide-react";
import { usePrefersReducedMotion } from "@/hooks/useAnimation";

interface FloatingEmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  ctaLabel?: string;
  onCta?: () => void;
}

export default function FloatingEmptyState({
  icon: Icon,
  title,
  description,
  ctaLabel,
  onCta,
}: FloatingEmptyStateProps) {
  const reduced = usePrefersReducedMotion();

  return (
    <div
      className="sxd-empty"
      data-reduced={reduced ? "1" : "0"}
    >
      <style>{`
        .sxd-empty {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          text-align: center;
          padding: 3rem 1.5rem;
          gap: 1rem;
        }
        .sxd-empty-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 96px;
          height: 96px;
          border-radius: 9999px;
          border: 1px solid var(--sxd-grid, rgba(148,163,184,0.2));
          background: rgba(6, 182, 212, 0.06);
          color: #06b6d4;
          animation: sxd-empty-float 4s ease-in-out infinite,
            sxd-empty-pulse 3s ease-in-out infinite;
        }
        .sxd-empty[data-reduced="1"] .sxd-empty-icon { animation: none; }
        .sxd-empty-cta {
          margin-top: 0.5rem;
          padding: 0.55rem 1.25rem;
          border-radius: 0.5rem;
          font-size: 0.875rem;
          font-weight: 600;
          color: #04181c;
          background: #06b6d4;
          border: none;
          cursor: pointer;
          animation: sxd-empty-attention 1.6s ease-in-out 3s infinite;
        }
        .sxd-empty[data-reduced="1"] .sxd-empty-cta { animation: none; }
        @keyframes sxd-empty-float {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-10px); }
        }
        @keyframes sxd-empty-pulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(6,182,212,0.25); }
          50% { box-shadow: 0 0 0 14px rgba(6,182,212,0); }
        }
        @keyframes sxd-empty-attention {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.06); }
        }
      `}</style>
      <div className="sxd-empty-icon">
        <Icon size={40} strokeWidth={1.5} aria-hidden="true" />
      </div>
      <h3 className="text-lg font-semibold text-ink">{title}</h3>
      <p className="max-w-sm text-sm text-ink-muted">{description}</p>
      {ctaLabel && (
        <button type="button" className="sxd-empty-cta" onClick={onCta}>
          {ctaLabel}
        </button>
      )}
    </div>
  );
}
