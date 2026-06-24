"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { Zap, ArrowRight, X } from "lucide-react";

/**
 * Blocking modal shown when the user tries to start a scan with no credits.
 * Primary action sends them to /billing; secondary just closes (no redirect).
 */
export function NoCreditsModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const router = useRouter();

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
          >
            <button
              type="button"
              onClick={onClose}
              aria-label="Sluiten"
              className="absolute right-4 top-4 text-ink-muted transition-colors hover:text-ink"
            >
              <X className="h-4 w-4" />
            </button>

            <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-lg border border-neon-red/40 bg-neon-red/10">
              <Zap className="h-5 w-5 text-neon-red" fill="currentColor" />
            </div>

            <h2 className="font-display text-lg font-bold tracking-tight text-ink">
              Geen scan credits
            </h2>
            <p className="mt-2 font-mono text-[12px] leading-relaxed text-ink-muted">
              U heeft geen credits meer. Koop een pakket om verder te gaan. 1 credit = 1 scan,
              en credits verlopen nooit.
            </p>

            <div className="mt-6 flex flex-col gap-2 sm:flex-row">
              <button
                type="button"
                onClick={() => router.push("/billing")}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-cyan px-4 py-2.5 font-display text-[12px] font-bold uppercase tracking-[0.1em] text-app shadow-glow-cyan transition-transform duration-150 hover:scale-[1.02] active:scale-[0.98]"
              >
                Credits kopen <ArrowRight className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={onClose}
                className="flex flex-1 items-center justify-center rounded-lg border border-grid bg-card2 px-4 py-2.5 font-mono text-[12px] uppercase tracking-[0.1em] text-ink-muted transition-colors duration-150 hover:border-cyan/50 hover:text-cyan"
              >
                Annuleren
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default NoCreditsModal;
