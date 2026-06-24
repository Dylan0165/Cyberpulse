"use client";

import { use } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Network, Loader2, CheckCircle2, XCircle, Clock, ExternalLink } from "lucide-react";
import { scansApi, type MultiScanJobStatus } from "@/lib/api";

const STATUS_META: Record<string, { label: string; cls: string; icon: typeof Clock }> = {
  completed: { label: "Voltooid", cls: "text-neon-green", icon: CheckCircle2 },
  failed: { label: "Mislukt", cls: "text-neon-red", icon: XCircle },
  cancelled: { label: "Geannuleerd", cls: "text-ink-muted", icon: XCircle },
  running: { label: "Bezig", cls: "text-cyan", icon: Loader2 },
  pending: { label: "In wachtrij", cls: "text-neon-orange", icon: Clock },
};

export default function MultiScanJobPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = use(params);

  const { data } = useQuery<MultiScanJobStatus>({
    queryKey: ["multi-job", jobId],
    queryFn: () => scansApi.multiJob(jobId).then((r) => r.data),
    // Poll every 10s until the whole job is done.
    refetchInterval: (q) => (q.state.data?.status === "completed" ? false : 10_000),
  });

  const progress =
    data && data.total_hosts > 0 ? Math.round((data.scanned_hosts / data.total_hosts) * 100) : 0;
  const done = data?.status === "completed";

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6">
      <div>
        <h1 className="flex items-center gap-2 font-display text-2xl font-bold uppercase tracking-[0.06em] text-ink">
          <Network className="h-6 w-6 text-cyan" /> Multi-scan
        </h1>
        <p className="mt-1 break-all font-mono text-[12px] text-ink-muted">{data?.input ?? jobId}</p>
      </div>

      {/* Progress */}
      <div className="rounded-xl border border-grid bg-card p-6">
        <div className="flex items-center justify-between font-mono text-[13px]">
          <span className="text-ink">
            {data?.scanned_hosts ?? 0} van {data?.total_hosts ?? 0} systemen gescand
          </span>
          <span className="text-cyan">{data?.credits_used ?? 0} credits gebruikt</span>
        </div>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-card2">
          <div
            className={`h-full rounded-full transition-all duration-500 ${done ? "bg-neon-green" : "bg-cyan"}`}
            style={{ width: `${progress}%` }}
          />
        </div>
        <p className="mt-2 font-mono text-[11px] text-ink-muted">
          {done ? "Alle scans voltooid." : "Pagina ververst automatisch elke 10 seconden."}
        </p>
      </div>

      {/* Per-host list */}
      <div className="overflow-hidden rounded-xl border border-grid">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-grid bg-card2">
              {["Host", "Status", ""].map((h) => (
                <th key={h} className="px-4 py-3 font-mono text-[10px] uppercase tracking-wider text-ink-muted">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(data?.scans ?? []).map((s) => {
              const meta = STATUS_META[s.status] ?? STATUS_META.pending;
              const Icon = meta.icon;
              return (
                <tr key={s.scan_id} className="border-b border-grid/60">
                  <td className="px-4 py-3 font-mono text-[12px] text-ink">{s.host ?? "—"}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1.5 font-mono text-[12px] ${meta.cls}`}>
                      <Icon className={`h-3.5 w-3.5 ${s.status === "running" ? "animate-spin" : ""}`} />
                      {meta.label}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {s.status === "completed" && (
                      <Link
                        href={`/scans/${s.scan_id}`}
                        className="inline-flex items-center gap-1 font-mono text-[12px] text-cyan hover:underline"
                      >
                        Rapport <ExternalLink className="h-3 w-3" />
                      </Link>
                    )}
                  </td>
                </tr>
              );
            })}
            {(data?.scans ?? []).length === 0 && (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-center font-mono text-[12px] text-ink-muted">
                  Scans worden voorbereid…
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
