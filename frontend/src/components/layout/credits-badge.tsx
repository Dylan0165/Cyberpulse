"use client";

import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Zap, Infinity as InfinityIcon } from "lucide-react";
import { billingApi } from "@/lib/api";

/**
 * Credits balance pill in the top header. Polls the balance and colour-codes it:
 *   3+  → cyan, 1-2 → orange, 0 → red + pulse, business/enterprise → "∞" gold.
 * Click navigates to /billing. Hidden entirely if the balance can't be loaded.
 */
export function CreditsBadge() {
  const router = useRouter();

  const { data } = useQuery({
    queryKey: ["credits-balance"],
    queryFn: () => billingApi.creditsBalance().then((r) => r.data),
    staleTime: 30_000,
    refetchOnWindowFocus: true,
    retry: false,
  });

  if (!data) return null;

  const unlimited = data.is_unlimited;
  const credits = data.credits_remaining;

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
      title="Bekijk uw credits en koop bij"
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
