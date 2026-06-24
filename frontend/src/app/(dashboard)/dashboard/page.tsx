"use client";

import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/lib/api";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";
import {
  ScanLine, Target, AlertTriangle, BarChart3, Radar,
} from "lucide-react";
import FloatingEmptyState from "@/components/animations/FloatingEmptyState";

import { statusLabel } from "@/lib/labels";
import { StatCard } from "@/components/cyber/stat-card";
import { GlowCard } from "@/components/cyber/glow-card";
import { RiskBadge } from "@/components/cyber/risk-badge";
import { SkeletonRow, SkeletonCard } from "@/components/cyber/skeleton";
import { NetworkGlobePanel } from "@/components/cyber/network-globe-lazy";

// ── Helpers ─────────────────────────────────────────────────────────────────
function riskScore(scan: any): number {
  if (scan?.security_score != null) {
    return Math.max(0, Math.min(100, Math.round(100 - scan.security_score)));
  }
  const crit = scan?.findings_critical ?? scan?.critical_count ?? 0;
  const high = scan?.findings_high ?? scan?.high_count ?? 0;
  const med = scan?.findings_medium ?? scan?.medium_count ?? 0;
  return Math.min(100, crit * 25 + high * 12 + med * 5);
}

function riskSeverity(score: number): string {
  if (score >= 60) return "critical";
  if (score >= 30) return "high";
  if (score >= 10) return "medium";
  return "low";
}

function timeAgo(date: string): string {
  const diff = Date.now() - new Date(date).getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return "zojuist";
  if (min < 60) return `${min} min geleden`;
  const hrs = Math.floor(min / 60);
  if (hrs < 24) return `${hrs} uur geleden`;
  const days = Math.floor(hrs / 24);
  return `${days} dag${days > 1 ? "en" : ""} geleden`;
}

const STATUS_MAP: Record<string, { color: string; pulse?: boolean }> = {
  completed: { color: "#00FF88" },
  running: { color: "#00D4FF", pulse: true },
  pending: { color: "#FF8C00" },
  analyzing: { color: "#0A84FF", pulse: true },
  failed: { color: "#FF2D55" },
  cancelled: { color: "#4A6880" },
};

