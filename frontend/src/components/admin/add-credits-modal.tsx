"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Zap } from "lucide-react";
import { AdminModal } from "./admin-modal";
import { adminApi } from "@/lib/api";

/**
 * Admin modal to manually grant credits to a user (support / compensation /
 * test accounts). Posts to /admin/users/{id}/add-credits.
 */
export function AddCreditsModal({
  user,
  onClose,
  onDone,
}: {
  user: { id: string; email?: string; name?: string; credits_remaining?: number } | null;
  onClose: () => void;
  onDone: () => void;
}) {
  const [credits, setCredits] = useState(1);
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    if (!user) return;
    if (!Number.isFinite(credits) || credits <= 0) {
      toast.error("Voer een aantal groter dan 0 in");
      return;
    }
    setSaving(true);
    try {
      await adminApi.addCredits(user.id, Math.floor(credits), reason || undefined);
      toast.success(`${Math.floor(credits)} credits toegevoegd`);
      onDone();
    } catch {
      toast.error("Credits konden niet worden toegevoegd");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AdminModal
      open={user !== null}
      onClose={onClose}
      title="Credits toevoegen"
      subtitle={user?.email}
      footer={
        <>
          <button
            onClick={onClose}
            className="rounded-lg border border-grid bg-card2 px-4 py-2 font-mono text-[12px] uppercase tracking-[0.1em] text-ink-muted transition-colors hover:border-cyan/50 hover:text-cyan"
          >
            Annuleren
          </button>
          <button
            onClick={submit}
            disabled={saving}
            className="inline-flex items-center gap-1.5 rounded-lg bg-cyan px-4 py-2 font-display text-[12px] font-bold uppercase tracking-[0.1em] text-app shadow-glow-cyan transition-transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-60"
          >
            <Zap className="h-3.5 w-3.5" fill="currentColor" />
            {saving ? "Bezig…" : "Toevoegen"}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <div>
          <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-wider text-ink-muted">
            Aantal credits
          </label>
          <input
            type="number"
            min={1}
            value={credits}
            onChange={(e) => setCredits(Number(e.target.value))}
            className="w-full rounded-lg border border-grid bg-app px-3 py-2 font-mono text-[13px] text-ink outline-none focus:border-cyan/60"
          />
          {typeof user?.credits_remaining === "number" && (
            <p className="mt-1.5 font-mono text-[11px] text-ink-muted">
              Huidig saldo: {user.credits_remaining}
            </p>
          )}
        </div>
        <div>
          <label className="mb-1.5 block font-mono text-[11px] uppercase tracking-wider text-ink-muted">
            Reden (optioneel)
          </label>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="bv. klantenservice compensatie"
            className="w-full rounded-lg border border-grid bg-app px-3 py-2 font-mono text-[13px] text-ink outline-none placeholder:text-ink-muted/50 focus:border-cyan/60"
          />
        </div>
      </div>
    </AdminModal>
  );
}

export default AddCreditsModal;
