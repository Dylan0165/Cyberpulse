"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { FolderKanban, Plus, FileDown } from "lucide-react";
import api, { projectsApi, type ScanProjectItem } from "@/lib/api";

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

export default function ProjectsPage() {
  const { data: projects } = useQuery<ScanProjectItem[]>({
    queryKey: ["projects"],
    queryFn: () => projectsApi.list().then((r) => r.data),
    refetchInterval: 15_000,
    retry: false,
  });

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 font-display text-2xl font-bold uppercase tracking-[0.06em] text-ink">
            <FolderKanban className="h-6 w-6 text-cyan" /> Projecten
          </h1>
          <p className="mt-1 font-mono text-[12px] text-ink-muted">
            Bundel meerdere systemen in één project met een gecombineerd rapport.
          </p>
        </div>
        <Link
          href="/projects/new"
          className="inline-flex flex-shrink-0 items-center gap-2 rounded-lg bg-cyan px-4 py-2.5 font-display text-[12px] font-bold uppercase tracking-[0.1em] text-app shadow-glow-cyan transition-transform hover:scale-[1.02] active:scale-[0.98]"
        >
          <Plus className="h-4 w-4" /> Nieuw project
        </Link>
      </div>

      <div className="space-y-3">
        {(projects ?? []).length === 0 ? (
          <div className="rounded-xl border border-dashed border-grid bg-card2 p-10 text-center font-mono text-[12px] text-ink-muted">
            Nog geen projecten.
          </div>
        ) : (
          (projects ?? []).map((p) => {
            const pct = p.total_scans > 0 ? Math.round((p.completed_scans / p.total_scans) * 100) : 0;
            const done = p.status === "completed";
            return (
              <div key={p.id} className="rounded-xl border border-grid bg-card p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <Link href={`/projects/${p.id}`} className="font-display text-[15px] font-bold text-ink hover:text-cyan">
                      {p.name}
                    </Link>
                    {p.description && <p className="mt-0.5 font-mono text-[11px] text-ink-muted">{p.description}</p>}
                  </div>
                  <button
                    type="button"
                    onClick={() => downloadReport(p.id, p.name)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-grid bg-app px-3 py-2 font-mono text-[12px] text-ink transition-colors hover:border-cyan/50 hover:text-cyan"
                  >
                    <FileDown className="h-4 w-4" /> Gecombineerd rapport
                  </button>
                </div>
                <div className="mt-3 flex items-center gap-3">
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-card2">
                    <div className={`h-full rounded-full ${done ? "bg-neon-green" : "bg-cyan"}`} style={{ width: `${pct}%` }} />
                  </div>
                  <span className="font-mono text-[11px] text-ink-muted">
                    {p.completed_scans} van {p.total_scans} scans
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
