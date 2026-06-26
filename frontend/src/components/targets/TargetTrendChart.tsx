"use client";

import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { TrendingUp } from "lucide-react";
import { GlowCard } from "@/components/cyber/glow-card";
import { analyticsApi } from "@/lib/api";

/** Risk-score trend over a target's scans (Blok 8B). */
export function TargetTrendChart({ targetId }: { targetId: string }) {
  const router = useRouter();
  const { data } = useQuery({
    queryKey: ["target-trend", targetId],
    queryFn: () => analyticsApi.trend(targetId).then((r) => r.data),
    retry: false,
  });

  const points = (data?.points ?? []) as any[];

  return (
    <GlowCard glowColor="#00D4FF" className="p-6" hoverLift={false}>
      <div className="mb-4 flex items-center gap-2">
        <TrendingUp className="h-4 w-4 text-cyan" />
        <h2 className="text-[13px] font-semibold uppercase tracking-[0.1em] text-ink">Risico-trend</h2>
      </div>
      {points.length < 2 ? (
        <p className="py-8 text-center font-mono text-[12px] text-ink-muted">
          Voer minimaal 2 scans uit voor een trend.
        </p>
      ) : (
        <>
          <div className="h-[220px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={points}
                onClick={(e: any) => {
                  const sid = e?.activePayload?.[0]?.payload?.scan_id;
                  if (sid) router.push(`/scans/${sid}`);
                }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#0A2035" />
                <XAxis dataKey="date" stroke="#4A6880" fontSize={11} />
                <YAxis domain={[0, 100]} stroke="#4A6880" fontSize={11} />
                <Tooltip
                  contentStyle={{ background: "#0A1520", border: "1px solid #0A2035", borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: "#9FB3C8" }}
                />
                <Line type="monotone" dataKey="risk_score" stroke="#00D4FF" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} name="Risicoscore" />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {points.map((p) => (
              <button
                key={p.scan_id}
                onClick={() => router.push(`/scans/${p.scan_id}`)}
                className="rounded-md border border-grid bg-app px-2 py-1 font-mono text-[10px] text-ink-muted transition-colors hover:border-cyan/50 hover:text-cyan"
                title={`${p.date} · score ${p.risk_score}`}
              >
                {p.date}: <span className="text-neon-red">{p.critical}C</span> <span className="text-neon-orange">{p.high}H</span> <span className="text-ink-muted">{p.medium}M</span>
              </button>
            ))}
          </div>
        </>
      )}
    </GlowCard>
  );
}

export default TargetTrendChart;
