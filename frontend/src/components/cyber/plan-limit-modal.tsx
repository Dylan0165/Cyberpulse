"use client";

import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, ArrowRight, X } from "lucide-react";

export type PlanLimitKind = "scan" | "target";

const COPY: Record<PlanLimitKind, { title: string; body: string; extra?: string }> = {
  scan: {
    title: "Scanlimiet bereikt",
    body: "U heeft het maximale aantal scans voor uw pakket gebruikt.",
    extra: "Upgrade naar Business voor onbeperkte scans.",
  },
  target: {
    title: "Systeemlimiet bereikt",
    body: "Uw pakket staat maximaal het ingestelde aantal systemen toe.",
  },
};

export function PlanLimitModal({
  open,
  kind,
  onClose,
}: {
  open: boolean;
  kind: PlanLimitKind;
  onClose: () => void;
}) {
  const copy = COPY[kind] ?? COPY.scan;

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            transition={{ type: "spring", stiffness: 300, damping: 26 }}
            onClick={(e) => e.stopPropagation()}
            className="relative w-full max-w-md rounded-xl border border-grid bg-card2 p-6 shadow-glow-cyan"
            style={{ background: "var(--bg-card)" }}
          >
            <button
              type="button"
              onClick={onClose}
              aria-label="Sluiten"
              className="absolute right-4 top-4 text-ink-muted transition-colors hover:text-ink"
            >
              <X className="h-4 w-4" />
            </button>

            <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-lg border border-grid bg-app">
              <AlertTriangle className="h-5 w-5" style={{ color: "#FF8C00" }} />
            </div>

            <h2 className="font-display text-lg font-bold tracking-tight text-ink">
              {copy.title}
            </h2>
            <p className="mt-2 font-mono text-[12px] leading-relaxed text-ink-muted">
              {copy.body}
            </p>
            {copy.extra && (
              <p className="mt-1 font-mono text-[12px] leading-relaxed text-cyan">
                {copy.extra}
              </p>
            )}

            <div className="mt-6 flex flex-col gap-2 sm:flex-row">
              <a
                href="https://scanix.nl/prijzen"
                target="_blank"
                rel="noopener noreferrer"
                className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-cyan px-4 py-2.5 font-display text-[12px] font-bold uppercase tracking-[0.1em] text-app shadow-glow-cyan transition-transform duration-150 hover:scale-[1.02] active:scale-[0.98]"
              >
                Upgrade <ArrowRight className="h-4 w-4" />
              </a>
              <button
                type="button"
                onClick={onClose}
                className="flex flex-1 items-center justify-center rounded-lg border border-grid bg-card2 px-4 py-2.5 font-mono text-[12px] uppercase tracking-[0.1em] text-ink-muted transition-colors duration-150 hover:border-cyan/50 hover:text-cyan"
              >
                Sluiten
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default PlanLimitModal;
