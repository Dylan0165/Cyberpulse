"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { targetsApi } from "@/lib/api";
import Link from "next/link";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, ExternalLink, Trash2, Loader2, X, Server } from "lucide-react";
import { GlowCard } from "@/components/cyber/glow-card";
import { SkeletonCard } from "@/components/cyber/skeleton";
import FloatingEmptyState from "@/components/animations/FloatingEmptyState";

const TYPE_OPTIONS = [
  { value: "url",      label: "Web Application / URL" },
  { value: "domain",   label: "Domein" },
  { value: "ip",       label: "IP-adres (server)" },
  { value: "ip_range", label: "IP-range / Netwerk" },
];

const TYPE_LABEL: Record<string, string> = {
  url: "Web / URL",
  domain: "Domein",
  ip: "IP-adres",
  ip_range: "IP-range",
  web_application: "Web App",
  network: "Netwerk",
  api: "API",
};

export default function TargetsPage() {
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ value: "", target_type: "url", name: "" });
  const [errorMsg, setErrorMsg] = useState("");

  const { data: raw, isLoading } = useQuery({
    queryKey: ["targets"],
    queryFn: () => targetsApi.list().then((r) => r.data),
  });

  // Normalise: backend returns array, guard against other shapes
  const targets: any[] = Array.isArray(raw) ? raw : [];

  const createMutation = useMutation({
    mutationFn: (data: any) => targetsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["targets"] });
      setShowAdd(false);
      setForm({ value: "", target_type: "url", name: "" });
      setErrorMsg("");
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail;
      setErrorMsg(
        typeof detail === "string" ? detail :
        Array.isArray(detail) ? detail.map((d: any) => d.msg ?? String(d)).join(", ") :
        // Structured errors (e.g. target/credit limit) carry a Dutch message.
        (detail && typeof detail === "object" && detail.message) ? detail.message :
        "Aanmaken mislukt"
      );
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => targetsApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["targets"] }),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");
    if (!form.value.trim()) { setErrorMsg("Voer een IP-adres of domein in"); return; }
    createMutation.mutate({
      value:       form.value.trim(),
      name:        form.name.trim() || form.value.trim(),
      target_type: form.target_type,
      hostname:    form.value.trim(),  // backend accepts either field
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-[28px] font-bold text-ink" style={{ letterSpacing: "-0.03em" }}>
            Mijn systemen
          </h1>
          <p className="mt-1 text-[14px] text-ink-muted">
            Beheer de systemen die u regelmatig wilt laten testen
          </p>
        </div>
        <button
          onClick={() => { setShowAdd((s) => !s); setErrorMsg(""); }}
          className="inline-flex shrink-0 items-center gap-2 rounded-lg bg-cyan px-5 py-2.5 text-[14px] font-semibold text-black transition-shadow hover:shadow-glow-cyan"
        >
          {showAdd ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
          Doel toevoegen
        </button>
      </div>

      {/* Add form */}
      <AnimatePresence>
        {showAdd && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <GlowCard glowColor="#00D4FF" className="p-6" hoverLift={false}>
              <h2 className="font-display text-[17px] font-semibold text-ink mb-4">Nieuw doel</h2>
              {errorMsg && (
                <p className="mb-4 rounded-lg border border-neon-red/30 bg-neon-red/5 px-4 py-3 text-[13px] text-neon-red">
                  {errorMsg}
                </p>
              )}
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="mb-1.5 block text-[13px] font-medium text-ink-muted">Vriendelijke naam</label>
                  <input
                    type="text"
                    placeholder="Bijv. Productie webserver"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    className="w-full rounded-lg border border-grid bg-app px-4 py-2.5 font-mono text-[14px] text-ink placeholder:text-ink-muted focus:border-cyan focus:outline-none focus:ring-1 focus:ring-cyan/40"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-[13px] font-medium text-ink-muted">IP-adres of domein</label>
                  <input
                    type="text"
                    placeholder="https://example.com  of  192.168.1.0/24"
                    value={form.value}
                    onChange={(e) => setForm({ ...form, value: e.target.value })}
                    required
                    className="w-full rounded-lg border border-grid bg-app px-4 py-2.5 font-mono text-[14px] text-ink placeholder:text-ink-muted focus:border-cyan focus:outline-none focus:ring-1 focus:ring-cyan/40"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-[13px] font-medium text-ink-muted">Type</label>
                  <select
                    value={form.target_type}
                    onChange={(e) => setForm({ ...form, target_type: e.target.value })}
                    className="w-full rounded-lg border border-grid bg-app px-4 py-2.5 text-[14px] text-ink focus:border-cyan focus:outline-none focus:ring-1 focus:ring-cyan/40"
                  >
                    {TYPE_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                </div>
                <div className="flex gap-3 pt-1">
                  <button
                    type="submit"
                    disabled={createMutation.isPending}
                    className="inline-flex items-center gap-2 rounded-lg bg-cyan px-5 py-2.5 text-[14px] font-semibold text-black transition-shadow hover:shadow-glow-cyan disabled:opacity-50"
                  >
                    {createMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                    {createMutation.isPending ? "Aanmaken..." : "Aanmaken"}
                  </button>
                  <button
                    type="button"
                    onClick={() => { setShowAdd(false); setErrorMsg(""); }}
                    className="rounded-lg border border-grid px-5 py-2.5 text-[14px] font-medium text-ink-muted transition-colors hover:text-ink"
                  >
                    Annuleren
                  </button>
                </div>
              </form>
            </GlowCard>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Target list */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : targets.length === 0 ? (
        <div className="rounded-lg border border-grid bg-card2">
          <FloatingEmptyState
            icon={Server}
            title="Nog geen doelen"
            description="Voeg uw eerste doel toe om te beginnen"
            ctaLabel="Doel toevoegen"
            onCta={() => setShowAdd(true)}
          />
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {targets.map((target: any, idx: number) => {
            const display = target.hostname ?? target.value ?? target.name ?? "—";
            return (
              <motion.div
                key={target.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: idx * 0.05 }}
              >
                <GlowCard glowColor="#00D4FF" className="flex h-full flex-col p-5">
                  {/* Top */}
                  <div className="flex items-start justify-between gap-2">
                    <p className="min-w-0 break-all font-mono text-[15px] font-bold text-ink">
                      {display}
                    </p>
                    {target.is_verified && (
                      <span className="shrink-0 rounded-md border border-neon-green/30 bg-neon-green/10 px-2 py-0.5 text-[11px] font-medium text-neon-green">
                        Geverifieerd
                      </span>
                    )}
                  </div>

                  {target.name && target.name !== display && (
                    <p className="mt-1 truncate text-[13px] text-ink-muted">{target.name}</p>
                  )}

                  <div className="mt-3">
                    <span className="inline-block rounded-md border border-cyan/30 bg-cyan/10 px-2.5 py-0.5 text-[11px] font-medium text-cyan">
                      {TYPE_LABEL[target.target_type] ?? (target.target_type ?? "—")}
                    </span>
                  </div>

                  {/* Bottom buttons */}
                  <div className="mt-auto flex items-center gap-2 pt-5">
                    <Link
                      href={`/scans/new?target=${target.id}`}
                      className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-cyan/10 px-3 py-2 text-[12px] font-semibold text-cyan transition-colors hover:bg-cyan/20"
                    >
                      Scan nu
                    </Link>
                    <Link
                      href={`/targets/${target.id}`}
                      className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-grid px-3 py-2 text-[12px] font-medium text-ink-muted transition-colors hover:text-ink"
                    >
                      Bekijken
                      <ExternalLink className="h-3 w-3" />
                    </Link>
                    <button
                      onClick={() => deleteMutation.mutate(target.id)}
                      disabled={deleteMutation.isPending}
                      aria-label="Verwijderen"
                      className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-grid text-ink-muted transition-colors hover:border-neon-red/40 hover:text-neon-red"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </GlowCard>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
