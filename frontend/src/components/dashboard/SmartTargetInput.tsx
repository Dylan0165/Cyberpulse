"use client";

import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Zap, Search, Network, ListOrdered, Globe, Loader2, ArrowRight } from "lucide-react";
import { scansApi, type MultiScanPreview } from "@/lib/api";

type Kind = "single" | "cidr" | "range" | "domain_with_subs";

/** Client-side mirror of the backend TargetParser for instant badges. */
function detect(value: string): Kind {
  const v = value.trim();
  if (!v) return "single";
  if (v.startsWith("*.") || v.endsWith("/*")) return "domain_with_subs";
  if (/^\d{1,3}(\.\d{1,3}){3}\/\d{1,2}$/.test(v)) return "cidr";
  if (/^\d{1,3}(\.\d{1,3}){2}\.\d{1,3}-\d{1,3}$/.test(v)) return "range";
  return "single";
}

const BADGE: Record<Kind, { label: string; icon: typeof Network }> = {
  single: { label: "Enkel systeem — 1 credit", icon: Zap },
  cidr: { label: "Subnet (CIDR)", icon: Network },
  range: { label: "IP-range", icon: ListOrdered },
  domain_with_subs: { label: "Subdomain discovery", icon: Globe },
};

/**
 * Smart target field: detects single host vs CIDR/range/subdomain, and for
 * multi-target inputs loads a discovery preview before starting the scans.
 * `onStarted(jobId)` fires after a confirmed multi-scan launch.
 */
export function SmartTargetInput({ onStarted }: { onStarted: (jobId: string) => void }) {
  const [value, setValue] = useState("");
  const [preview, setPreview] = useState<MultiScanPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [starting, setStarting] = useState(false);

  const kind = useMemo(() => detect(value), [value]);
  const isMulti = kind !== "single";
  const badge = BADGE[kind];

  const loadPreview = async () => {
    if (!value.trim() || loading) return;
    setLoading(true);
    setPreview(null);
    try {
      const { data } = await scansApi.previewMulti(value.trim());
      setPreview(data);
    } catch {
      toast.error("Preview kon niet worden geladen.");
    } finally {
      setLoading(false);
    }
  };

  const start = async () => {
    if (starting) return;
    setStarting(true);
    try {
      const { data } = await scansApi.startMulti(value.trim());
      toast.success(data.message);
      onStarted(data.job_id);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      toast.error(
        detail && typeof detail === "object" && detail.message
          ? detail.message
          : "Scans konden niet worden gestart."
      );
    } finally {
      setStarting(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-muted">
          IP, subnet, range of domein
        </label>
        <input
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setPreview(null);
          }}
          placeholder="192.168.1.0/24  ·  10.0.0.50-100  ·  *.bedrijf.nl"
          className="mt-2 w-full rounded-lg border border-grid bg-card2 px-4 py-3 font-mono text-[14px] text-ink outline-none transition-colors focus:border-cyan/60"
        />
        <div className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-grid bg-card2 px-3 py-1 font-mono text-[11px] text-cyan">
          <badge.icon className="h-3.5 w-3.5" /> {badge.label}
        </div>
      </div>

      {isMulti && !preview && (
        <button
          type="button"
          onClick={loadPreview}
          disabled={loading || !value.trim()}
          className="inline-flex items-center gap-2 rounded-lg border border-cyan/40 bg-cyan/10 px-4 py-2.5 font-mono text-[12px] font-semibold uppercase tracking-[0.1em] text-cyan transition-all hover:brightness-125 disabled:opacity-50"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
          {loading ? "Preview laden…" : "Preview laden"}
        </button>
      )}

      {preview && (
        <div className="rounded-xl border border-grid bg-card2 p-5">
          <p className="flex items-center gap-2 font-display text-[14px] font-bold text-ink">
            <Search className="h-4 w-4 text-cyan" /> Preview: {preview.input}
          </p>
          <p className="mt-2 font-mono text-[12px] text-ink-muted">
            Gevonden: <span className="text-ink">{preview.estimated_hosts}</span>{" "}
            {preview.type === "domain_with_subs" ? "subdomeinen" : "actieve systemen"}
          </p>
          {preview.alive_hosts.length > 0 && (
            <p className="mt-1 line-clamp-2 break-all font-mono text-[11px] text-ink-muted">
              {preview.alive_hosts.slice(0, 12).join(", ")}
              {preview.alive_hosts.length > 12 ? "…" : ""}
            </p>
          )}
          <div className="mt-3 flex items-center gap-4 font-mono text-[12px]">
            <span className="text-cyan">Credits nodig: {preview.credits_required}</span>
            <span className={preview.can_afford ? "text-neon-green" : "text-neon-red"}>
              Uw saldo: {preview.credits_available} {preview.can_afford ? "✓" : "✗"}
            </span>
          </div>

          <div className="mt-4 flex gap-2">
            <button
              type="button"
              onClick={() => setPreview(null)}
              className="flex-1 rounded-lg border border-grid bg-app px-4 py-2.5 font-mono text-[12px] uppercase tracking-[0.1em] text-ink-muted transition-colors hover:text-ink"
            >
              Annuleren
            </button>
            <button
              type="button"
              onClick={start}
              disabled={!preview.can_afford || starting}
              className="flex flex-[2] items-center justify-center gap-2 rounded-lg bg-cyan px-4 py-2.5 font-display text-[12px] font-bold uppercase tracking-[0.1em] text-app shadow-glow-cyan transition-transform hover:scale-[1.01] active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {starting ? <Loader2 className="h-4 w-4 animate-spin" /> : <>Start {preview.estimated_hosts} scans <ArrowRight className="h-4 w-4" /></>}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
