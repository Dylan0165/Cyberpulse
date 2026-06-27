"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ArrowDown, ArrowUp, X, ChevronDown } from "lucide-react";
import { analyticsApi } from "@/lib/api";
import { RiskBadge } from "@/components/cyber/risk-badge";

type Diff = {
  new_findings: any[];
  resolved_findings: any[];
  unchanged_findings: any[];
  risk_score_delta: number;
  current_risk: number;
  previous_risk: number;
  summary: string;
};

function Row({ f, tone }: { f: any; tone: "new" | "resolved" | "unchanged" }) {
  const border = tone === "new" ? "border-l-4 border-neon-red" : tone === "resolved" ? "border-l-4 border-neon-green" : "border-l-4 border-grid";
  const text = tone === "resolved" ? "text-ink-muted line-through decoration-ink-muted/50" : "text-ink";
  const badge = tone === "new" ? { label: "NIEUW", cls: "bg-neon-red/15 text-neon-red" } : tone === "resolved" ? { label: "OPGELOST", cls: "bg-neon-green/15 text-neon-green" } : null;
  return (
    <div className={`flex items-center gap-2 rounded-r-lg bg-card2 px-3 py-2 ${border}`}>
      <RiskBadge severity={String(f.severity ?? "info").toLowerCase()} />
      <span className={`flex-1 text-[13px] ${text}`}>{f.title ?? f.type ?? "Bevinding"}</span>
      {badge && <span className={`rounded-full px-2 py-0.5 font-mono text-[10px] font-bold ${badge.cls}`}>{badge.label}</span>}
    </div>
  );
}

export function ScanDiffView({
  currentScanId,
  previousScanId,
  previousDate,
  onClose,
}: {
  currentScanId: string;
  previousScanId: string;
  previousDate?: string;
  onClose: () => void;
}) {
  const { data, isLoading } = useQuery<Diff>({
    queryKey: ["scan-diff", currentScanId, previousScanId],
    queryFn: () => analyticsApi.compare(currentScanId, previousScanId).then((r) => r.data),
    retry: false,
  });

  const [showAllResolved, setShowAllResolved] = useState(false);
  const [showUnchanged, setShowUnchanged] = useState(false);

  if (isLoading || !data) {
    return <div className="rounded-lg border border-grid bg-card2 p-6 text-center font-mono text-[12px] text-ink-muted">Vergelijking laden…</div>;
  }

  const improved = data.risk_score_delta < 0;
  const resolved = data.resolved_findings ?? [];
  const visibleResolved = showAllResolved ? resolved : resolved.slice(0, 2);

  return (
    <div className="overflow-hidden rounded-lg border border-grid">
      <div className="flex items-center justify-between gap-3 border-b border-grid bg-card2 px-4 py-3">
        <div>
          <p className="font-display text-[14px] font-bold text-ink">↔ Vergelijking{previousDate ? ` met scan van ${previousDate}` : ""}</p>
          <p className="mt-0.5 font-mono text-[12px] text-ink-muted">
            Risicoscore: {data.previous_risk} → {data.current_risk}{" "}
            <span className={improved ? "text-neon-green" : data.risk_score_delta > 0 ? "text-neon-red" : "text-ink-muted"}>
              ({data.risk_score_delta > 0 ? "+" : ""}{data.risk_score_delta} punten{" "}
              {improved ? <ArrowDown className="inline h-3 w-3" /> : data.risk_score_delta > 0 ? <ArrowUp className="inline h-3 w-3" /> : null}
              {improved ? " verbeterd" : data.risk_score_delta > 0 ? " verslechterd" : ""})
            </span>
          </p>
        </div>
        <button type="button" onClick={onClose} aria-label="Sluit vergelijking" className="text-ink-muted hover:text-ink"><X className="h-4 w-4" /></button>
      </div>

      <div className="space-y-4 p-4">
        {/* New */}
        <div>
          <p className="mb-2 font-mono text-[12px] font-semibold text-neon-red">🔴 NIEUW ({data.new_findings.length})</p>
          <div className="space-y-1.5">
            {data.new_findings.length === 0 ? <p className="font-mono text-[11px] text-ink-muted">Geen nieuwe bevindingen.</p> : data.new_findings.map((f, i) => <Row key={i} f={f} tone="new" />)}
          </div>
        </div>

        {/* Resolved */}
        <div>
          <p className="mb-2 font-mono text-[12px] font-semibold text-neon-green">🟢 OPGELOST ({resolved.length})</p>
          <div className="space-y-1.5">
            {resolved.length === 0 ? <p className="font-mono text-[11px] text-ink-muted">Niets opgelost.</p> : visibleResolved.map((f, i) => <Row key={i} f={f} tone="resolved" />)}
          </div>
          {resolved.length > 2 && (
            <button type="button" onClick={() => setShowAllResolved((v) => !v)} className="mt-2 font-mono text-[12px] text-cyan hover:underline">
              {showAllResolved ? "Toon minder" : `Toon alle ${resolved.length} →`}
            </button>
          )}
        </div>

        {/* Unchanged */}
        <div>
          <button type="button" onClick={() => setShowUnchanged((v) => !v)} className="flex items-center gap-1.5 font-mono text-[12px] font-semibold text-ink-muted hover:text-ink">
            ⚪ ONGEWIJZIGD ({data.unchanged_findings.length})
            <ChevronDown className="h-3.5 w-3.5" style={{ transform: showUnchanged ? "rotate(180deg)" : "none" }} />
          </button>
          {showUnchanged && (
            <div className="mt-2 space-y-1.5">
              {data.unchanged_findings.map((f, i) => <Row key={i} f={f} tone="unchanged" />)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ScanDiffView;
