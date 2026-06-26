"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { targetsApi, scansListApi } from "@/lib/api";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowLeft, Shield, Trash2, Globe, CheckCircle2, XCircle, Loader2,
} from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import { GlowCard } from "@/components/cyber/glow-card";
import { TargetTrendChart } from "@/components/targets/TargetTrendChart";

const TYPE_LABEL: Record<string, string> = {
  url: "Web / URL",
  domain: "Domein",
  ip: "IP-adres",
  ip_range: "IP-range",
  web_application: "Web App",
  network: "Netwerk",
  api: "API",
};

const STATUS_LABEL: Record<string, string> = {
  completed: "Voltooid",
  running: "Bezig",
  pending: "In wachtrij",
  failed: "Mislukt",
  cancelled: "Geannuleerd",
};

function riskScore(scan: any): number {
  if (scan?.security_score != null) {
    return Math.max(0, Math.min(100, Math.round(100 - scan.security_score)));
  }
  const crit = scan?.findings_critical ?? scan?.critical_count ?? 0;
  const high = scan?.findings_high ?? scan?.high_count ?? 0;
  const med = scan?.findings_medium ?? scan?.medium_count ?? 0;
  return Math.min(100, crit * 25 + high * 12 + med * 5);
}

function riskColor(score: number): string {
  if (score >= 61) return "#FF2D55";
  if (score >= 31) return "#FF8C00";
  return "#00FF88";
}

