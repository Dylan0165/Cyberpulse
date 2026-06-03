"use client";

import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/lib/api";
import Link from "next/link";
import { Sparkles, Shield, AlertTriangle, ArrowRight, Plus } from "lucide-react";

export default function AiAnalysisPage() {
  const { data: scansData, isLoading } = useQuery({
    queryKey: ["scans-completed"],
    queryFn: () => dashboardApi.listScans(1, 50),
  });

  const scansWithAI = (scansData?.items ?? []).filter(
    (s: any) => s.status === "completed" && s.ai_analysis,
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-[28px] font-bold" style={{ letterSpacing: "-0.03em" }}>
          AI Analyse
        </h1>
        <p className="text-[15px] text-muted-foreground mt-0.5">
          DeepSeek AI beveiligingsanalyse per scan
        </p>
      </div>

      {isLoading ? (
        <SkeletonList />
      ) : scansWithAI.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="space-y-6">
          {scansWithAI.map((scan: any) => {
            const ai = scan.ai_analysis;
            const riskScore = ai?.risk_score ?? 0;
            const riskLevel = (ai?.risk_level ?? "LOW").toUpperCase();
            const findings: any[] = ai?.findings ?? [];

            const riskColor =
              riskScore >= 70 ? "#ff3b30" :
              riskScore >= 40 ? "#ff9500" :
              "#34c759";

            return (
              <div
                key={scan.id}
                className="rounded-2xl border border-border bg-card shadow-apple overflow-hidden"
              >
                {/* Card header */}
                <div className="flex items-center justify-between px-6 py-5" style={{ borderBottom: "1px solid #e5e5ea" }}>
                  <div className="flex items-center gap-4">
                    <div
                      className="h-11 w-11 rounded-xl flex items-center justify-center flex-shrink-0"
                      style={{ background: "rgba(191,90,242,0.10)" }}
                    >
                      <Sparkles className="h-5 w-5" style={{ color: "#bf5af2" }} />
                    </div>
                    <div>
                      <p className="text-[15px] font-semibold">
                        {scan.scan_type?.replace(/_/g, " ") ?? "scan"} analyse
                      </p>
                      <p className="text-[13px] text-muted-foreground mt-0.5">
                        {new Date(scan.completed_at ?? scan.created_at).toLocaleDateString("nl-NL", {
                          day: "2-digit",
                          month: "long",
                          year: "numeric",
                        })}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-5">
                    {/* Risk gauge */}
                    <div className="text-center">
                      <p className="text-[11px] text-muted-foreground uppercase tracking-wider mb-1">
                        Risicoscore
                      </p>
                      <div className="flex items-baseline gap-1">
                        <span
                          className="text-[36px] font-bold leading-none"
                          style={{ color: riskColor, letterSpacing: "-0.03em" }}
                        >
                          {riskScore}
                        </span>
                        <span className="text-[13px] text-muted-foreground">/100</span>
                      </div>
                      <span
                        className="inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold mt-1"
                        style={{
                          background: `${riskColor}15`,
                          color: riskColor,
                        }}
                      >
                        {riskLevel}
                      </span>
                    </div>

                    <Link
                      href={`/scans/${scan.id}`}
                      className="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-[13px] font-semibold transition-opacity hover:opacity-90"
                      style={{ background: "#0071e3", color: "#fff" }}
                    >
                      Scan bekijken
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                </div>

                <div className="px-6 py-5 space-y-5">
                  {/* Management summary */}
                  {ai?.management_summary && (
                    <div>
                      <p className="text-[12px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                        Managementsamenvatting
                      </p>
                      <p className="text-[14px] leading-relaxed">
                        {ai.management_summary}
                      </p>
                    </div>
                  )}

                  {/* Findings */}
                  {findings.length > 0 && (
                    <div>
                      <p className="text-[12px] font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                        Bevindingen ({findings.length})
                      </p>
                      <div className="space-y-2">
                        {findings.slice(0, 5).map((f: any, i: number) => {
                          const sev = (f.severity ?? "info").toUpperCase();
                          const sevColor =
                            sev === "CRITICAL" ? "#ff3b30" :
                            sev === "HIGH"     ? "#ff9500" :
                            sev === "MEDIUM"   ? "#c69b00" :
                            sev === "LOW"      ? "#34c759" :
                            "#8e8e93";
                          return (
                            <div
                              key={i}
                              className="flex items-start gap-3 rounded-xl p-3"
                              style={{ background: "#f5f5f7" }}
                            >
                              <span
                                className="rounded-full px-2 py-0.5 text-[11px] font-semibold flex-shrink-0 mt-0.5"
                                style={{ background: `${sevColor}18`, color: sevColor }}
                              >
                                {sev.charAt(0) + sev.slice(1).toLowerCase()}
                              </span>
                              <div className="min-w-0">
                                <p className="text-[13px] font-medium truncate">
                                  {f.title ?? f.name ?? "Onbekende bevinding"}
                                </p>
                                {f.description && (
                                  <p className="text-[12px] text-muted-foreground mt-0.5 line-clamp-2">
                                    {f.description}
                                  </p>
                                )}
                                <div className="flex items-center gap-3 mt-1.5">
                                  {f.cve && (
                                    <span className="text-[11px] font-mono text-muted-foreground">
                                      {f.cve}
                                    </span>
                                  )}
                                  {f.owasp && (
                                    <span className="text-[11px] text-muted-foreground">
                                      OWASP: {f.owasp}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                        {findings.length > 5 && (
                          <Link
                            href={`/scans/${scan.id}`}
                            className="flex items-center gap-1.5 text-[13px] font-medium text-primary hover:underline px-3 py-1"
                          >
                            +{findings.length - 5} meer bevindingen bekijken
                            <ArrowRight className="h-3.5 w-3.5" />
                          </Link>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Remediation quick wins */}
                  {ai?.remediation_roadmap?.quick_wins?.length > 0 && (
                    <div>
                      <p className="text-[12px] font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                        Quick Wins
                      </p>
                      <div className="space-y-1.5">
                        {(ai.remediation_roadmap.quick_wins as string[]).slice(0, 3).map((win, i) => (
                          <div key={i} className="flex items-start gap-2 text-[13px]">
                            <span className="text-emerald-500 mt-0.5 flex-shrink-0">✓</span>
                            <span>{win}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="rounded-2xl border border-border bg-card p-16 text-center shadow-apple">
      <Sparkles className="h-12 w-12 text-muted-foreground/20 mx-auto mb-4" />
      <p className="text-[17px] font-semibold mb-2">Geen AI-analyses</p>
      <p className="text-[14px] text-muted-foreground mb-6">
        AI-analyse verschijnt hier nadat een scan voltooid is.
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
    <div className="space-y-6">
      {[...Array(2)].map((_, i) => (
        <div key={i} className="rounded-2xl border border-border bg-card shadow-apple overflow-hidden animate-pulse">
          <div className="flex items-center gap-4 px-6 py-5 border-b border-border">
            <div className="h-11 w-11 rounded-xl bg-muted flex-shrink-0" />
            <div className="flex-1">
              <div className="h-4 w-48 rounded bg-muted mb-2" />
              <div className="h-3 w-32 rounded bg-muted" />
            </div>
            <div className="h-10 w-20 rounded bg-muted" />
          </div>
          <div className="px-6 py-5 space-y-3">
            <div className="h-3 w-full rounded bg-muted" />
            <div className="h-3 w-4/5 rounded bg-muted" />
            <div className="h-3 w-3/5 rounded bg-muted" />
          </div>
        </div>
      ))}
    </div>
  );
}
