"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Server, Plus, Trash2, Radar, Copy, Check, X, Loader2, Circle,
} from "lucide-react";
import { agentsApi, type ScanixAgentItem } from "@/lib/api";

function timeAgo(iso: string | null): string {
  if (!iso) return "nooit";
  const secs = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  if (secs < 60) return `${secs}s geleden`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m geleden`;
  if (secs < 86400) return `${Math.floor(secs / 3600)}u geleden`;
  return `${Math.floor(secs / 86400)}d geleden`;
}

export default function AgentsPage() {
  const qc = useQueryClient();
  const router = useRouter();
  const [showAdd, setShowAdd] = useState(false);
  const [name, setName] = useState("");
  const [created, setCreated] = useState<{ install_command: string } | null>(null);
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);

  const { data: agents } = useQuery<ScanixAgentItem[]>({
    queryKey: ["agents"],
    queryFn: () => agentsApi.list().then((r) => r.data),
    refetchInterval: 30_000,
    retry: false,
  });

  const create = async () => {
    if (busy || !name.trim()) return;
    setBusy(true);
    try {
      const { data } = await agentsApi.register(name.trim());
      setCreated({ install_command: data.install_command });
      qc.invalidateQueries({ queryKey: ["agents"] });
    } catch {
      toast.error("Agent aanmaken mislukt.");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: string) => {
    try {
      await agentsApi.remove(id);
      qc.invalidateQueries({ queryKey: ["agents"] });
      toast.success("Agent verwijderd");
    } catch {
      toast.error("Verwijderen mislukt.");
    }
  };

  const startScan = async (id: string) => {
    const target = window.prompt("Welk lokaal IP of systeem wilt u scannen via deze agent?");
    if (!target) return;
    try {
      const { data } = await agentsApi.startScan(id, target.trim());
      toast.success(data.message);
      router.push(`/scans/${data.scan_id}`);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      toast.error(detail && typeof detail === "object" && detail.message ? detail.message : "Scan starten mislukt.");
    }
  };

  const closeModal = () => {
    setShowAdd(false);
    setName("");
    setCreated(null);
    setCopied(false);
  };

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 font-display text-2xl font-bold uppercase tracking-[0.06em] text-ink">
            <Server className="h-6 w-6 text-cyan" /> Scanix Agents
          </h1>
          <p className="mt-1 font-mono text-[12px] text-ink-muted">
            Scan systemen achter uw router — zonder port forwarding of VPN.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowAdd(true)}
          className="inline-flex flex-shrink-0 items-center gap-2 rounded-lg bg-cyan px-4 py-2.5 font-display text-[12px] font-bold uppercase tracking-[0.1em] text-app shadow-glow-cyan transition-transform hover:scale-[1.02] active:scale-[0.98]"
        >
          <Plus className="h-4 w-4" /> Nieuwe agent
        </button>
      </div>

      <div className="space-y-3">
        {(agents ?? []).length === 0 ? (
          <div className="rounded-xl border border-dashed border-grid bg-card2 p-10 text-center font-mono text-[12px] text-ink-muted">
            Nog geen agents. Maak er een aan en installeer hem op uw server.
          </div>
        ) : (
          (agents ?? []).map((a) => {
            const online = a.status === "online";
            return (
              <div key={a.agent_id} className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-grid bg-card p-5">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-display text-[15px] font-bold text-ink">{a.name}</span>
                    <span className={`inline-flex items-center gap-1 font-mono text-[11px] ${online ? "text-neon-green" : "text-neon-red"}`}>
                      <Circle className="h-2 w-2" fill="currentColor" /> {online ? "Online" : "Offline"}
                    </span>
                  </div>
                  <p className="mt-1 font-mono text-[11px] text-ink-muted">
                    {[a.hostname, a.local_ip, a.os].filter(Boolean).join(" · ") || "wacht op eerste heartbeat"}
                  </p>
                  <p className="mt-0.5 font-mono text-[11px] text-ink-muted">Laatste heartbeat: {timeAgo(a.last_seen)}</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => startScan(a.agent_id)}
                    disabled={!online}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-grid bg-app px-3 py-2 font-mono text-[12px] text-ink transition-colors hover:border-cyan/50 hover:text-cyan disabled:opacity-40"
                  >
                    <Radar className="h-4 w-4" /> Scan starten
                  </button>
                  <button
                    type="button"
                    onClick={() => remove(a.agent_id)}
                    aria-label="Verwijderen"
                    className="inline-flex items-center justify-center rounded-lg border border-grid bg-app p-2 text-ink-muted transition-colors hover:border-neon-red/50 hover:text-neon-red"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Add / install modal */}
      {showAdd && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm" onClick={closeModal}>
          <div className="relative w-full max-w-lg rounded-xl border border-grid bg-card2 p-6" onClick={(e) => e.stopPropagation()}>
            <button type="button" onClick={closeModal} aria-label="Sluiten" className="absolute right-4 top-4 text-ink-muted hover:text-ink">
              <X className="h-4 w-4" />
            </button>

            {!created ? (
              <>
                <h2 className="font-display text-lg font-bold text-ink">Agent toevoegen</h2>
                <label className="mt-4 block font-mono text-[11px] uppercase tracking-[0.14em] text-ink-muted">Naam</label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Kantoor Amsterdam"
                  className="mt-2 w-full rounded-lg border border-grid bg-app px-4 py-2.5 font-mono text-[14px] text-ink outline-none focus:border-cyan/60"
                />
                <button
                  type="button"
                  onClick={create}
                  disabled={busy || !name.trim()}
                  className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-cyan px-4 py-2.5 font-display text-[12px] font-bold uppercase tracking-[0.1em] text-app disabled:opacity-50"
                >
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Aanmaken"}
                </button>
              </>
            ) : (
              <>
                <h2 className="flex items-center gap-2 font-display text-lg font-bold text-ink">
                  <Check className="h-5 w-5 text-neon-green" /> Agent aangemaakt
                </h2>
                <p className="mt-3 font-mono text-[12px] text-ink-muted">Voer dit commando uit op uw server:</p>
                <div className="mt-2 flex items-start gap-2 overflow-x-auto rounded-lg border border-grid bg-app p-3">
                  <code className="flex-1 whitespace-pre-wrap break-all font-mono text-[12px] text-cyan">{created.install_command}</code>
                  <button
                    type="button"
                    onClick={async () => {
                      try {
                        await navigator.clipboard.writeText(created.install_command);
                        setCopied(true);
                        window.setTimeout(() => setCopied(false), 2000);
                      } catch { /* ignore */ }
                    }}
                    aria-label="Kopieer"
                    className="flex-shrink-0 rounded-lg border border-grid px-2.5 py-1.5 text-ink-muted hover:border-cyan/40 hover:text-cyan"
                  >
                    {copied ? <Check className="h-4 w-4 text-neon-green" /> : <Copy className="h-4 w-4" />}
                  </button>
                </div>
                <p className="mt-3 font-mono text-[11px] text-ink-muted">
                  De agent verschijnt automatisch als &quot;Online&quot; zodra hij geïnstalleerd is.
                </p>
                <button
                  type="button"
                  onClick={closeModal}
                  className="mt-5 inline-flex w-full items-center justify-center rounded-lg border border-grid bg-app px-4 py-2.5 font-mono text-[12px] uppercase tracking-[0.1em] text-ink-muted hover:text-ink"
                >
                  Sluiten
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
