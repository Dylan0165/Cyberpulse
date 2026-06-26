"use client";

import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { ChevronDown, Circle, Check, MinusCircle, AlertTriangle } from "lucide-react";
import { findingsApi } from "@/lib/api";

export const STATUS_META: Record<string, { label: string; cls: string; icon: typeof Circle }> = {
  open: { label: "Open", cls: "border-neon-red/50 bg-neon-red/10 text-neon-red", icon: Circle },
  resolved: { label: "Opgelost", cls: "border-neon-green/50 bg-neon-green/10 text-neon-green", icon: Check },
  false_positive: { label: "False positive", cls: "border-grid bg-card2 text-ink-muted", icon: MinusCircle },
  accepted_risk: { label: "Geaccepteerd risico", cls: "border-neon-orange/50 bg-neon-orange/10 text-neon-orange", icon: AlertTriangle },
};

const OPTIONS = ["open", "resolved", "false_positive", "accepted_risk"] as const;

export function FindingStatusBadge({
  findingId,
  currentStatus,
  currentNote,
  onUpdate,
}: {
  findingId: string;
  currentStatus: string;
  currentNote?: string | null;
  onUpdate: (status: string, note?: string) => void;
}) {
  const [openMenu, setOpenMenu] = useState(false);
  const [note, setNote] = useState(currentNote ?? "");
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpenMenu(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const meta = STATUS_META[currentStatus] ?? STATUS_META.open;
  const Icon = meta.icon;

  const choose = async (status: string) => {
    if (busy) return;
    setBusy(true);
    try {
      await findingsApi.setStatus(findingId, status, note.trim() || undefined);
      onUpdate(status, note.trim() || undefined);
      toast.success("Status bijgewerkt");
      setOpenMenu(false);
    } catch {
      toast.error("Status bijwerken mislukt.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpenMenu((v) => !v)}
        className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[11px] font-semibold transition-colors ${meta.cls}`}
      >
        <Icon className="h-3 w-3" />
        {meta.label}
        <ChevronDown className="h-3 w-3 opacity-70" />
      </button>

      {openMenu && (
        <div className="absolute right-0 z-20 mt-1 w-56 rounded-lg border border-grid bg-card2 p-2 shadow-glow-cyan">
          {OPTIONS.map((opt) => {
            const m = STATUS_META[opt];
            const OIcon = m.icon;
            const active = opt === currentStatus;
            return (
              <button
                key={opt}
                type="button"
                disabled={busy}
                onClick={() => choose(opt)}
                className={`flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left font-mono text-[12px] transition-colors hover:bg-app ${
                  active ? "text-cyan" : "text-ink"
                }`}
              >
                <OIcon className="h-3.5 w-3.5" /> {m.label}
                {active && <Check className="ml-auto h-3.5 w-3.5 text-cyan" />}
              </button>
            );
          })}
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Toelichting (optioneel)"
            className="mt-2 w-full rounded-md border border-grid bg-app px-2.5 py-1.5 font-mono text-[11px] text-ink outline-none focus:border-cyan/50"
          />
        </div>
      )}
    </div>
  );
}

export default FindingStatusBadge;