export default function DashboardPage() {
  const router = useRouter();

  const { data: scansData, isLoading: scansLoading } = useQuery({
    queryKey: ["scans"],
    queryFn: () => dashboardApi.listScans(1, 20),
  });
  const { data: targets, isLoading: targetsLoading } = useQuery({
    queryKey: ["targets"],
    queryFn: dashboardApi.listTargets,
  });

  // Backend aggregate stats (optional) — graceful fallback to local computation.
  const { data: apiStats } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: async (): Promise<any | null> => {
      try {
        const res = await fetch("/api/stats");
        if (!res.ok) return null;
        return await res.json();
      } catch {
        return null;
      }
    },
    retry: false,
  });

  const isLoading = scansLoading || targetsLoading;

  const recentScans: any[] = scansData?.items ?? [];
  const totalTargets = targets?.length ?? 0;

  const criticalFindings = recentScans.reduce(
    (sum: number, s: any) => sum + (s.findings_critical ?? s.critical_count ?? 0),
    0
  );

  const avgRisk = recentScans.length
    ? Math.round(
        recentScans.reduce((sum: number, s: any) => sum + riskScore(s), 0) /
          recentScans.length
      )
    : 0;

  // Risk trend — last 10 scans, chronological (local fallback)
  const localTrendData = [...recentScans]
    .reverse()
    .slice(-10)
    .map((s: any) => ({
      date: new Date(s.created_at).toLocaleDateString("nl-NL", {
        day: "2-digit",
        month: "short",
      }),
      risk: riskScore(s),
    }));

  // ── Resolve stats: prefer GET /api/stats, fall back to local computation ──
  const statTotalScans = apiStats?.total_scans ?? recentScans.length;
  const statActiveTargets = apiStats?.active_targets ?? totalTargets;
  const statCriticalOpen = apiStats?.critical_open ?? criticalFindings;
  const statAvgRisk = apiStats?.avg_risk_score ?? avgRisk;

  const avgRiskColor =
    statAvgRisk >= 60 ? "#FF2D55" : statAvgRisk >= 30 ? "#FF8C00" : "#00FF88";

  // API trend may be an array of numbers or {date,risk} objects; normalize.
  const apiTrend: any[] | null = Array.isArray(apiStats?.risk_trend)
    ? apiStats.risk_trend.map((p: any, i: number) =>
        typeof p === "number"
          ? { date: `#${i + 1}`, risk: p }
          : { date: p.date ?? `#${i + 1}`, risk: p.risk ?? p.value ?? 0 }
      )
    : null;

  const trendData = apiTrend && apiTrend.length > 0 ? apiTrend : localTrendData;

  // Globe targets
  const globeTargets = recentScans.slice(0, 12).map((s: any) => ({
    id: String(s.id ?? s.target_id ?? Math.random()),
    label: (s.target_value ?? s.scan_type ?? "target").toString().replace(/_/g, " "),
    risk: riskScore(s),
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <h1 className="font-display text-2xl font-bold text-ink">
          Overzicht
        </h1>
        <p className="font-mono text-[12px] text-ink-muted">
          Realtime overzicht van scans, doelen en risico&apos;s
        </p>
      </motion.div>

      {/* TOP ROW — stat cards */}
      {isLoading ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard
            label="Uitgevoerde scans"
            value={statTotalScans}
            icon={ScanLine}
            color="#00D4FF"
            index={0}
          />
          <StatCard
            label="Actieve doelen"
            value={statActiveTargets}
            icon={Target}
            color="#0A84FF"
            index={1}
          />
          <StatCard
            label="Kritieke bevindingen"
            value={statCriticalOpen}
            icon={AlertTriangle}
            color="#FF2D55"
            accent={statCriticalOpen > 0 ? "#FF2D55" : undefined}
            index={2}
          />
          <StatCard
            label="Gemiddelde risicoscore"
            value={statAvgRisk}
            icon={BarChart3}
            color={avgRiskColor}
            index={3}
          />
        </div>
      )}

      {/* MIDDLE ROW — recent scans (60%) + risk trend (40%) */}
      <div className="grid gap-4 lg:grid-cols-5">
        {/* LEFT — Recent scans */}
        <motion.div
          className="lg:col-span-3"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
        >
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-display text-[15px] font-semibold text-ink">
              Recente scans
            </h2>
            <button
              onClick={() => router.push("/scans")}
              className="font-mono text-[11px] uppercase tracking-wider text-cyan transition-opacity hover:opacity-70"
            >
              Alles bekijken
            </button>
          </div>

          {isLoading ? (
            <div className="space-y-2.5">
              {[0, 1, 2, 3].map((i) => (
                <SkeletonRow key={i} />
              ))}
            </div>
          ) : recentScans.length === 0 ? (
            <div className="rounded-lg border border-grid bg-card2">
              <FloatingEmptyState
                icon={Radar}
                title="Uw eerste scan wacht"
                description="Start uw eerste scan om resultaten te zien."
                ctaLabel="Start uw eerste scan"
                onCta={() => router.push("/scans/new")}
                videoSrc="/videos/animatie1.mp4"
                videoPoster="/videos/posters/poster1.jpg"
                cursor
              />
            </div>
          ) : (
            <div className="space-y-2.5">
              {recentScans.slice(0, 6).map((scan: any) => {
                const score = riskScore(scan);
                const st = STATUS_MAP[scan.status] ?? { color: "#4A6880" };
                const stLabel = statusLabel(scan.status);
                const crit = scan.findings_critical ?? scan.critical_count ?? 0;
                const high = scan.findings_high ?? scan.high_count ?? 0;
                const med = scan.findings_medium ?? scan.medium_count ?? 0;
                const low = scan.findings_low ?? scan.low_count ?? 0;
                return (
                  <GlowCard
                    key={scan.id}
                    glowColor="#00D4FF"
                    onClick={() => router.push(`/scans/${scan.id}`)}
                    className="px-4 py-3"
                  >
                    <div className="flex items-center gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="truncate font-mono text-[13px] font-medium text-ink">
                            {scan.target_value
                              ?? (scan.scan_type ?? "scan").toString().replace(/_/g, " ")}
                          </span>
                          <RiskBadge severity={riskSeverity(score)} />
                        </div>
                        <div className="mt-1 flex items-center gap-3">
                          <span className="font-mono text-[11px] text-ink-muted">
                            {timeAgo(scan.created_at)}
                          </span>
                          <span
                            className={`inline-flex items-center gap-1.5 font-mono text-[11px] font-medium ${
                              st.pulse ? "animate-pulse" : ""
                            }`}
                            style={{ color: st.color }}
                          >
                            <span
                              className="h-1.5 w-1.5 rounded-full"
                              style={{ background: st.color }}
                            />
                            {stLabel}
                          </span>
                        </div>
                      </div>

                      {/* Finding-count dots */}
                      <div className="flex items-center gap-1.5">
                        <FindingDot count={crit} color="#FF2D55" />
                        <FindingDot count={high} color="#FF8C00" />
                        <FindingDot count={med} color="#FFD60A" />
                        <FindingDot count={low} color="#0A84FF" />
                      </div>
                    </div>
                  </GlowCard>
                );
              })}
            </div>
          )}
        </motion.div>

        {/* RIGHT — Risk trend chart */}
        <motion.div
          className="lg:col-span-2"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
        >
          <h2 className="mb-3 font-display text-[15px] font-semibold text-ink">
            Risico-trend
          </h2>
          <div className="rounded-lg border border-grid bg-card2 p-4">
            {isLoading ? (
              <div className="h-[220px]">
                <SkeletonCard className="h-full" />
              </div>
            ) : trendData.length === 0 ? (
              <div className="flex h-[220px] items-center justify-center">
                <span className="font-mono text-[12px] text-ink-muted">
                  Geen gegevens beschikbaar
                </span>
              </div>
            ) : (
              <div className="h-[220px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trendData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                    <defs>
                      <linearGradient id="riskGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#00D4FF" stopOpacity={0.5} />
                        <stop offset="100%" stopColor="#00D4FF" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis
                      dataKey="date"
                      stroke="#4A6880"
                      tick={{ fontSize: 10, fill: "#4A6880" }}
                      tickLine={false}
                      axisLine={{ stroke: "#0A2035" }}
                    />
                    <YAxis
                      domain={[0, 100]}
                      stroke="#4A6880"
                      tick={{ fontSize: 10, fill: "#4A6880" }}
                      tickLine={false}
                      axisLine={{ stroke: "#0A2035" }}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "#080F18",
                        border: "1px solid #0A2035",
                        color: "#E8F4F8",
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                      labelStyle={{ color: "#4A6880" }}
                      cursor={{ stroke: "#0A2035" }}
                    />
                    <Area
                      type="monotone"
                      dataKey="risk"
                      stroke="#00D4FF"
                      strokeWidth={2}
                      fill="url(#riskGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </motion.div>
      </div>

      {/* BOTTOM — Network globe */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.3 }}
      >
        <NetworkGlobePanel targets={globeTargets} />
      </motion.div>
    </div>
  );
}

function FindingDot({ count, color }: { count: number; color: string }) {
  if (!count) return null;
  return (
    <span
      className="inline-flex h-5 min-w-[20px] items-center justify-center rounded-full px-1 font-mono text-[10px] font-semibold tabular-nums"
      style={{
        color,
        background: `${color}1A`,
        border: `1px solid ${color}55`,
      }}
    >
      {count}
    </span>
  );
}
