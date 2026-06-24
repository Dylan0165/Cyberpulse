"use client";

import { useRouter } from "next/navigation";
import { Network } from "lucide-react";
import { SmartTargetInput } from "@/components/dashboard/SmartTargetInput";

export default function MultiScanStartPage() {
  const router = useRouter();

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6">
      <div>
        <h1 className="flex items-center gap-2 font-display text-2xl font-bold uppercase tracking-[0.06em] text-ink">
          <Network className="h-6 w-6 text-cyan" /> Multi-scan
        </h1>
        <p className="mt-1 font-mono text-[12px] text-ink-muted">
          Scan een heel subnet, een IP-range of alle subdomeinen van een domein in één keer.
        </p>
      </div>

      <div className="rounded-xl border border-grid bg-card p-6">
        <SmartTargetInput onStarted={(jobId) => router.push(`/multi-scan/${jobId}`)} />
      </div>

      <p className="font-mono text-[11px] text-ink-muted">
        1 credit = 1 systeem. Subnet-prijzen: /29 = 3, /28 = 5, /24 = 10 credits. De preview toont
        het exacte aantal vóór er credits worden afgeschreven.
      </p>
    </div>
  );
}
