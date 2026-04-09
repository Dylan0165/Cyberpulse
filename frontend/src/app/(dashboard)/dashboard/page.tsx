"use client";

import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import {
  Shield,
  Target,
  AlertTriangle,
  CheckCircle,
  Clock,
  Activity,
  ArrowRight,
  Wrench,
} from "lucide-react";

export default function DashboardPage() {
  const { data: scans } = useQuery({
    queryKey: ["scans"],
    queryFn: () => dashboardApi.listScans(1, 10),
  });

  const { data: targets } = useQuery({
    queryKey: ["targets"],
    queryFn: dashboardApi.listTargets,
  });

  const recentScans = scans?.items ?? [];
  const totalTargets = targets?.length ?? 0;

  const completedScans = recentScans.filter(
    (s: any) => s.status === "completed"
  ).length;
  const runningScans = recentScans.filter(
    (s: any) => s.status === "running"
  ).length;

  const totalFindings = recentScans.reduce(
    (sum: number, s: any) =>
      sum + (s.findings_critical ?? 0) + (s.findings_high ?? 0) + (s.findings_medium ?? 0) + (s.findings_low ?? 0) + (s.findings_info ?? 0),
    0
  );

  const criticalFindings = recentScans.reduce(
    (sum: number, s: any) => sum + (s.findings_critical ?? 0),
    0
  );

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between border-b border-border pb-4">
        <h1 className="text-[18px] font-bold tracking-[0.05em]">Dashboard</h1>
        <Link href="/scans/new">
          <Button className="text-[12px] uppercase tracking-[0.05em]">
            + Nieuwe scan
          </Button>
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-[1px] bg-border grid-cols-4">
        {[
          { label: "Targets", value: totalTargets, icon: Target },
          { label: "Scans", value: completedScans, icon: Activity, sub: runningScans > 0 ? `${runningScans} actief` : undefined },
          { label: "Bevindingen", value: totalFindings, icon: AlertTriangle },
          { label: "Kritiek", value: criticalFindings, icon: Shield, critical: true },
        ].map((s) => (
          <div key={s.label} className="bg-card p-4">
            <div className="text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-1">{s.label}</div>
            <div className={`text-[24px] font-bold ${s.critical && criticalFindings > 0 ? "text-[var(--critical)]" : ""}`}>
              {s.value}
            </div>
            {s.sub && <div className="text-[10px] text-muted-foreground">{s.sub}</div>}
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="grid gap-[1px] bg-border grid-cols-3">
        <Link href="/targets" className="bg-card p-4 hover:bg-secondary transition-colors">
          <div className="flex items-center gap-2 text-[12px] uppercase tracking-[0.05em]">
            <Target className="h-4 w-4" /> Target toevoegen
          </div>
        </Link>
        <Link href="/scans/new" className="bg-card p-4 hover:bg-secondary transition-colors">
          <div className="flex items-center gap-2 text-[12px] uppercase tracking-[0.05em]">
            <Shield className="h-4 w-4" /> Pentest starten
          </div>
        </Link>
        <Link href="/tools" className="bg-card p-4 hover:bg-secondary transition-colors">
          <div className="flex items-center gap-2 text-[12px] uppercase tracking-[0.05em]">
            <Wrench className="h-4 w-4" /> Kali Tools
          </div>
        </Link>
      </div>

      {/* Recent Scans */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-[11px] uppercase tracking-[0.1em] text-muted-foreground">Recente scans</h2>
          <Link href="/scans" className="text-[11px] text-muted-foreground hover:text-foreground">
            Alles bekijken ?
          </Link>
        </div>

        {recentScans.length === 0 ? (
          <div className="border bg-card p-8 text-center text-muted-foreground text-[12px]">
            Nog geen scans. Start je eerste pentest.
          </div>
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b">
                <th className="text-left text-[10px] uppercase tracking-[0.1em] text-muted-foreground font-normal p-2">Type</th>
                <th className="text-left text-[10px] uppercase tracking-[0.1em] text-muted-foreground font-normal p-2">Status</th>
                <th className="text-left text-[10px] uppercase tracking-[0.1em] text-muted-foreground font-normal p-2">Bevindingen</th>
                <th className="text-right text-[10px] uppercase tracking-[0.1em] text-muted-foreground font-normal p-2">Datum</th>
              </tr>
            </thead>
            <tbody>
              {recentScans.slice(0, 8).map((scan: any) => (
                <tr key={scan.id} className="border-b hover:bg-secondary/50 transition-colors">
                  <td className="p-2 text-[12px]">
                    <Link href={`/scans/${scan.id}`} className="font-medium hover:underline">
                      {scan.scan_type}
                    </Link>
                  </td>
                  <td className="p-2">
                    <StatusBadge status={scan.status} />
                  </td>
                  <td className="p-2 text-[12px]">
                    {(scan.findings_critical ?? 0) + (scan.findings_high ?? 0) + (scan.findings_medium ?? 0) + (scan.findings_low ?? 0)}
                  </td>
                  <td className="p-2 text-[12px] text-muted-foreground text-right">
                    {new Date(scan.created_at).toLocaleDateString("nl-NL", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    completed: "text-green-600",
    running: "text-blue-500 animate-pulse",
    failed: "text-[var(--critical)]",
  };

  return (
    <span className={`text-[11px] uppercase tracking-[0.05em] font-medium ${styles[status] ?? "text-muted-foreground"}`}>
      {status === "completed" ? "? " : status === "running" ? "? " : "? "}
      {status.replace("_", " ")}
    </span>
  );
}
