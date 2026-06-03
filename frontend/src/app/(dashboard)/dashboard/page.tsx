"use client";

import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/lib/api";
import Link from "next/link";
import {
  Shield,
  Target,
  AlertTriangle,
  Activity,
  ArrowRight,
  Plus,
} from "lucide-react";

export default function DashboardPage() {
  const { data: scansData } = useQuery({
    queryKey: ["scans"],
    queryFn: () => dashboardApi.listScans(1, 20),
  });

  const { data: targets } = useQuery({
    queryKey: ["targets"],
    queryFn: dashboardApi.listTargets,
  });

  const recentScans = scansData?.items ?? [];
  const totalTargets = targets?.length ?? 0;

  const completedScans = recentScans.filter((s: any) => s.status === "completed").length;
  const runningScans = recentScans.filter((s: any) => s.status === "running").length;
  const totalFindings = recentScans.reduce(
    (sum: number, s: any) =>
      sum +
      (s.findings_critical ?? 0) +
      (s.findings_high ?? 0) +
      (s.findings_medium ?? 0) +
      (s.findings_low ?? 0),
    0
  );
  const criticalFindings = recentScans.reduce(
    (sum: number, s: any) => sum + (s.findings_critical ?? 0),
    0
  );

  const stats = [
    {
      label: "Targets",
      value: totalTargets,
      icon: Target,
      href: "/targets",
    },
    {
      label: "Scans voltooid",
      value: completedScans,
      icon: Activity,
      sub: runningScans > 0 ? `${runningScans} actief` : undefined,
      href: "/scans",
    },
    {
      label: "Bevindingen",
      value: totalFindings,
      icon: AlertTriangle,
      href: "/scans",
    },
    {
      label: "Kritiek",
      value: criticalFindings,
      icon: Shield,
      critical: criticalFindings > 0,
      href: "/scans",
    },
  ];

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold tracking-tight">Dashboard</h1>
        <Link
          href="/scans/new"
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Nieuwe scan
        </Link>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-4">
        {stats.map((s) => {
          const Icon = s.icon;
          return (
            <Link key={s.label} href={s.href}>
              <div className="rounded-lg border border-border bg-card p-5 hover:border-primary/30 transition-colors">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    {s.label}
                  </span>
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </div>
                <div
                  className={`text-3xl font-bold tracking-tight ${
                    s.critical ? "text-red-400" : "text-foreground"
                  }`}
                >
                  {s.value}
                </div>
                {s.sub && (
                  <p className="text-xs text-primary mt-1">{s.sub}</p>
                )}
              </div>
            </Link>
          );
        })}
      </div>

      {/* Recent scans */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-foreground">Recente scans</h2>
          <Link
            href="/scans"
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            Alles bekijken <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        {recentScans.length === 0 ? (
          <div className="rounded-lg border border-border bg-card px-6 py-12 text-center">
            <Shield className="h-8 w-8 text-muted-foreground/30 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">
              Nog geen scans. Start je eerste pentest.
            </p>
            <Link
              href="/scans/new"
              className="inline-flex items-center gap-2 mt-4 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
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
                    Type
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
                </tr>
              </thead>
              <tbody>
                {recentScans.slice(0, 8).map((scan: any, i: number) => (
                  <tr
                    key={scan.id}
                    className={`hover:bg-secondary/50 transition-colors ${
                      i < recentScans.slice(0, 8).length - 1 ? "border-b border-border" : ""
                    }`}
                  >
                    <td className="px-4 py-3">
                      <Link
                        href={`/scans/${scan.id}`}
                        className="text-sm font-medium hover:text-primary transition-colors"
                      >
                        {scan.scan_type?.replace("_", " ") ?? "scan"}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={scan.status} />
                    </td>
                    <td className="px-4 py-3">
                      <FindingsSummary scan={scan} />
                    </td>
                    <td className="px-4 py-3 text-right text-xs text-muted-foreground">
                      {new Date(scan.created_at).toLocaleDateString("nl-NL", {
                        day: "2-digit",
                        month: "short",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { color: string; dot: string; label: string }> = {
    completed:  { color: "text-emerald-400", dot: "bg-emerald-500",  label: "Voltooid" },
    running:    { color: "text-blue-400",    dot: "bg-blue-500 animate-pulse", label: "Actief" },
    pending:    { color: "text-yellow-400",  dot: "bg-yellow-500",   label: "Wachtend" },
    analyzing:  { color: "text-purple-400",  dot: "bg-purple-500 animate-pulse", label: "Analyseren" },
    failed:     { color: "text-red-400",     dot: "bg-red-500",      label: "Mislukt" },
    cancelled:  { color: "text-muted-foreground", dot: "bg-muted-foreground", label: "Geannuleerd" },
  };
  const c = config[status] ?? { color: "text-muted-foreground", dot: "bg-muted-foreground", label: status };

  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${c.color}`}>
      <span className={`h-1.5 w-1.5 rounded-full flex-shrink-0 ${c.dot}`} />
      {c.label}
    </span>
  );
}

function FindingsSummary({ scan }: { scan: any }) {
  const crit = scan.findings_critical ?? 0;
  const high = scan.findings_high ?? 0;
  const med = scan.findings_medium ?? 0;

  if (crit + high + med === 0) {
    return <span className="text-xs text-muted-foreground">—</span>;
  }

  return (
    <div className="flex items-center gap-1.5">
      {crit > 0 && (
        <span className="inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-medium bg-red-500/10 text-red-400">
          {crit} kritiek
        </span>
      )}
      {high > 0 && (
        <span className="inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-medium bg-orange-500/10 text-orange-400">
          {high} hoog
        </span>
      )}
      {med > 0 && (
        <span className="inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-medium bg-yellow-500/10 text-yellow-400">
          {med} medium
        </span>
      )}
    </div>
  );
}
