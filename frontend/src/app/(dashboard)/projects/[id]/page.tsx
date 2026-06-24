"use client";

import { use } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { FolderKanban, FileDown, ExternalLink } from "lucide-react";
import api, { projectsApi } from "@/lib/api";

type ProjectDetail = {
  id: string;
  name: string;
  description: string | null;
  status: string;
  total_scans: number;
  completed_scans: number;
  scans: { scan_id: string; host: string | null; status: string }[];
};

function downloadReport(id: string, name: string) {
  api
    .get(projectsApi.reportUrl(id), { responseType: "blob" })
    .then((r) => {
      const url = URL.createObjectURL(r.data as Blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `project_${name}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    })
    .catch(() => {});
}

export default function ProjectDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);

  const { data } = useQuery<ProjectDetail>({
    queryKey: ["project", id],
    queryFn: () => projectsApi.get(id).then((r) => r.data),
    refetchInterval: (q) => (q.state.data?.status === "completed" ? false : 12_000),
  });

  const pct = data && data.total_scans > 0 ? Math.round((data.completed_scans / data.total_scans) * 100) : 0;

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 font-display text-2xl font-bold uppercase tracking-[0.06em] text-ink">
            <FolderKanban className="h-6 w-6 text-cyan" /> {data?.name ?? "Project"}
          </h1>
          {data?.description && <p className="mt-1 font-mono text-[12px] text-ink-muted">{data.description}</p>}
        </div>
        <button
          type="button"
          onClick={() => data && downloadReport(data.id, data.name)}
          className="inline-flex items-center gap-2 rounded-lg border border-grid bg-app px-4 py-2.5 font-mono text-[12px] text-ink transition-colors hover:border-cyan/50 hover:text-cyan"
        >
          <FileDown className="h-4 w-4" /> Gecombineerd rapport
        </button>
      </div>

      <div className="rounded-xl border border-grid bg-card p-5">
        <div className="flex items-center justify-between font-mono text-[12px]">
          <span className="text-ink">{data?.completed_scans ?? 0} van {data?.total_scans ?? 0} scans voltooid</span>
          <span className="text-cyan">{data?.status}</span>
        </div>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-card2">
          <div className="h-full rounded-full bg-cyan transition-all" style={{ width: `${pct}%` }} />
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-grid">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-grid bg-card2">
              {["Host", "Status", ""].map((h) => (
                <th key={h} className="px-4 py-3 font-mono text-[10px] uppercase tracking-wider text-ink-muted">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(data?.scans ?? []).map((s) => (
              <tr key={s.scan_id} className="border-b border-grid/60">
                <td className="px-4 py-3 font-mono text-[12px] text-ink">{s.host ?? "—"}</td>
                <td className="px-4 py-3 font-mono text-[12px] text-ink-muted">{s.status}</td>
                <td className="px-4 py-3 text-right">
                  {s.status === "completed" && (
                    <Link href={`/scans/${s.scan_id}`} className="inline-flex items-center gap-1 font-mono text-[12px] text-cyan hover:underline">
                      Rapport <ExternalLink className="h-3 w-3" />
                    </Link>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
