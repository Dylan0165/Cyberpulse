"use client";

import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/lib/api";
import Link from "next/link";
import { useState } from "react";
import { Shield, Plus, Search, ArrowRight, Download } from "lucide-react";
import { scanTypeLabel, statusLabel } from "@/lib/labels";

type StatusFilter = "all" | "running" | "completed" | "failed" | "pending";

export default function ScansPage() {
  const { data: scansData, isLoading } = useQuery({
    queryKey: ["scans"],
    queryFn: () => dashboardApi.listScans(1, 100),
  });

  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<StatusFilter>("all");

  const all = scansData?.items ?? [];
  const scans = all.filter((s: any) => {
    const matchStatus = filter === "all" || s.status === filter;
    const matchSearch =
      !search ||
      (s.scan_type ?? "").toLowerCase().includes(search.toLowerCase()) ||
      ((s.target_value ?? s.target_id ?? "")).toLowerCase().includes(search.toLowerCase());
    return matchStatus && matchSearch;
  });

  const counts: Record<StatusFilter, number> = {
    all: all.length,
    running: all.filter((s: any) => s.status === "running").length,
    completed: all.filter((s: any) => s.status === "completed").length,
    failed: all.filter((s: any) => s.status === "failed").length,
    pending: all.filter((s: any) => ["pending", "analyzing"].includes(s.status)).length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[28px] font-bold" style={{ letterSpacing: "-0.03em" }}>
            Scan Geschiedenis
          </h1>
          <p className="text-[15px] text-muted-foreground mt-0.5">
            Overzicht van alle penetratietests
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

      {/* Filter tabs + search */}
      <div className="flex items-center gap-4">
        <div className="flex rounded-xl border border-border bg-card p-1 gap-0.5">
          {(["all", "running", "completed", "failed", "pending"] as StatusFilter[]).map((f) => {
            const labels: Record<StatusFilter, string> = {
              all: "Alle",
              running: "Actief",
              completed: "Voltooid",
              failed: "Mislukt",
              pending: "Wachtend",
            };
            return (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className="rounded-lg px-3 py-1.5 text-[13px] font-medium transition-colors"
                style={{
                  background: filter === f ? "#fff" : "transparent",
                  color: filter === f ? "#1d1d1f" : "#6e6e73",
                  boxShadow: filter === f ? "0 1px 4px rgba(0,0,0,0.08)" : "none",
                }}
              >
                {labels[f]} {counts[f] > 0 && <span className="ml-1 opacity-60">{counts[f]}</span>}
              </button>
            );
          })}
        </div>
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Zoek op type of target..."
            className="w-full rounded-xl border border-border bg-card pl-9 pr-4 py-2.5 text-[14px] placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <SkeletonTable />
      ) : scans.length === 0 ? (
        <EmptyState hasFilter={filter !== "all" || !!search} />
      ) : (
        <div className="rounded-2xl border border-border bg-card shadow-apple overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border" style={{ background: "#f5f5f7" }}>
                {["Target / Type", "Modus", "Status", "Bevindingen", "Datum", ""].map((h) => (
                  <th
                    key={h}
                    className={`text-[11px] font-semibold text-muted-foreground uppercase tracking-wider px-5 py-3.5 ${
                      h === "" ? "w-8" : "text-left"
                    }`}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {scans.map((scan: any, i: number) => (
                <tr
                  key={scan.id}
                  className={`group hover:bg-secondary/60 transition-colors cursor-pointer ${
                    i < scans.length - 1 ? "border-b border-border" : ""
                  }`}
                  onClick={() => (window.location.href = `/scans/${scan.id}`)}
                >
                  <td className="px-5 py-4">
                    <p className="text-[14px] font-semibold font-mono">
                      {scan.target_value ?? (scan.scan_type?.replace(/_/g, " ") ?? "scan")}
                    </p>
                    <p className="text-[12px] text-muted-foreground mt-0.5">
                      {scan.scan_type?.replace(/_/g, " ") ?? "scan"}
                    </p>
                  </td>
                  <td className="px-5 py-4">
                    <ModeBadge mode={scan.scan_mode} />
                  </td>
                  <td className="px-5 py-4">
                    <StatusIndicator status={scan.status} progress={scan.progress} />
                  </td>
                  <td className="px-5 py-4">
                    <FindingsSummary scan={scan} />
                  </td>
                  <td className="px-5 py-4 text-[13px] text-muted-foreground whitespace-nowrap">
                    {new Date(scan.created_at).toLocaleDateString("nl-NL", {
                      day: "2-digit",
                      month: "short",
                      year: "numeric",
                    })}
                  </td>
                  <td className="px-4 py-4 text-right">
                    <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ModeBadge({ mode }: { mode?: string }) {
  if (!mode) return <span className="text-[13px] text-muted-foreground">—</span>;
  const map: Record<string, { bg: string; color: string }> = {
    blackbox: { bg: "rgba(255,59,48,0.08)",   color: "#ff3b30" },
    graybox:  { bg: "rgba(255,149,0,0.08)",   color: "#ff9500" },
    whitebox: { bg: "rgba(52,199,89,0.08)",   color: "#34c759" },
  };
  const s = map[mode] ?? { bg: "#f5f5f7", color: "#6e6e73" };
  const label = scanTypeLabel(mode);
  return (
    <span
      className="inline-flex rounded-full px-2.5 py-1 text-[12px] font-semibold"
      style={{ background: s.bg, color: s.color }}
    >
      {label}
    </span>
  );
}

function StatusIndicator({ status, progress }: { status: string; progress?: number }) {
  const map: Record<string, { color: string; pulse?: boolean }> = {
    completed:  { color: "#34c759" },
    running:    { color: "#0071e3", pulse: true },
    pending:    { color: "#ff9500" },
    analyzing:  { color: "#bf5af2", pulse: true },
    failed:     { color: "#ff3b30" },
    cancelled:  { color: "#8e8e93" },
  };
  const s = map[status] ?? { color: "#8e8e93" };
  const label = statusLabel(status);
  return (
    <div className="flex items-center gap-1.5">
      <span
        className={`h-2 w-2 rounded-full flex-shrink-0 ${s.pulse ? "animate-pulse" : ""}`}
        style={{ background: s.color }}
      />
      <span className="text-[13px] font-medium" style={{ color: s.color }}>
        {label}
      </span>
      {status === "running" && progress != null && progress > 0 && (
        <span className="text-[12px] text-muted-foreground">({progress}%)</span>
      )}
    </div>
  );
}

function FindingsSummary({ scan }: { scan: any }) {
  const crit = scan.findings_critical ?? 0;
  const high = scan.findings_high ?? 0;
  const med  = scan.findings_medium ?? 0;
  const low  = scan.findings_low ?? 0;
  const total = crit + high + med + low;

  if (total === 0 && scan.status !== "completed")
    return <span className="text-[13px] text-muted-foreground">—</span>;
  if (total === 0)
    return <span className="text-[13px] font-medium" style={{ color: "#34c759" }}>Schoon</span>;

  return (
    <div className="flex items-center gap-1.5">
      {crit > 0 && <span className="rounded-full px-2 py-0.5 text-[11px] font-semibold" style={{ background: "rgba(255,59,48,0.10)", color: "#ff3b30" }}>{crit}K</span>}
      {high > 0 && <span className="rounded-full px-2 py-0.5 text-[11px] font-semibold" style={{ background: "rgba(255,149,0,0.10)", color: "#ff9500" }}>{high}H</span>}
      {med  > 0 && <span className="rounded-full px-2 py-0.5 text-[11px] font-semibold" style={{ background: "rgba(255,204,0,0.12)", color: "#c69b00" }}>{med}M</span>}
      {low  > 0 && <span className="rounded-full px-2 py-0.5 text-[11px] font-semibold" style={{ background: "rgba(142,142,147,0.10)", color: "#8e8e93" }}>{low}L</span>}
    </div>
  );
}

function EmptyState({ hasFilter }: { hasFilter: boolean }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-16 text-center shadow-apple">
      <Shield className="h-12 w-12 text-muted-foreground/20 mx-auto mb-4" />
      <p className="text-[17px] font-semibold mb-2">
        {hasFilter ? "Geen resultaten" : "Nog geen scans uitgevoerd"}
      </p>
      <p className="text-[14px] text-muted-foreground mb-6">
        {hasFilter
          ? "Pas de filters aan of wis de zoekopdracht."
          : "Start je eerste penetratietest om resultaten te zien."}
      </p>
      {!hasFilter && (
        <Link
          href="/scans/new"
          className="inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-[14px] font-semibold transition-opacity hover:opacity-90"
          style={{ background: "#0071e3", color: "#fff" }}
        >
          <Plus className="h-4 w-4" />
          Scan starten
        </Link>
      )}
    </div>
  );
}

function SkeletonTable() {
  return (
    <div className="rounded-2xl border border-border bg-card shadow-apple overflow-hidden">
      {[...Array(5)].map((_, i) => (
        <div key={i} className={`flex items-center gap-4 px-5 py-4 ${i < 4 ? "border-b border-border" : ""}`}>
          <div className="h-4 w-32 rounded animate-pulse bg-muted" />
          <div className="h-4 w-16 rounded-full animate-pulse bg-muted ml-8" />
          <div className="h-4 w-20 rounded animate-pulse bg-muted ml-8" />
          <div className="h-4 w-24 rounded animate-pulse bg-muted ml-auto" />
        </div>
      ))}
    </div>
  );
}
