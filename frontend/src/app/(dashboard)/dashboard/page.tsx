"use client";

import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/lib/api";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Shield, Target, AlertTriangle, Activity, ArrowRight,
  Plus, Terminal, Zap, BarChart3,
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
  const [toolsAvail, setToolsAvail] = useState<number | null>(null);

  useEffect(() => {
    fetch("/api/tools/available")
      .then((r) => r.json())
      .then((d) => setToolsAvail(d.available_count ?? null))
      .catch(() => {});
  }, []);

  const recentScans = scansData?.items ?? [];
  const totalTargets = targets?.length ?? 0;
  const criticalFindings = recentScans.reduce(
    (sum: number, s: any) => sum + (s.findings_critical ?? 0), 0
  );
  const runningScans = recentScans.filter((s: any) => s.status === "running").length;

  // Scans this week
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  const scansThisWeek = recentScans.filter(
    (s: any) => new Date(s.created_at).getTime() > weekAgo
  ).length;

  const stats = [
    {
      label: "Totaal scans",
      value: recentScans.length,
      icon: Activity,
      color: "#0071e3",
      bg: "rgba(0,113,227,0.08)",
      sub: runningScans > 0 ? `${runningScans} actief` : undefined,
      href: "/scans",
    },
    {
      label: "Kritieke bevindingen",
      value: criticalFindings,
      icon: AlertTriangle,
      color: criticalFindings > 0 ? "#ff3b30" : "#34c759",
      bg: criticalFindings > 0 ? "rgba(255,59,48,0.08)" : "rgba(52,199,89,0.08)",
      href: "/scans",
    },
    {
      label: "Tools beschikbaar",
      value: toolsAvail ?? "—",
      icon: Terminal,
      color: "#34c759",
      bg: "rgba(52,199,89,0.08)",
      href: "/tools",
    },
    {
      label: "Scans deze week",
      value: scansThisWeek,
      icon: BarChart3,
      color: "#bf5af2",
      bg: "rgba(191,90,242,0.08)",
      href: "/scans",
    },
  ];

  return (
    <div className="space-y-8">
      {/* Hero */}
      <div className="rounded-2xl overflow-hidden" style={{ background: "linear-gradient(135deg, #1d1d1f 0%, #2d2d2f 100%)" }}>
        <div className="px-8 py-10">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white mb-2" style={{ letterSpacing: "-0.03em" }}>
                CyberPulse Security Platform
              </h1>
              <p className="text-[15px]" style={{ color: "rgba(255,255,255,0.6)" }}>
                Geautomatiseerde penetratietests op basis van AI-analyse
              </p>
              <div className="flex gap-3 mt-6">
                <Link
                  href="/scans/new"
                  className="inline-flex items-center gap-2 rounded-lg px-5 py-2.5 text-[14px] font-semibold transition-opacity hover:opacity-90"
                  style={{ background: "#0071e3", color: "#fff" }}
                >
                  <Plus className="h-4 w-4" />
                  Scan starten
                </Link>
                <Link
                  href="/reports"
                  className="inline-flex items-center gap-2 rounded-lg px-5 py-2.5 text-[14px] font-semibold transition-colors"
                  style={{
                    background: "rgba(255,255,255,0.10)",
                    color: "#fff",
                    border: "1px solid rgba(255,255,255,0.15)",
                  }}
                >
                  Rapporten bekijken
                </Link>
              </div>
            </div>
            <Shield className="h-16 w-16 opacity-10 text-white flex-shrink-0" />
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {stats.map((s) => {
          const Icon = s.icon;
          return (
            <Link key={s.label} href={s.href}>
              <div className="rounded-2xl border border-border bg-card p-5 shadow-apple hover:shadow-apple-md transition-shadow cursor-pointer">
                <div className="flex items-center justify-between mb-4">
                  <p className="text-[13px] font-medium text-muted-foreground">{s.label}</p>
                  <div
                    className="h-8 w-8 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ background: s.bg }}
                  >
                    <Icon className="h-4 w-4" style={{ color: s.color }} />
                  </div>
                </div>
                <p
                  className="text-[32px] font-bold leading-none"
                  style={{ color: s.color, letterSpacing: "-0.03em" }}
                >
                  {s.value}
                </p>
                {s.sub && (
                  <p className="text-[12px] text-primary mt-1.5 font-medium">{s.sub}</p>
                )}
              </div>
            </Link>
          );
        })}
      </div>

      {/* Quick actions */}
      <div>
        <h2 className="text-[17px] font-semibold mb-4">Snel starten</h2>
        <div className="grid grid-cols-3 gap-4">
          <Link href="/scans/new?type=quick" className="group">
            <div className="rounded-2xl border border-border bg-card p-5 shadow-apple hover:shadow-apple-md hover:border-primary/30 transition-all cursor-pointer">
              <div className="h-10 w-10 rounded-xl flex items-center justify-center mb-4" style={{ background: "rgba(0,113,227,0.08)" }}>
                <Zap className="h-5 w-5" style={{ color: "#0071e3" }} />
              </div>
              <p className="font-semibold text-[15px] mb-1">Snelle scan</p>
              <p className="text-[13px] text-muted-foreground">nmap + nuclei — klaar in 5–10 min</p>
            </div>
          </Link>
          <Link href="/scans/new?type=full" className="group">
            <div className="rounded-2xl border border-border bg-card p-5 shadow-apple hover:shadow-apple-md hover:border-primary/30 transition-all cursor-pointer">
              <div className="h-10 w-10 rounded-xl flex items-center justify-center mb-4" style={{ background: "rgba(191,90,242,0.08)" }}>
                <Shield className="h-5 w-5" style={{ color: "#bf5af2" }} />
              </div>
              <p className="font-semibold text-[15px] mb-1">Volledige assessment</p>
              <p className="text-[13px] text-muted-foreground">Alle 8 fases — uitgebreide pentest</p>
            </div>
          </Link>
          <Link href="/tools" className="group">
            <div className="rounded-2xl border border-border bg-card p-5 shadow-apple hover:shadow-apple-md hover:border-primary/30 transition-all cursor-pointer">
              <div className="h-10 w-10 rounded-xl flex items-center justify-center mb-4" style={{ background: "rgba(52,199,89,0.08)" }}>
                <Terminal className="h-5 w-5" style={{ color: "#34c759" }} />
              </div>
              <p className="font-semibold text-[15px] mb-1">Kali Tools status</p>
              <p className="text-[13px] text-muted-foreground">
                {toolsAvail !== null ? `${toolsAvail} tools beschikbaar` : "Tools controleren"}
              </p>
            </div>
          </Link>
        </div>
      </div>

      {/* Recent scans */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[17px] font-semibold">Recente activiteit</h2>
          <Link
            href="/scans"
            className="flex items-center gap-1 text-[13px] font-medium text-primary hover:underline"
          >
            Alles bekijken <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        {recentScans.length === 0 ? (
          <div className="rounded-2xl border border-border bg-card p-12 text-center shadow-apple">
            <Shield className="h-10 w-10 text-muted-foreground/20 mx-auto mb-3" />
            <p className="text-[15px] font-medium mb-1">Nog geen scans</p>
            <p className="text-[13px] text-muted-foreground mb-5">
              Start je eerste penetratietest om resultaten te zien.
            </p>
            <Link
              href="/scans/new"
              className="inline-flex items-center gap-2 rounded-lg px-5 py-2.5 text-[14px] font-semibold transition-opacity hover:opacity-90"
              style={{ background: "#0071e3", color: "#fff" }}
            >
              <Plus className="h-4 w-4" />
              Scan starten
            </Link>
          </div>
        ) : (
          <div className="rounded-2xl border border-border bg-card shadow-apple overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border" style={{ background: "#f5f5f7" }}>
                  <th className="text-left text-[11px] font-semibold text-muted-foreground uppercase tracking-wider px-5 py-3">
                    Type
                  </th>
                  <th className="text-left text-[11px] font-semibold text-muted-foreground uppercase tracking-wider px-5 py-3">
                    Status
                  </th>
                  <th className="text-left text-[11px] font-semibold text-muted-foreground uppercase tracking-wider px-5 py-3">
                    Bevindingen
                  </th>
                  <th className="text-right text-[11px] font-semibold text-muted-foreground uppercase tracking-wider px-5 py-3">
                    Datum
                  </th>
                </tr>
              </thead>
              <tbody>
                {recentScans.slice(0, 8).map((scan: any, i: number) => (
                  <tr
                    key={scan.id}
                    className={`hover:bg-secondary/60 transition-colors cursor-pointer ${
                      i < Math.min(recentScans.length, 8) - 1 ? "border-b border-border" : ""
                    }`}
                    onClick={() => (window.location.href = `/scans/${scan.id}`)}
                  >
                    <td className="px-5 py-3.5">
                      <span className="text-[14px] font-medium">
                        {scan.scan_type?.replace(/_/g, " ") ?? "scan"}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusDot status={scan.status} />
                    </td>
                    <td className="px-5 py-3.5">
                      <FindingsPills scan={scan} />
                    </td>
                    <td className="px-5 py-3.5 text-right text-[13px] text-muted-foreground">
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

function StatusDot({ status }: { status: string }) {
  const map: Record<string, { label: string; color: string; pulse?: boolean }> = {
    completed:  { label: "Voltooid",    color: "#34c759" },
    running:    { label: "Actief",      color: "#0071e3", pulse: true },
    pending:    { label: "Wachtend",    color: "#ff9500" },
    analyzing:  { label: "Analyseren", color: "#bf5af2", pulse: true },
    failed:     { label: "Mislukt",     color: "#ff3b30" },
    cancelled:  { label: "Geannuleerd", color: "#8e8e93" },
  };
  const s = map[status] ?? { label: status, color: "#8e8e93" };
  return (
    <span className="inline-flex items-center gap-1.5 text-[13px] font-medium" style={{ color: s.color }}>
      <span
        className={`h-2 w-2 rounded-full flex-shrink-0 ${s.pulse ? "animate-pulse" : ""}`}
        style={{ background: s.color }}
      />
      {s.label}
    </span>
  );
}

function FindingsPills({ scan }: { scan: any }) {
  const crit = scan.findings_critical ?? 0;
  const high = scan.findings_high ?? 0;
  const med  = scan.findings_medium ?? 0;
  if (crit + high + med === 0) return <span className="text-[13px] text-muted-foreground">—</span>;
  return (
    <div className="flex items-center gap-1.5">
      {crit > 0 && <span className="rounded-full px-2 py-0.5 text-[11px] font-semibold" style={{ background: "rgba(255,59,48,0.10)", color: "#ff3b30" }}>{crit}K</span>}
      {high > 0 && <span className="rounded-full px-2 py-0.5 text-[11px] font-semibold" style={{ background: "rgba(255,149,0,0.10)", color: "#ff9500" }}>{high}H</span>}
      {med  > 0 && <span className="rounded-full px-2 py-0.5 text-[11px] font-semibold" style={{ background: "rgba(255,204,0,0.12)", color: "#c69b00" }}>{med}M</span>}
    </div>
  );
}
