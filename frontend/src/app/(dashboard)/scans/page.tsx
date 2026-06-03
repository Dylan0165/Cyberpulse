"use client";

import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/lib/api";
import Link from "next/link";
import {
  Shield,
  Plus,
  ArrowRight,
  Activity,
  CheckCircle,
  Clock,
  AlertTriangle,
  XCircle,
} from "lucide-react";

export default function ScansPage() {
  const { data: scansData, isLoading } = useQuery({
    queryKey: ["scans"],
    queryFn: () => dashboardApi.listScans(1, 50),
  });

  const scans = scansData?.items ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Scans</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Overzicht van alle pentests
          </p>
        </div>
        <Link
          href="/scans/new"
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Nieuwe scan
        </Link>
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-sm text-muted-foreground">
          Laden...
        </div>
      ) : scans.length === 0 ? (
        <div className="rounded-lg border border-border bg-card px-6 py-16 text-center">
          <Shield className="h-10 w-10 text-muted-foreground/20 mx-auto mb-4" />
          <p className="text-sm text-muted-foreground mb-4">
            Nog geen scans. Start je eerste penetratietest.
          </p>
          <Link
            href="/scans/new"
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Scan starten
          </Link>
        </div>
      ) : (
        <div className="rounded-lg border border-border bg-card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                  Target / Type
                </th>
                <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                  Modus
                </th>
                <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                  Status
                </th>
                <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                  Bevindingen
                </th>
                <th className="text-right text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                  Datum
                </th>
                <th className="w-8 px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {scans.map((scan: any, i: number) => (
                <tr
                  key={scan.id}
                  className={`group hover:bg-secondary/40 transition-colors cursor-pointer ${
                    i < scans.length - 1 ? "border-b border-border" : ""
                  }`}
                  onClick={() => (window.location.href = `/scans/${scan.id}`)}
                >
                  <td className="px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        {scan.scan_type?.replace(/_/g, " ") ?? "scan"}
                      </p>
                      {scan.target_id && (
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {scan.target_id}
                        </p>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <ScanModeBadge mode={scan.scan_mode} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={scan.status} progress={scan.progress} />
                  </td>
                  <td className="px-4 py-3">
                    <FindingsSummary scan={scan} />
                  </td>
                  <td className="px-4 py-3 text-right text-xs text-muted-foreground whitespace-nowrap">
                    {new Date(scan.created_at).toLocaleDateString("nl-NL", {
                      day: "2-digit",
                      month: "short",
                      year: "numeric",
                    })}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <ArrowRight className="h-4 w-4 text-muted-foreground/0 group-hover:text-muted-foreground transition-colors" />
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

function ScanModeBadge({ mode }: { mode?: string }) {
  if (!mode) return <span className="text-xs text-muted-foreground">—</span>;

  const config: Record<string, { label: string; className: string }> = {
    blackbox: { label: "Blackbox", className: "text-red-400 bg-red-400/10 border-red-400/20" },
    graybox:  { label: "Graybox",  className: "text-yellow-400 bg-yellow-400/10 border-yellow-400/20" },
    whitebox: { label: "Whitebox", className: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20" },
  };
  const c = config[mode] ?? { label: mode, className: "text-muted-foreground bg-muted border-border" };

  return (
    <span className={`inline-flex items-center rounded border px-2 py-0.5 text-[11px] font-medium ${c.className}`}>
      {c.label}
    </span>
  );
}

function StatusBadge({ status, progress }: { status: string; progress?: number }) {
  const config: Record<string, { color: string; dot: string; label: string }> = {
    completed:  { color: "text-emerald-400", dot: "bg-emerald-500",             label: "Voltooid" },
    running:    { color: "text-blue-400",    dot: "bg-blue-500 animate-pulse",  label: "Actief" },
    pending:    { color: "text-yellow-400",  dot: "bg-yellow-500",              label: "Wachtend" },
    analyzing:  { color: "text-purple-400",  dot: "bg-purple-500 animate-pulse", label: "Analyseren" },
    failed:     { color: "text-red-400",     dot: "bg-red-500",                 label: "Mislukt" },
    cancelled:  { color: "text-muted-foreground", dot: "bg-muted-foreground",   label: "Geannuleerd" },
  };
  const c = config[status] ?? { color: "text-muted-foreground", dot: "bg-muted-foreground", label: status };

  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${c.color}`}>
      <span className={`h-1.5 w-1.5 rounded-full flex-shrink-0 ${c.dot}`} />
      {c.label}
      {status === "running" && progress != null && progress > 0 && (
        <span className="text-muted-foreground">({progress}%)</span>
      )}
    </span>
  );
}

function FindingsSummary({ scan }: { scan: any }) {
  const crit = scan.findings_critical ?? 0;
  const high = scan.findings_high ?? 0;
  const med  = scan.findings_medium ?? 0;
  const low  = scan.findings_low ?? 0;

  const total = crit + high + med + low;
  if (total === 0 && scan.status !== "completed") {
    return <span className="text-xs text-muted-foreground">—</span>;
  }
  if (total === 0) {
    return <span className="text-xs text-emerald-400">Schoon</span>;
  }

  return (
    <div className="flex items-center gap-1.5">
      {crit > 0 && (
        <span className="rounded px-1.5 py-0.5 text-[11px] font-medium bg-red-500/10 text-red-400">
          {crit}K
        </span>
      )}
      {high > 0 && (
        <span className="rounded px-1.5 py-0.5 text-[11px] font-medium bg-orange-500/10 text-orange-400">
          {high}H
        </span>
      )}
      {med > 0 && (
        <span className="rounded px-1.5 py-0.5 text-[11px] font-medium bg-yellow-500/10 text-yellow-400">
          {med}M
        </span>
      )}
      {low > 0 && (
        <span className="rounded px-1.5 py-0.5 text-[11px] font-medium bg-muted text-muted-foreground">
          {low}L
        </span>
      )}
    </div>
  );
}
