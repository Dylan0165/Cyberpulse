"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { dashboardApi, reportsApi, targetsApi } from "@/lib/api";
import { toast } from "sonner";
import Link from "next/link";
import { motion } from "framer-motion";
import { Download, ArrowRight, Plus, Search, FileSearch } from "lucide-react";
import { GlowCard } from "@/components/cyber/glow-card";
import { SkeletonRow } from "@/components/cyber/skeleton";

type SeverityFilter = "all" | "critical" | "medium" | "low";
type SortMode = "newest" | "oldest" | "risk";

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
      toast.error("Download mislukt. Probeer opnieuw.");
    }
  };

  // ───── UI state: filter / sort / search ─────
  const [filter, setFilter] = useState<SeverityFilter>("all");
  const [sort, setSort] = useState<SortMode>("newest");
  const [query, setQuery] = useState("");

  const topSeverity = (s: any): SeverityFilter => {
    const crit = s.critical_count ?? s.findings_critical ?? 0;
    const high = s.high_count ?? s.findings_high ?? 0;
    const med = s.medium_count ?? s.findings_medium ?? 0;
    if (crit > 0 || high > 0) return "critical";
    if (med > 0) return "medium";
    return "low";
  };

  const riskOf = (s: any): number => {
    if (s.security_score != null) return Math.round(100 - s.security_score);
    const crit = s.critical_count ?? s.findings_critical ?? 0;
    const high = s.high_count ?? s.findings_high ?? 0;
    const med = s.medium_count ?? s.findings_medium ?? 0;
    const low = s.low_count ?? s.findings_low ?? 0;
    return Math.min(100, crit * 25 + high * 12 + med * 5 + low * 1);
  };

  const visibleScans = useMemo(() => {
    let list = [...completedScans];

    if (filter !== "all") {
      list = list.filter((s) => topSeverity(s) === filter);
    }

    const q = query.trim().toLowerCase();
    if (q) {
      list = list.filter((s) => {
        const display = (targetMap[s.target_id] ?? s.target_id ?? "").toLowerCase();
        return display.includes(q);
      });
    }

    list.sort((a, b) => {
      if (sort === "risk") return riskOf(b) - riskOf(a);
      const ta = new Date(a.completed_at ?? a.created_at).getTime();
      const tb = new Date(b.completed_at ?? b.created_at).getTime();
      return sort === "newest" ? tb - ta : ta - tb;
    });

    return list;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [completedScans, filter, sort, query, targetsData]);

  return (
    <div className="space-y-6">
      {/* ───── Header ───── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1
            className="font-display text-[30px] font-bold text-ink"
            style={{ letterSpacing: "-0.03em" }}
          >
            Reports
          </h1>
          <p className="mt-1 text-[14px] text-ink-muted">
            Download en bekijk voltooide pentest rapporten
          </p>
        </div>
        <Link
          href="/scans/new"
          className="inline-flex items-center gap-2 rounded-lg bg-cyan px-5 py-2.5 text-[14px] font-semibold text-black transition-opacity duration-150 hover:opacity-90 shadow-glow-cyan"
        >
          <Plus className="h-4 w-4" />
          Nieuwe scan
        </Link>
      </div>

      {/* ───── Controls ───── */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          {/* Severity filter pills */}
          <div className="flex items-center gap-1.5">
            {([
              ["all", "All"],
              ["critical", "Critical"],
              ["medium", "Medium"],
              ["low", "Low"],
            ] as [SeverityFilter, string][]).map(([key, label]) => (
              <Pill
                key={key}
                active={filter === key}
                onClick={() => setFilter(key)}
              >
                {label}
              </Pill>
            ))}
          </div>

          {/* Sort pills */}
          <span className="mx-1 hidden h-4 w-px bg-grid sm:block" />
          <div className="flex items-center gap-1.5">
            {([
              ["newest", "Newest"],
              ["oldest", "Oldest"],
              ["risk", "Risk Score"],
            ] as [SortMode, string][]).map(([key, label]) => (
              <Pill
                key={key}
                active={sort === key}
                onClick={() => setSort(key)}
              >
                {label}
              </Pill>
            ))}
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Zoek op IP / hostname"
            className="w-full rounded-lg border border-grid bg-panel py-2 pl-9 pr-3 font-mono text-[13px] text-ink placeholder:text-ink-muted outline-none transition-colors duration-150 focus:border-cyan lg:w-64"
          />
        </div>
      </div>

      {/* ───── Body ───── */}
      {isLoading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <SkeletonRow key={i} />
          ))}
        </div>
      ) : visibleScans.length === 0 ? (
        <EmptyState hasReports={completedScans.length > 0} />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {visibleScans.map((scan: any, index: number) => {
            // ScanResponse uses critical_count / high_count / medium_count / low_count
            const crit = scan.critical_count ?? scan.findings_critical ?? 0;
            const high = scan.high_count ?? scan.findings_high ?? 0;
            const med = scan.medium_count ?? scan.findings_medium ?? 0;
            const low = scan.low_count ?? scan.findings_low ?? 0;
            const total = crit + high + med + low;
            const risk = riskOf(scan);
            const riskColor =
              risk >= 70 ? "#FF2D55" : risk >= 40 ? "#FF8C00" : "#00FF88";
            const targetDisplay = targetMap[scan.target_id] ?? scan.target_id ?? "—";

            return (
              <motion.div
                key={scan.id}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
              >
                <GlowCard
                  glowColor={riskColor}
                  accentBorder={crit > 0 ? "#FF2D55" : undefined}
                  className="h-full"
                >
                  <div className="flex items-stretch gap-4 p-5">
                    {/* Left: risk score box */}
                    <div className="flex flex-shrink-0 flex-col items-center justify-center">
                      <div
                        className="flex h-16 w-16 flex-col items-center justify-center rounded-lg"
                        style={{
                          background: `${riskColor}14`,
                          border: `1px solid ${riskColor}55`,
                          boxShadow: `0 0 18px ${riskColor}33`,
                        }}
                      >
                        <span
                          className="font-display text-[24px] font-bold leading-none"
                          style={{ color: riskColor }}
                        >
                          {risk}
                        </span>
                        <span className="mt-1 text-[9px] font-semibold uppercase tracking-widest text-ink-muted">
                          Risk
                        </span>
                      </div>
                    </div>

                    {/* Center: target, date, findings */}
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-mono text-[15px] font-semibold text-ink">
                        {targetDisplay}
                      </p>
                      <p className="mt-0.5 font-mono text-[12px] text-ink-muted">
                        {scan.scan_type?.replace(/_/g, " ") ?? "pentest"}
                        {" · "}
                        {new Date(
                          scan.completed_at ?? scan.created_at,
                        ).toLocaleDateString("nl-NL", {
                          day: "2-digit",
                          month: "short",
                          year: "numeric",
                        })}
                      </p>

                      {/* Findings dots */}
                      {total > 0 ? (
                        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1.5">
                          {crit > 0 && <Dot color="#FF2D55" count={crit} label="K" />}
                          {high > 0 && <Dot color="#FF8C00" count={high} label="H" />}
                          {med > 0 && <Dot color="#FFD60A" count={med} label="M" />}
                          {low > 0 && <Dot color="#0A84FF" count={low} label="L" />}
                        </div>
                      ) : (
                        <p className="mt-3 font-mono text-[11px] text-neon-green">
                          Geen findings
                        </p>
                      )}
                    </div>

                    {/* Right: actions */}
                    <div className="flex flex-shrink-0 flex-col items-end justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <button
                          title="Download PDF"
                          onClick={(e) => handleDownload(e, scan.id, "pdf")}
                          className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-grid bg-panel text-ink-muted transition-colors duration-150 hover:border-cyan hover:text-cyan"
                        >
                          <Download className="h-4 w-4" />
                        </button>
                        <button
                          title="Download JSON"
                          onClick={(e) => handleDownload(e, scan.id, "json")}
                          className="inline-flex h-8 items-center justify-center rounded-md border border-grid bg-panel px-2 font-mono text-[11px] font-semibold text-ink-muted transition-colors duration-150 hover:border-cyan hover:text-cyan"
                        >
                          JSON
                        </button>
                      </div>
                      <Link
                        href={`/scans/${scan.id}`}
                        className="inline-flex items-center gap-1.5 rounded-md border border-grid bg-panel px-3 py-1.5 text-[12px] font-semibold text-ink transition-colors duration-150 hover:border-cyan hover:text-cyan"
                      >
                        Bekijken
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    </div>
                  </div>

                  {/* Summary bar if AI analysis available */}
                  {scan.ai_analysis?.management_summary && (
                    <div className="border-t border-grid px-5 py-3">
                      <p className="line-clamp-2 text-[12px] text-ink-muted">
                        {scan.ai_analysis.management_summary}
                      </p>
                    </div>
                  )}
                </GlowCard>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Pill({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={
        "rounded-lg border px-3 py-1.5 text-[12px] font-semibold transition-colors duration-150 " +
        (active
          ? "border-cyan bg-cyan/10 text-cyan shadow-glow-cyan"
          : "border-grid bg-panel text-ink-muted hover:border-cyan/40 hover:text-ink")
      }
    >
      {children}
    </button>
  );
}

function Dot({ color, count, label }: { color: string; count: number; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 font-mono text-[12px] text-ink">
      <span
        className="h-2 w-2 rounded-full"
        style={{ background: color, boxShadow: `0 0 8px ${color}` }}
      />
      <span style={{ color }}>{count}</span>
      <span className="text-ink-muted">{label}</span>
    </span>
  );
}

function EmptyState({ hasReports }: { hasReports: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-grid bg-card2 px-6 py-20 text-center">
      <motion.div
        animate={{ opacity: [0.4, 1, 0.4], scale: [0.98, 1.02, 0.98] }}
        transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
      >
        <FileSearch className="h-12 w-12 text-cyan" />
      </motion.div>
      <p className="mt-5 font-display text-[17px] font-semibold text-ink">
        {hasReports ? "Geen resultaten" : "No reports yet"}
      </p>
      <p className="mt-2 max-w-sm text-[13px] text-ink-muted">
        {hasReports
          ? "Geen rapporten gevonden voor deze filters."
          : "Run your first scan to generate a report."}
      </p>
      {!hasReports && (
        <Link
          href="/scans/new"
          className="mt-6 inline-flex items-center gap-2 rounded-lg bg-cyan px-5 py-2.5 text-[14px] font-semibold text-black transition-opacity duration-150 hover:opacity-90 shadow-glow-cyan"
        >
          <Plus className="h-4 w-4" />
          Scan starten
        </Link>
      )}
    </div>
  );
}
