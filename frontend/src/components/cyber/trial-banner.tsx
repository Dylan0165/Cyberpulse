"use client";

import { useEffect, useState } from "react";
import { ArrowRight, Sparkles, X } from "lucide-react";
import { useAuth } from "@/contexts/auth-context";

const DISMISS_KEY = "scanix_trial_banner_dismissed";

export function TrialBanner() {
  const { planInfo } = useAuth();
  const [dismissed, setDismissed] = useState(true);

  // Read dismissal state from localStorage on mount (client-only, SSR-safe).
  useEffect(() => {
    try {
      setDismissed(localStorage.getItem(DISMISS_KEY) === "1");
    } catch {
      setDismissed(false);
    }
  }, []);

  const isTrial = planInfo?.plan === "trial";
  if (!isTrial || dismissed) return null;

  const dismiss = () => {
    try {
      localStorage.setItem(DISMISS_KEY, "1");
    } catch {
      // ignore — storage may be unavailable (private mode, etc.)
    }
    setDismissed(true);
  };

  return (
    <div
      className="mb-5 flex flex-col gap-3 rounded-lg border px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
      style={{
        borderColor: "rgba(0,180,216,0.4)",
        background: "rgba(0,180,216,0.06)",
      }}
    >
      <div className="flex items-start gap-3">
        <Sparkles className="mt-0.5 h-4 w-4 flex-shrink-0 text-cyan" />
        <p className="font-mono text-[12px] leading-snug text-ink">
          U gebruikt een gratis proefaccount. Upgrade naar Starter voor meer scans.
        </p>
      </div>
      <div className="flex items-center gap-2 self-end sm:self-auto">
        <a
          href="https://scanix.nl/prijzen"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 whitespace-nowrap rounded-md bg-cyan px-3 py-1.5 font-display text-[11px] font-bold uppercase tracking-[0.08em] text-app transition-transform duration-150 hover:scale-[1.02] active:scale-[0.98]"
        >
          Bekijk pakketten <ArrowRight className="h-3.5 w-3.5" />
        </a>
        <button
          type="button"
          onClick={dismiss}
          aria-label="Sluiten"
          className="flex h-7 w-7 items-center justify-center rounded-md text-ink-muted transition-colors hover:text-ink"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

export default TrialBanner;
