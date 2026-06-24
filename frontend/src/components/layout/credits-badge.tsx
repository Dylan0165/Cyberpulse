"use client";

import { useRouter } from "next/navigation";
import { Zap, Infinity as InfinityIcon } from "lucide-react";
import { useCredits } from "@/hooks/useCredits";

/**
 * Credits balance pill in the top header. Polls the balance (30s) and
 * colour-codes it: 3+ → cyan, 1-2 → orange, 0 → red + pulse,
 * business/enterprise → "∞" gold. Click navigates to /billing.
 */
export function CreditsBadge() {
  const router = useRouter();
  const { balance, isLoading } = useCredits();

  // Skeleton while the first fetch is in flight.
  if (isLoading) {
    return <div className="h-7 w-20 animate-pulse rounded-full border border-grid bg-card2" aria-hidden />;
  }
  if (!balance) return null;

  const unlimited = balance.is_unlimited;
  const credits = balance.credits_remaining;
  const tooltip = unlimited
    ? "Onbeperkt scan credits"
    : `${credits} scan ${credits === 1 ? "credit" : "credits"} beschikbaar. Klik om bij te kopen.`;

  let tone: { border: string; bg: string; text: string; pulse?: boolean };
  if (unlimited) {
    tone = { border: "border-violet-400/40", bg: "bg-violet-400/10", text: "text-violet-300" };
  } else if (credits >= 3) {
    tone = { border: "border-cyan/40", bg: "bg-cyan/10", text: "text-cyan" };
  } else if (credits >= 1) {
    tone = { border: "border-neon-orange/50", bg: "bg-neon-orange/10", text: "text-neon-orange" };
  } else {
    tone = { border: "border-neon-red/60", bg: "bg-neon-red/15", text: "text-neon-red", pulse: true };
  }

  return (
    <button
      type="button"
      onClick={() => router.push("/billing")}
      title={tooltip}
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 font-mono text-[12px] font-semibold transition-all hover:brightness-125 ${tone.border} ${tone.bg} ${tone.text} ${
        tone.pulse ? "animate-pulse" : ""
      }`}
    >
      {unlimited ? (
        <>
          <InfinityIcon className="h-3.5 w-3.5" strokeWidth={2.5} />
          Onbeperkt
        </>
      ) : (
        <>
          <Zap className="h-3.5 w-3.5" strokeWidth={2.5} fill="currentColor" />
          {credits} {credits === 1 ? "credit" : "credits"}
        </>
      )}
    </button>
  );
}
