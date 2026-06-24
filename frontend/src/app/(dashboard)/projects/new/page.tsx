"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { FolderKanban, Plus, X, Loader2, ArrowRight } from "lucide-react";
import { projectsApi } from "@/lib/api";

export default function NewProjectPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [targets, setTargets] = useState<string[]>([""]);
  const [busy, setBusy] = useState(false);

  const validTargets = targets.map((t) => t.trim()).filter(Boolean);

  const setTarget = (i: number, v: string) =>
    setTargets((prev) => prev.map((t, idx) => (idx === i ? v : t)));
  const addTarget = () => setTargets((prev) => [...prev, ""]);
  const removeTarget = (i: number) => setTargets((prev) => prev.filter((_, idx) => idx !== i));

  const submit = async () => {
    if (busy || !name.trim() || validTargets.length === 0) return;
    setBusy(true);
    try {
      const { data } = await projectsApi.create({
        name: name.trim(),
        description: description.trim() || undefined,
        target_list: validTargets,
      });
      toast.success(`${data.scans_started} scans gestart`);
      router.push(`/projects/${data.project_id}`);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      toast.error(detail && typeof detail === "object" && detail.message ? detail.message : "Project aanmaken mislukt.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6">
      <h1 className="flex items-center gap-2 font-display text-2xl font-bold uppercase tracking-[0.06em] text-ink">
        <FolderKanban className="h-6 w-6 text-cyan" /> Nieuw project
      </h1>

      <div className="space-y-4 rounded-xl border border-grid bg-card p-6">
        <div>
          <label className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-muted">Naam</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Q3 Security Audit 2025"
            className="mt-2 w-full rounded-lg border border-grid bg-card2 px-4 py-2.5 font-mono text-[14px] text-ink outline-none focus:border-cyan/60"
          />
        </div>
        <div>
          <label className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-muted">Omschrijving (optioneel)</label>
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="mt-2 w-full rounded-lg border border-grid bg-card2 px-4 py-2.5 font-mono text-[14px] text-ink outline-none focus:border-cyan/60"
          />
        </div>

        <div>
          <label className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-muted">Targets</label>
          <div className="mt-2 space-y-2">
            {targets.map((t, i) => (
              <div key={i} className="flex items-center gap-2">
                <input
                  value={t}
                  onChange={(e) => setTarget(i, e.target.value)}
                  placeholder="bedrijf.nl  of  192.168.1.0/24"
                  className="flex-1 rounded-lg border border-grid bg-card2 px-4 py-2.5 font-mono text-[13px] text-ink outline-none focus:border-cyan/60"
                />
                {targets.length > 1 && (
                  <button type="button" onClick={() => removeTarget(i)} aria-label="Verwijder" className="rounded-lg border border-grid p-2.5 text-ink-muted hover:border-neon-red/50 hover:text-neon-red">
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
          <button type="button" onClick={addTarget} className="mt-2 inline-flex items-center gap-1.5 font-mono text-[12px] text-cyan hover:underline">
            <Plus className="h-3.5 w-3.5" /> Target toevoegen
          </button>
        </div>

        <div className="flex items-center justify-between border-t border-grid pt-4">
          <span className="font-mono text-[12px] text-ink-muted">
            {validTargets.length} targets · ~{validTargets.length} credits
          </span>
          <button
            type="button"
            onClick={submit}
            disabled={busy || !name.trim() || validTargets.length === 0}
            className="inline-flex items-center gap-2 rounded-lg bg-cyan px-5 py-2.5 font-display text-[12px] font-bold uppercase tracking-[0.1em] text-app shadow-glow-cyan disabled:opacity-50"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <>Start project <ArrowRight className="h-4 w-4" /></>}
          </button>
        </div>
      </div>
      <p className="font-mono text-[11px] text-ink-muted">
        Elk target wordt een aparte scan. CIDR/range telt per actief systeem. Combineer ze daarna in één rapport.
      </p>
    </div>
  );
}
