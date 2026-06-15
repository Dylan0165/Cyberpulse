"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Calendar,
  Plus,
  X,
  Trash2,
  Play,
  Pause,
  Clock,
} from "lucide-react";
import { schedulesApi } from "@/lib/api";
import { scanTypeLabel } from "@/lib/labels";
import { GlowCard } from "@/components/cyber/glow-card";

const SCAN_TYPE_LABEL: Record<string, string> = {
  quick: "Snelle test",
  full: "Volledige test",
};

interface Schedule {
  id: string;
  target: string;
  interval: string;
  scan_type: string;
  scan_mode: string;
  enabled: boolean;
  next_run: string | null;
  last_run: string | null;
}

const INTERVAL_LABELS: Record<string, string> = {
  daily: "Dagelijks",
  weekly: "Wekelijks",
  monthly: "Maandelijks",
};

const inputCls =
  "w-full rounded-lg border border-grid bg-app px-3 py-2 text-[13px] text-ink placeholder:text-ink-muted/60 outline-none transition-colors focus:border-cyan focus:shadow-glow-cyan font-mono";

const labelCls =
  "mb-1.5 block text-[11px] uppercase tracking-[0.1em] text-ink-muted";

export default function SchedulePage() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [form, setForm] = useState({
    target: "",
    scan_type: "quick",
    scan_mode: "blackbox",
    target_type: "web",
    interval: "weekly",
    enabled: true,
  });

  async function load() {
    setLoading(true);
    try {
      setSchedules(await schedulesApi.list());
    } catch {
      // Backend may not implement schedules — fall back to empty state.
      setSchedules([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.target.trim()) return;
    setSubmitting(true);
    try {
      await schedulesApi.create(form);
      setShowForm(false);
      setForm({
        target: "",
        scan_type: "quick",
        scan_mode: "blackbox",
        target_type: "web",
        interval: "weekly",
        enabled: true,
      });
      await load();
    } catch {
      // Swallow — never surface raw errors to the user.
    } finally {
      setSubmitting(false);
    }
  }

  async function remove(id: string) {
    try {
      await schedulesApi.remove(id);
      await load();
    } catch {
      /* ignore */
    }
  }

  async function toggle(id: string, enabled: boolean) {
    try {
      await schedulesApi.toggle(id, !enabled);
      await load();
    } catch {
      /* ignore */
    }
  }

  function fmtDate(ts: string | null) {
    if (!ts) return "—";
    try {
      return new Date(ts).toLocaleString("nl-NL", {
        dateStyle: "short",
        timeStyle: "short",
      });
    } catch {
      return ts;
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold tracking-[0.02em] text-ink">
            Automatische tests
          </h1>
          <p className="mt-1 text-[13px] text-ink-muted">
            Automatische scans op vaste tijden
          </p>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="inline-flex items-center gap-2 self-start rounded-lg border border-cyan/40 bg-cyan/10 px-4 py-2 text-[13px] font-medium text-cyan transition-all hover:bg-cyan/20 hover:shadow-glow-cyan"
        >
          {showForm ? (
            <>
              <X className="h-4 w-4" /> Annuleer
            </>
          ) : (
            <>
              <Plus className="h-4 w-4" /> Scan inplannen
            </>
          )}
        </button>
      </div>

      {/* Add form */}
      {showForm && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
        >
          <GlowCard className="p-6">
            <h2 className="mb-5 text-[13px] font-semibold uppercase tracking-[0.1em] text-ink">
              Nieuwe scan plannen
            </h2>
            <form onSubmit={submit}>
              <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
                <div className="md:col-span-2">
                  <label className={labelCls}>Systeem *</label>
                  <input
                    className={inputCls}
                    value={form.target}
                    onChange={(e) =>
                      setForm({ ...form, target: e.target.value })
                    }
                    placeholder="example.com"
                    required
                  />
                </div>
                <div>
                  <label className={labelCls}>Interval</label>
                  <select
                    className={inputCls}
                    value={form.interval}
                    onChange={(e) =>
                      setForm({ ...form, interval: e.target.value })
                    }
                  >
                    <option value="daily">Dagelijks</option>
                    <option value="weekly">Wekelijks</option>
                    <option value="monthly">Maandelijks</option>
                  </select>
                </div>
                <div>
                  <label className={labelCls}>Soort test</label>
                  <select
                    className={inputCls}
                    value={form.scan_type}
                    onChange={(e) =>
                      setForm({ ...form, scan_type: e.target.value })
                    }
                  >
                    <option value="quick">Snelle test</option>
                    <option value="full">Volledige test</option>
                  </select>
                </div>
                <div>
                  <label className={labelCls}>Aanpak</label>
                  <select
                    className={inputCls}
                    value={form.scan_mode}
                    onChange={(e) =>
                      setForm({ ...form, scan_mode: e.target.value })
                    }
                  >
                    <option value="blackbox">Buitenstaander test</option>
                    <option value="greybox">Gedeeltelijke test</option>
                    <option value="whitebox">Volledige doorlichting</option>
                  </select>
                </div>
              </div>
              <div className="mt-6">
                <button
                  type="submit"
                  disabled={submitting || !form.target.trim()}
                  className="inline-flex items-center gap-2 rounded-lg border border-cyan/40 bg-cyan/10 px-5 py-2 text-[13px] font-medium text-cyan transition-all hover:bg-cyan/20 hover:shadow-glow-cyan disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {submitting ? "Plannen..." : "Planning aanmaken"}
                </button>
              </div>
            </form>
          </GlowCard>
        </motion.div>
      )}

      {/* Loading skeletons */}
      {loading && (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="skeleton h-16 w-full rounded-lg" />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && schedules.length === 0 && (
        <GlowCard className="p-12" hoverLift={false}>
          <div className="flex flex-col items-center text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-lg border border-grid bg-app">
              <Calendar className="h-7 w-7 text-cyan" />
            </div>
            <h3 className="text-[15px] font-semibold text-ink">
              Geen geplande scans
            </h3>
            <p className="mt-1 text-[13px] text-ink-muted">
              Plan uw eerste automatische scan
            </p>
            <button
              onClick={() => setShowForm(true)}
              className="mt-5 inline-flex items-center gap-2 rounded-lg border border-cyan/40 bg-cyan/10 px-4 py-2 text-[13px] font-medium text-cyan transition-all hover:bg-cyan/20 hover:shadow-glow-cyan"
            >
              <Plus className="h-4 w-4" /> Scan inplannen
            </button>
            <p className="mt-6 text-[11px] text-ink-muted/70">
              Planning wordt binnenkort volledig ondersteund.
            </p>
          </div>
        </GlowCard>
      )}

      {/* Schedule cards */}
      {!loading && schedules.length > 0 && (
        <div className="grid grid-cols-1 gap-4">
          {schedules.map((s, i) => (
            <motion.div
              key={s.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: i * 0.05 }}
            >
              <GlowCard
                className={`p-5 ${!s.enabled ? "opacity-60" : ""}`}
                accentBorder={s.enabled ? "#00FF88" : "#4A6880"}
              >
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <div className="min-w-0 flex-1 space-y-2">
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="truncate font-mono text-[14px] font-medium text-cyan">
                        {s.target}
                      </span>
                      <span className="rounded-md border border-grid bg-app px-2 py-0.5 text-[10px] uppercase tracking-[0.08em] text-ink-muted">
                        {INTERVAL_LABELS[s.interval] ?? s.interval}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-4 text-[12px] text-ink-muted">
                      <span>
                        {SCAN_TYPE_LABEL[s.scan_type] ?? s.scan_type} · {scanTypeLabel(s.scan_mode)}
                      </span>
                      <span className="inline-flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5" />
                        Volgende: {fmtDate(s.next_run)}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => toggle(s.id, s.enabled)}
                      className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-[12px] font-medium transition-colors ${
                        s.enabled
                          ? "border-neon-green/40 bg-neon-green/10 text-neon-green hover:bg-neon-green/20"
                          : "border-grid bg-card2 text-ink-muted hover:border-ink-muted"
                      }`}
                    >
                      {s.enabled ? (
                        <>
                          <Play className="h-3.5 w-3.5" /> Actief
                        </>
                      ) : (
                        <>
                          <Pause className="h-3.5 w-3.5" /> Gepauzeerd
                        </>
                      )}
                    </button>
                    <button
                      onClick={() => remove(s.id)}
                      aria-label="Verwijder planning"
                      className="inline-flex items-center justify-center rounded-lg border border-grid bg-card2 p-2 text-ink-muted transition-colors hover:border-neon-red/40 hover:text-neon-red"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </GlowCard>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