export default function TargetDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const targetId = params.id as string;

  const { data: target, isLoading } = useQuery({
    queryKey: ["target", targetId],
    queryFn: () => targetsApi.get(targetId).then((r) => r.data),
  });

  // Scan history for this target (used for risk trend + recente scans).
  const { data: allScans } = useQuery({
    queryKey: ["scans", "for-target", targetId],
    queryFn: () => scansListApi.list(50),
  });

  const deleteMutation = useMutation({
    mutationFn: () => targetsApi.delete(targetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["targets"] });
      toast.success("Doel verwijderd");
      router.push("/targets");
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail ?? "Verwijderen mislukt");
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20 text-ink-muted">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Laden...
      </div>
    );
  }

  if (!target) {
    return (
      <div className="rounded-lg border border-grid bg-card2 p-16 text-center text-ink-muted">
        Doel niet gevonden
      </div>
    );
  }

  const display = target.hostname ?? target.value ?? target.name ?? "—";
  const typeLabel = TYPE_LABEL[target.target_type] ?? (target.target_type ?? "—");

  // Scans belonging to this target. The list endpoint exposes target_id; some
  // payloads use target/value, so we match loosely.
  const scans: any[] = Array.isArray(allScans)
    ? allScans.filter((s: any) => {
        const t = String(s.target_id ?? s.target ?? s.value ?? "");
        return t === String(targetId) || t === String(target.value) || t === String(target.hostname);
      })
    : [];

  // Chart data: oldest → newest.
  const chartData = [...scans]
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
    .map((s) => ({
      date: new Date(s.created_at).toLocaleDateString("nl-NL", { day: "numeric", month: "short" }),
      risk: riskScore(s),
    }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <Link
            href="/targets"
            className="mb-2 inline-flex items-center gap-1.5 text-[13px] text-ink-muted transition-colors hover:text-cyan"
          >
            <ArrowLeft className="h-4 w-4" /> Terug naar doelen
          </Link>
          <h1 className="font-display text-[26px] font-bold text-ink" style={{ letterSpacing: "-0.03em" }}>
            {target.name ?? display}
          </h1>
          <p className="mt-1 break-all font-mono text-[14px] text-cyan">{display}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Link
            href={`/scans/new?target=${target.id}`}
            className="inline-flex items-center gap-2 rounded-lg bg-cyan px-5 py-2.5 text-[14px] font-semibold text-black transition-shadow hover:shadow-glow-cyan"
          >
            <Shield className="h-4 w-4" /> Scan nu
          </Link>
          <button
            onClick={() => {
              if (confirm("Dit doel verwijderen? Dit kan niet ongedaan worden gemaakt.")) {
                deleteMutation.mutate();
              }
            }}
            disabled={deleteMutation.isPending}
            className="inline-flex items-center gap-2 rounded-lg border border-neon-red/40 px-4 py-2.5 text-[14px] font-medium text-neon-red transition-shadow hover:shadow-glow-red disabled:opacity-50"
          >
            <Trash2 className="h-4 w-4" /> Verwijderen
          </button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Risicoverloop */}
        <GlowCard glowColor="#00D4FF" className="p-6 lg:col-span-2" hoverLift={false}>
          <h2 className="font-display text-[17px] font-semibold text-ink mb-1">Risicoverloop</h2>
          <p className="mb-5 text-[13px] text-ink-muted">Risicoscore per scan (0–100)</p>
          {chartData.length === 0 ? (
            <div className="flex h-[260px] items-center justify-center text-center text-[14px] text-ink-muted">
              Voer scans uit om het risicoverloop te zien
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={chartData} margin={{ top: 10, right: 12, left: -12, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#0A2035" />
                <XAxis
                  dataKey="date"
                  stroke="#4A6880"
                  tick={{ fill: "#4A6880", fontSize: 11 }}
                  tickLine={false}
                  axisLine={{ stroke: "#0A2035" }}
                />
                <YAxis
                  domain={[0, 100]}
                  stroke="#4A6880"
                  tick={{ fill: "#4A6880", fontSize: 11 }}
                  tickLine={false}
                  axisLine={{ stroke: "#0A2035" }}
                />
                <Tooltip
                  contentStyle={{
                    background: "#080F18",
                    border: "1px solid #0A2035",
                    borderRadius: 8,
                    color: "#E8F4F8",
                    fontSize: 12,
                  }}
                  labelStyle={{ color: "#4A6880" }}
                  formatter={(v: any) => [v, "Risicoscore"]}
                />
                <Line
                  type="monotone"
                  dataKey="risk"
                  stroke="#00D4FF"
                  strokeWidth={2}
                  dot={{ r: 3, fill: "#00D4FF" }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </GlowCard>

        {/* Doelinformatie */}
        <GlowCard glowColor="#00D4FF" className="p-6" hoverLift={false}>
          <h2 className="font-display text-[17px] font-semibold text-ink mb-4">Doelinformatie</h2>
          <dl className="space-y-3.5 text-[14px]">
            <div className="flex items-start justify-between gap-3">
              <dt className="text-ink-muted">Naam</dt>
              <dd className="text-right text-ink">{target.name ?? "—"}</dd>
            </div>
            <div className="flex items-start justify-between gap-3">
              <dt className="text-ink-muted">IP / domein</dt>
              <dd className="break-all text-right font-mono text-ink">{display}</dd>
            </div>
            <div className="flex items-start justify-between gap-3">
              <dt className="text-ink-muted">Type</dt>
              <dd className="text-right">
                <span className="rounded-md border border-cyan/30 bg-cyan/10 px-2 py-0.5 text-[12px] text-cyan">
                  {typeLabel}
                </span>
              </dd>
            </div>
            <div className="flex items-start justify-between gap-3">
              <dt className="text-ink-muted">Geverifieerd</dt>
              <dd className="text-right">
                {target.is_verified ? (
                  <span className="inline-flex items-center gap-1 text-neon-green">
                    <CheckCircle2 className="h-4 w-4" /> Ja
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-ink-muted">
                    <XCircle className="h-4 w-4" /> Nee
                  </span>
                )}
              </dd>
            </div>
            <div className="flex items-start justify-between gap-3">
              <dt className="text-ink-muted">Aangemaakt</dt>
              <dd className="text-right text-ink">
                {target.created_at
                  ? new Date(target.created_at).toLocaleDateString("nl-NL", {
                      day: "numeric", month: "long", year: "numeric",
                    })
                  : "—"}
              </dd>
            </div>
          </dl>
        </GlowCard>
      </div>

      {/* Risico-trend over scans */}
      <TargetTrendChart targetId={targetId} />

      {/* Recente scans */}
      <GlowCard glowColor="#00D4FF" className="p-6" hoverLift={false}>
        <h2 className="font-display text-[17px] font-semibold text-ink mb-4">Recente scans</h2>
        {scans.length === 0 ? (
          <p className="py-8 text-center text-[14px] text-ink-muted">
            Nog geen scans voor dit doel uitgevoerd
          </p>
        ) : (
          <div className="space-y-2">
            {[...scans]
              .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
              .map((scan: any, idx: number) => {
                const score = riskScore(scan);
                const color = riskColor(score);
                return (
                  <motion.div
                    key={scan.id ?? idx}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.25, delay: idx * 0.04 }}
                  >
                    <Link
                      href={`/scans/${scan.id}`}
                      className="flex items-center justify-between gap-3 rounded-lg border border-grid bg-app px-4 py-3 transition-colors hover:border-cyan/40"
                    >
                      <div className="flex min-w-0 items-center gap-3">
                        <Globe className="h-4 w-4 shrink-0 text-ink-muted" />
                        <div className="min-w-0">
                          <p className="text-[13px] text-ink">
                            {STATUS_LABEL[scan.status] ?? scan.status ?? "Scan"}
                          </p>
                          <p className="font-mono text-[11px] text-ink-muted">
                            {scan.created_at
                              ? new Date(scan.created_at).toLocaleString("nl-NL")
                              : "—"}
                          </p>
                        </div>
                      </div>
                      <span
                        className="shrink-0 rounded-md px-2.5 py-1 font-mono text-[13px] font-bold"
                        style={{ color, background: `${color}1a`, border: `1px solid ${color}40` }}
                      >
                        {score}
                      </span>
                    </Link>
                  </motion.div>
                );
              })}
          </div>
        )}
      </GlowCard>
    </div>
  );
}
