"use client";

import { useQuery } from "@tanstack/react-query";
import { dashboardApi, reportsApi, targetsApi } from "@/lib/api";
import Link from "next/link";
import { FileText, Download, ArrowRight, Plus } from "lucide-react";

export default function ReportsPage() {
  const { data: scansData, isLoading } = useQuery({
    queryKey: ["scans-completed"],
    queryFn: () => dashboardApi.listScans(1, 100),
  });

  const { data: targetsData } = useQuery({
    queryKey: ["targets"],
    queryFn: () => targetsApi.list().then((r) => r.data),
  });

  // Build a quick lookup map: target_id → display value (IP or hostname)
  const targetMap: Record<string, string> = {};
  if (Array.isArray(targetsData)) {
    for (const t of targetsData as any[]) {
      targetMap[t.id] = t.value ?? t.hostname ?? t.name ?? t.id;
    }
  }

  const completedScans =
    (scansData?.items ?? []).filter((s: any) => s.status === "completed");

  const handleDownload = async (
    e: React.MouseEvent,
    scanId: string,
    format: "pdf" | "json",
  ) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const res = format === "pdf"
        ? await reportsApi.downloadPdf(scanId)
        : await reportsApi.downloadJson(scanId);
      const blob = new Blob([res.data]);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `cyberpulse-report-${scanId}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Download mislukt. Probeer opnieuw.");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[28px] font-bold" style={{ letterSpacing: "-0.03em" }}>
            Rapporten
          </h1>
          <p className="text-[15px] text-muted-foreground mt-0.5">
            Download en bekijk voltooide pentest rapporten
          </p>
        </div>
        <Link
          href="/scans/new"
          className="inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-[14px] font-semibold transition-opacity hover:opacity-90"
          style={{ background: "#0071e3", color: "#fff" }}
        >
          <Plus className="h-4 w-4" />
          Nieuwe scan
        </Link>
      </div>

      {isLoading ? (
        <SkeletonList />
      ) : completedScans.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="space-y-3">
          {completedScans.map((scan: any) => {
            // ScanResponse uses critical_count / high_count / medium_count / low_count
            const crit = scan.critical_count ?? scan.findings_critical ?? 0;
            const high = scan.high_count    ?? scan.findings_high     ?? 0;
            const med  = scan.medium_count  ?? scan.findings_medium   ?? 0;
            const low  = scan.low_count     ?? scan.findings_low      ?? 0;
            const total = crit + high + med + low;
            const riskScore = scan.security_score != null
              ? Math.round(100 - scan.security_score)
              : null;
            const targetDisplay = targetMap[scan.target_id] ?? scan.target_id ?? "—";

            return (
              <div
                key={scan.id}
                className="rounded-2xl border border-border bg-card shadow-apple hover:shadow-apple-md transition-shadow"
              >
                <div className="flex items-center justify-between p-5">
                  {/* Left: icon + info */}
                  <div className="flex items-center gap-4 min-w-0">
                    <div
                      className="h-12 w-12 rounded-xl flex items-center justify-center flex-shrink-0"
                      style={{ background: "rgba(0,113,227,0.08)" }}
                    >
                      <FileText className="h-6 w-6" style={{ color: "#0071e3" }} />
                    </div>
                    <div className="min-w-0">
                      <p className="text-[15px] font-semibold truncate font-mono">
                        {targetDisplay}
                      </p>
                      <p className="text-[13px] text-muted-foreground mt-0.5">
                        {scan.scan_type?.replace(/_/g, " ") ?? "pentest"}
                        {" · "}
                        {new Date(scan.completed_at ?? scan.created_at).toLocaleDateString("nl-NL", {
                          day: "2-digit",
                          month: "short",
                          year: "numeric",
                        })}
                      </p>
                      {/* Finding breakdown */}
                      {total > 0 && (
                        <div className="flex items-center gap-2 mt-1.5">
                          {crit > 0 && <span className="text-[11px] font-semibold rounded-full px-2 py-0.5" style={{ background: "rgba(255,59,48,0.10)", color: "#ff3b30" }}>{crit} kritiek</span>}
                          {high > 0 && <span className="text-[11px] font-semibold rounded-full px-2 py-0.5" style={{ background: "rgba(255,149,0,0.10)", color: "#ff9500" }}>{high} hoog</span>}
                          {med  > 0 && <span className="text-[11px] font-semibold rounded-full px-2 py-0.5" style={{ background: "rgba(255,204,0,0.12)", color: "#c69b00" }}>{med} gemiddeld</span>}
                          {low  > 0 && <span className="text-[11px] font-semibold rounded-full px-2 py-0.5" style={{ background: "rgba(142,142,147,0.10)", color: "#8e8e93" }}>{low} laag</span>}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Right: risk + findings + actions */}
                  <div className="flex items-center gap-4 flex-shrink-0">
                    {/* Risk score */}
                    {riskScore !== null && (
                      <div className="text-right">
                        <p className="text-[11px] text-muted-foreground uppercase tracking-wider">
                          Risico
                        </p>
                        <p
                          className="text-[20px] font-bold leading-tight"
                          style={{
                            color: riskScore >= 70 ? "#ff3b30" : riskScore >= 40 ? "#ff9500" : "#34c759",
                          }}
                        >
                          {riskScore}
                        </p>
                      </div>
                    )}

                    {/* Findings pills */}
                    {total > 0 && (
                      <div className="flex items-center gap-1.5">
                        {crit > 0 && <Pill value={crit} label="K" color="#ff3b30" bg="rgba(255,59,48,0.10)" />}
                        {high > 0 && <Pill value={high} label="H" color="#ff9500" bg="rgba(255,149,0,0.10)" />}
                        {med  > 0 && <Pill value={med}  label="M" color="#c69b00" bg="rgba(255,204,0,0.12)" />}
                        {low  > 0 && <Pill value={low}  label="L" color="#8e8e93" bg="rgba(142,142,147,0.10)" />}
                      </div>
                    )}

                    {/* Download buttons */}
                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => handleDownload(e, scan.id, "pdf")}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-secondary px-3 py-2 text-[13px] font-medium text-foreground hover:bg-border transition-colors"
                      >
                        <Download className="h-3.5 w-3.5" />
                        PDF
                      </button>
                      <button
                        onClick={(e) => handleDownload(e, scan.id, "json")}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-secondary px-3 py-2 text-[13px] font-medium text-foreground hover:bg-border transition-colors"
                      >
                        <Download className="h-3.5 w-3.5" />
                        JSON
                      </button>
                      <Link
                        href={`/scans/${scan.id}`}
                        className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-[13px] font-semibold transition-opacity hover:opacity-90"
                        style={{ background: "#0071e3", color: "#fff" }}
                      >
                        Bekijken
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    </div>
                  </div>
                </div>

                {/* Summary bar if AI analysis available */}
                {scan.ai_analysis?.management_summary && (
                  <div
                    className="px-5 pb-4 pt-0"
                    style={{ borderTop: "1px solid #e5e5ea" }}
                  >
                    <p className="text-[13px] text-muted-foreground mt-3 line-clamp-2">
                      {scan.ai_analysis.management_summary}
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Pill({ value, label, color, bg }: { value: number; label: string; color: string; bg: string }) {
  return (
    <span
      className="rounded-full px-2 py-0.5 text-[11px] font-semibold"
      style={{ background: bg, color }}
    >
      {value}{label}
    </span>
  );
}

function EmptyState() {
  return (
    <div className="rounded-2xl border border-border bg-card p-16 text-center shadow-apple">
      <FileText className="h-12 w-12 text-muted-foreground/20 mx-auto mb-4" />
      <p className="text-[17px] font-semibold mb-2">Geen rapporten</p>
      <p className="text-[14px] text-muted-foreground mb-6">
        Rapporten verschijnen hier nadat een scan voltooid is.
      </p>
      <Link
        href="/scans/new"
        className="inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-[14px] font-semibold transition-opacity hover:opacity-90"
        style={{ background: "#0071e3", color: "#fff" }}
      >
        <Plus className="h-4 w-4" />
        Scan starten
      </Link>
    </div>
  );
}

function SkeletonList() {
  return (
    <div className="space-y-3">
      {[...Array(3)].map((_, i) => (
        <div key={i} className="rounded-2xl border border-border bg-card p-5 shadow-apple animate-pulse">
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-xl bg-muted flex-shrink-0" />
            <div className="flex-1">
              <div className="h-4 w-48 rounded bg-muted mb-2" />
              <div className="h-3 w-32 rounded bg-muted" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
