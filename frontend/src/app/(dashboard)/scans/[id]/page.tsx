"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { scansApi, reportsApi } from "@/lib/api";
import { useParams } from "next/navigation";
import { useState, useEffect, useRef, useMemo } from "react";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import {
  Shield, ArrowLeft, Play, StopCircle, Download, FileText,
  CheckCircle, AlertTriangle, Activity, Clock, Circle,
  ChevronDown, Cpu, Zap,
} from "lucide-react";
import Link from "next/link";

import { GlowCard } from "@/components/cyber/glow-card";
import { RiskBadge, severityColor } from "@/components/cyber/risk-badge";
import { RiskGauge } from "@/components/cyber/risk-gauge";
import { TerminalOutput, type TermLine } from "@/components/cyber/terminal-output";
import { AttackSurfacePanel } from "@/components/cyber/attack-surface-lazy";
import type { SurfaceNode } from "@/components/cyber/attack-surface";

// ── Types ─────────────────────────────────────────────────────────────────────

interface WsEvent {
  type: string;
  phase?: string;
  phase_num?: number;
  display?: string;
  tool?: string;
  output?: string;
  success?: boolean;
  duration?: number;
  progress?: number;
  risk_score?: number;
  risk_level?: string;
  findings?: number;
  critical?: number;
  high?: number;
  message?: string;
  reason?: string;
  timestamp?: number;
}

interface PhaseState {
  name: string;
  display: string;
  num: number;
  status: "pending" | "running" | "done" | "skipped" | "failed";
  tools: { name: string; done: boolean; success: boolean; output: string; duration?: number }[];
  expanded: boolean;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const PHASE_META: Record<string, { display: string; tools: string[] }> = {
  recon:       { display: "Phase 1 — Reconnaissance",        tools: ["nmap","httpx-pd","whatweb"] },
  vuln_scan:   { display: "Phase 2 — Vulnerability Scan",    tools: ["nuclei"] },
  webapp:      { display: "Phase 3 — Web Application Tests", tools: ["nikto","sqlmap","ffuf"] },
  network:     { display: "Phase 4 — Network Services",      tools: ["nmap"] },
  auth:        { display: "Phase 5 — Authentication Tests",  tools: ["hydra"] },
  ssl:         { display: "Phase 6 — SSL/TLS Analysis",      tools: ["testssl.sh"] },
  osint:       { display: "Phase 7 — OSINT & Secrets",       tools: ["theharvester","gitleaks"] },
  ai_analysis: { display: "Phase 8 — AI Analysis",           tools: ["DeepSeek"] },
  m09: { display: "M09 — Business Logic Tester",    tools: ["custom"] },
  m10: { display: "M10 — CVE Correlator",           tools: ["NVD API"] },
  m11: { display: "M11 — Visual Recon",             tools: ["Playwright"] },
  m12: { display: "M12 — Smart Credential Attack",  tools: ["hydra"] },
  m13: { display: "M13 — AI Adaptive Scanner",      tools: ["DeepSeek"] },
  m14: { display: "M14 — Scan Comparator",          tools: ["diff"] },
};

const CUSTOM_MODULE_KEYS = new Set(["m09", "m10", "m11", "m12", "m13", "m14"]);

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ScanDetailPage() {
  const params = useParams();
  const scanId = params.id as string;
  const queryClient = useQueryClient();

  const [tab, setTab] = useState<"live" | "findings" | "report">("live");
  const [phases, setPhases] = useState<PhaseState[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [terminalLines, setTerminalLines] = useState<string[]>([]);
  const [sevFilter, setSevFilter] = useState<string>("all");
  const [findingSort, setFindingSort] = useState<"severity" | "cvss">("severity");
  const [expandedFinding, setExpandedFinding] = useState<number | null>(null);
  const [selectedNode, setSelectedNode] = useState<SurfaceNode | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const { data: scan, isLoading } = useQuery({
    queryKey: ["scan", scanId],
    queryFn: () => scansApi.get(scanId).then(r => r.data),
    refetchInterval: q => {
      const s = q.state.data;
      return s && ["running","analyzing","pending"].includes(s.status) ? 3000 : false;
    },
  });

  const { data: report } = useQuery({
    queryKey: ["scan-report", scanId],
    queryFn: () => scansApi.getReport(scanId).then(r => r.data),
    enabled: scan?.status === "completed",
  });

  const startMutation = useMutation({
    mutationFn: () => scansApi.start(scanId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scan", scanId] });
      toast.success("Scan gestart!");
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail ?? "Starten mislukt"),
  });

  const cancelMutation = useMutation({
    mutationFn: () => scansApi.cancel(scanId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scan", scanId] });
      toast.success("Scan geannuleerd");
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail ?? "Annuleren mislukt"),
  });

  // Initialise phases from PHASE_META, filtered by which phases this scan has
  useEffect(() => {
    const scanPhaseSet = new Set<string>(scan?.phases ?? []);
    setPhases(
      Object.entries(PHASE_META)
        .filter(([name]) => !CUSTOM_MODULE_KEYS.has(name) || scanPhaseSet.has(name))
        .map(([name, meta], i) => ({
          name, display: meta.display, num: i + 1,
          status: "pending",
          tools: meta.tools.map(t => ({ name: t, done: false, success: true, output: "" })),
          expanded: false,
        }))
    );
  }, [scan?.phases?.join(",")]); // eslint-disable-line react-hooks/exhaustive-deps

  // WebSocket connection
  useEffect(() => {
    if (!scanId) return;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${proto}://${window.location.host}/ws/scan/${scanId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen  = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);
    ws.onerror = () => setWsConnected(false);

    ws.onmessage = (e) => {
      try {
        const ev: WsEvent = JSON.parse(e.data);
        handleWsEvent(ev);
      } catch {}
    };

    return () => { ws.close(); };
  }, [scanId]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleWsEvent(ev: WsEvent) {
    const ts = ev.timestamp ? new Date(ev.timestamp * 1000).toLocaleTimeString() : "";

    switch (ev.type) {
      case "scan_start":
        addTermLine(`[${ts}] ▶ Scan gestart — target: ${ev.message ?? ""}`);
        break;

      case "phase_start":
        addTermLine(`[${ts}] ═══ ${ev.display ?? ev.phase} ═══`);
        setPhases(prev => prev.map(p =>
          p.name === ev.phase ? { ...p, status: "running", expanded: true } : p
        ));
        break;

      case "phase_skip":
        addTermLine(`[${ts}] ⊘ ${ev.phase} overgeslagen: ${ev.reason ?? ""}`);
        setPhases(prev => prev.map(p =>
          p.name === ev.phase ? { ...p, status: "skipped" } : p
        ));
        break;

      case "tool_start":
        addTermLine(`[${ts}]   ⏳ ${ev.tool}...`);
        break;

      case "tool_done":
        addTermLine(`[${ts}]   ${ev.success ? "✓" : "✗"} ${ev.tool} (${ev.duration ?? 0}s)`);
        if (ev.output) {
          const preview = ev.output.split("\n").slice(0, 3).join("\n");
          if (preview.trim()) addTermLine(`         ${preview}`);
        }
        setPhases(prev => prev.map(p => {
          if (p.name !== ev.phase) return p;
          return {
            ...p,
            tools: p.tools.map(t =>
              t.name === ev.tool
                ? { ...t, done: true, success: !!ev.success, output: ev.output ?? "", duration: ev.duration }
                : t
            ),
          };
        }));
        break;

      case "phase_complete":
        setPhases(prev => prev.map(p =>
          p.name === ev.phase ? { ...p, status: "done" } : p
        ));
        break;

      case "scan_complete":
        addTermLine(`[${ts}] ✓ Scan voltooid — risicoscore: ${ev.risk_score}/100 (${ev.risk_level})`);
        addTermLine(`         Bevindingen: ${ev.findings ?? 0} (${ev.critical ?? 0} kritiek, ${ev.high ?? 0} hoog)`);
        queryClient.invalidateQueries({ queryKey: ["scan", scanId] });
        queryClient.invalidateQueries({ queryKey: ["scan-report", scanId] });
        setTab("report");
        break;

      case "error":
        addTermLine(`[${ts}] ✗ FOUT: ${ev.message ?? "onbekende fout"}`);
        break;
    }
  }

  function addTermLine(line: string) {
    setTerminalLines(prev => [...prev.slice(-500), line]);
  }

  // Convert raw terminal strings → styled TermLines for <TerminalOutput/>
  const termLines: TermLine[] = useMemo(
    () => terminalLines.map((line): TermLine => {
      let kind: TermLine["kind"] = "out";
      if (line.includes("✓")) kind = "success";
      else if (line.includes("✗")) kind = "error";
      else if (line.includes("═══")) kind = "phase";
      else if (line.includes("⊘")) kind = "warn";
      else if (line.includes("⏳")) kind = "dim";
      else if (line.startsWith("         ")) kind = "dim";
      return { text: line, kind };
    }),
    [terminalLines]
  );

  const findings = report?.report_data?.findings ?? report?.findings ?? [];
  const aiReport = report?.report_data ?? report ?? null;

  // Build 3D attack-surface nodes from findings that reference a port
  const surfaceNodes: SurfaceNode[] = useMemo(() => {
    const nodes: SurfaceNode[] = [];
    for (let i = 0; i < findings.length; i++) {
      const f: any = findings[i];
      if (f.port) {
        nodes.push({
          id: `${f.port}-${i}`,
          port: Number(f.port),
          service: f.service ?? f.tool ?? "service",
          severity: (f.severity ?? "info").toLowerCase(),
        });
      }
    }
    return nodes;
  }, [findings]);

  // Filtered + sorted findings
  const visibleFindings = useMemo(() => {
    const SEV_ORDER: Record<string, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFO: 4 };
    let list = [...findings];
    if (sevFilter !== "all") {
      list = list.filter((f: any) => (f.severity ?? "").toUpperCase() === sevFilter.toUpperCase());
    }
    list.sort((a: any, b: any) => {
      if (findingSort === "cvss") return (b.cvss ?? 0) - (a.cvss ?? 0);
      return (SEV_ORDER[(a.severity ?? "INFO").toUpperCase()] ?? 5) - (SEV_ORDER[(b.severity ?? "INFO").toUpperCase()] ?? 5);
    });
    return list;
  }, [findings, sevFilter, findingSort]);

  const riskScore = aiReport?.risk_score ?? (scan ? Math.round((100 - (scan.security_score ?? 100))) : 0);

  if (isLoading) {
    return <div className="py-16 text-center font-mono text-sm text-ink-muted">Laden…</div>;
  }
  if (!scan) {
    return <div className="py-16 text-center font-mono text-sm text-ink-muted">Scan niet gevonden</div>;
  }

  return (
    <div className="space-y-6">
      {/* ── Header ── */}
      <div className="flex flex-wrap items-center gap-4">
        <Link
          href="/scans"
          className="flex items-center gap-1.5 rounded-md border border-grid bg-card2 px-3 py-2 font-mono text-[11px] uppercase tracking-wider text-ink-muted transition-colors hover:text-cyan"
        >
          <ArrowLeft className="h-3.5 w-3.5" />Terug
        </Link>
        <div className="flex-1">
          <h1 className="flex items-center gap-2 font-display text-2xl font-bold text-ink">
            <Shield className="h-6 w-6 text-cyan" style={{ filter: "drop-shadow(0 0 6px #00D4FF88)" }} />
            Scan Details
          </h1>
          <p className="mt-0.5 font-mono text-[12px] text-ink-muted">
            {scan.scan_type?.replace("_", " ")} · {new Date(scan.created_at).toLocaleString("nl-NL")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {wsConnected && (
            <span className="flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-wider text-neon-green">
              <span className="h-1.5 w-1.5 rounded-full bg-neon-green animate-pulse-dot" />live
            </span>
          )}
          {scan.status === "pending" && (
            <ActionButton onClick={() => startMutation.mutate()} disabled={startMutation.isPending} variant="primary">
              <Play className="h-3.5 w-3.5" />Scan Starten
            </ActionButton>
          )}
          {scan.status === "running" && (
            <ActionButton onClick={() => cancelMutation.mutate()} variant="danger">
              <StopCircle className="h-3.5 w-3.5" />Stoppen
            </ActionButton>
          )}
          {scan.status === "completed" && (
            <>
              <ActionButton variant="ghost" onClick={async () => {
                const res = await reportsApi.downloadJson(scanId);
                const url = URL.createObjectURL(new Blob([res.data]));
                Object.assign(document.createElement("a"), { href: url, download: `scan-${scanId}.json` }).click();
                URL.revokeObjectURL(url);
              }}>
                <FileText className="h-3.5 w-3.5" />JSON
              </ActionButton>
              <ActionButton variant="ghost" onClick={async () => {
                const res = await reportsApi.downloadPdf(scanId);
                const url = URL.createObjectURL(new Blob([res.data]));
                Object.assign(document.createElement("a"), { href: url, download: `scan-${scanId}.pdf` }).click();
                URL.revokeObjectURL(url);
              }}>
                <Download className="h-3.5 w-3.5" />PDF
              </ActionButton>
            </>
          )}
        </div>
      </div>

      {/* ── Hero: target + gauge + finding counts ── */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Left: target info */}
        <GlowCard className="flex flex-col justify-center p-6">
          <p className="font-mono text-[11px] uppercase tracking-widest text-ink-muted">target</p>
          <p className="mt-1 break-all font-mono text-xl font-semibold text-ink">{scan.target_id ?? "—"}</p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="rounded border border-grid bg-panel px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-cyan">
              {scan.scan_mode ?? "blackbox"}
            </span>
            <StatusChip status={scan.status} />
          </div>
          <div className="mt-4">
            <div className="mb-1 flex items-center justify-between font-mono text-[10px] uppercase tracking-wider text-ink-muted">
              <span>voortgang</span><span>{scan.progress ?? 0}%</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-panel">
              <motion.div
                className="h-full rounded-full"
                style={{ background: "linear-gradient(90deg,#00D4FF,#00FF88)", boxShadow: "0 0 8px #00D4FF" }}
                animate={{ width: `${scan.progress ?? 0}%` }}
                transition={{ duration: 0.7, ease: "easeOut" }}
              />
            </div>
          </div>
        </GlowCard>

        {/* Center: risk gauge */}
        <GlowCard className="flex items-center justify-center p-6">
          <RiskGauge score={riskScore} />
        </GlowCard>

        {/* Right: finding counts */}
        <GlowCard className="p-6">
          <p className="font-mono text-[11px] uppercase tracking-widest text-ink-muted">findings</p>
          <div className="mt-3 grid grid-cols-2 gap-3">
            {[
              { label: "Critical", count: scan.critical_count, color: "#FF2D55" },
              { label: "High",     count: scan.high_count,     color: "#FF8C00" },
              { label: "Medium",   count: scan.medium_count,   color: "#FFD60A" },
              { label: "Low",      count: scan.low_count,      color: "#0A84FF" },
            ].map((b) => (
              <div
                key={b.label}
                className="rounded-lg border border-grid bg-panel px-3 py-2.5"
                style={{ boxShadow: (b.count ?? 0) > 0 ? `inset 0 0 0 1px ${b.color}44` : "none" }}
              >
                <div className="font-display text-2xl font-bold tabular-nums" style={{ color: b.color }}>
                  {b.count ?? 0}
                </div>
                <div className="font-mono text-[10px] uppercase tracking-wider text-ink-muted">{b.label}</div>
              </div>
            ))}
          </div>
        </GlowCard>
      </div>

      {/* ── Tabs ── */}
      <div className="flex gap-1 border-b border-grid">
        {[
          { key: "live",     label: "Live Output" },
          { key: "findings", label: `Findings (${findings.length})` },
          { key: "report",   label: "AI Rapport" },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key as any)}
            className="relative px-4 py-2.5 font-mono text-[12px] uppercase tracking-wider transition-colors"
            style={{ color: tab === t.key ? "#00D4FF" : "#4A6880" }}
          >
            {t.label}
            {tab === t.key && (
              <motion.span
                layoutId="tab-underline"
                className="absolute inset-x-0 -bottom-px h-0.5"
                style={{ background: "#00D4FF", boxShadow: "0 0 8px #00D4FF" }}
              />
            )}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {/* ── Tab: Live Output ── */}
        {tab === "live" && (
          <motion.div
            key="live"
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="grid gap-4 lg:grid-cols-5"
          >
            {/* Phase timeline */}
            <div className="space-y-1.5 lg:col-span-2">
              {phases.map((phase) => (
                <div
                  key={phase.name}
                  className="rounded-lg border transition-colors"
                  style={{
                    borderColor:
                      phase.status === "running" ? "rgba(0,212,255,0.5)" :
                      phase.status === "done"    ? "rgba(0,255,136,0.3)" :
                      phase.status === "skipped" ? "rgba(255,214,10,0.2)" : "#0A2035",
                    background:
                      phase.status === "running" ? "rgba(0,212,255,0.05)" :
                      phase.status === "done"    ? "rgba(0,255,136,0.04)" : "#080F18",
                  }}
                >
                  <button
                    onClick={() => setPhases(prev => prev.map(p => p.name === phase.name ? { ...p, expanded: !p.expanded } : p))}
                    className="flex w-full items-center gap-2.5 px-3 py-2.5 text-left"
                  >
                    <span className={phase.status === "running" ? "rounded-full animate-pulse-ring" : ""}>
                      <PhaseIcon status={phase.status} />
                    </span>
                    <span className="flex-1 font-mono text-[12px] font-medium text-ink">{phase.display}</span>
                    <ChevronDown
                      className="h-3.5 w-3.5 text-ink-muted transition-transform"
                      style={{ transform: phase.expanded ? "rotate(180deg)" : "none" }}
                    />
                  </button>
                  {phase.expanded && (
                    <div className="space-y-1 px-3 pb-2.5 pl-9">
                      {phase.tools.map((tool) => (
                        <div key={tool.name} className="flex items-center gap-2 font-mono text-[11px]">
                          {tool.done
                            ? tool.success
                              ? <CheckCircle className="h-3 w-3 shrink-0 text-neon-green" />
                              : <AlertTriangle className="h-3 w-3 shrink-0 text-neon-red" />
                            : phase.status === "running"
                              ? <Cpu className="h-3 w-3 shrink-0 animate-pulse text-cyan" />
                              : <Circle className="h-3 w-3 shrink-0 text-ink-muted" />}
                          <span className="text-ink-muted">{tool.name}</span>
                          {tool.duration != null && <span className="text-ink-muted/60">{tool.duration}s</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Terminal */}
            <div className="lg:col-span-3">
              <TerminalOutput lines={termLines} complete={scan.status === "completed"} />
            </div>
          </motion.div>
        )}

        {/* ── Tab: Findings ── */}
        {tab === "findings" && (
          <motion.div
            key="findings"
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="space-y-4"
          >
            {/* Filter / sort bar */}
            {findings.length > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                {["all", "critical", "high", "medium", "low"].map((s) => (
                  <button
                    key={s}
                    onClick={() => setSevFilter(s)}
                    className="rounded-md border px-2.5 py-1 font-mono text-[11px] uppercase tracking-wider transition-colors"
                    style={{
                      borderColor: sevFilter === s ? severityColor(s) : "#0A2035",
                      color: sevFilter === s ? (s === "all" ? "#00D4FF" : severityColor(s)) : "#4A6880",
                      background: sevFilter === s ? `${s === "all" ? "#00D4FF" : severityColor(s)}11` : "transparent",
                    }}
                  >
                    {s}
                  </button>
                ))}
                <span className="mx-1 hidden h-4 w-px bg-grid sm:block" />
                {(["severity", "cvss"] as const).map((s) => (
                  <button
                    key={s}
                    onClick={() => setFindingSort(s)}
                    className="rounded-md border px-2.5 py-1 font-mono text-[11px] uppercase tracking-wider transition-colors"
                    style={{
                      borderColor: findingSort === s ? "#00D4FF" : "#0A2035",
                      color: findingSort === s ? "#00D4FF" : "#4A6880",
                    }}
                  >
                    sort: {s}
                  </button>
                ))}
              </div>
            )}

            {visibleFindings.length === 0 ? (
              <div className="py-12 text-center font-mono text-[13px] text-ink-muted">
                {scan.status === "completed"
                  ? "Geen bevindingen — je target lijkt veilig."
                  : "Bevindingen verschijnen hier zodra de scan klaar is."}
              </div>
            ) : (
              visibleFindings.map((f: any, i: number) => {
                const sev = (f.severity ?? "info").toLowerCase();
                const open = expandedFinding === i;
                const critical = sev === "critical";
                return (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: Math.min(i * 0.03, 0.3) }}
                  >
                    <div
                      className={`overflow-hidden rounded-lg border bg-card2 ${critical ? "animate-pulse-red-border" : "border-grid"}`}
                      style={!critical ? { borderLeft: `2px solid ${severityColor(sev)}` } : { borderLeftWidth: 2 }}
                    >
                      <button
                        onClick={() => setExpandedFinding(open ? null : i)}
                        className="flex w-full items-center gap-3 px-4 py-3 text-left"
                      >
                        <RiskBadge severity={sev} />
                        <span className="flex-1 text-[14px] font-medium text-ink">{f.title}</span>
                        {f.cvss != null && (
                          <span className="rounded bg-panel px-2 py-0.5 font-mono text-[11px] text-ink-muted">
                            CVSS {f.cvss}
                          </span>
                        )}
                        <ChevronDown
                          className="h-4 w-4 text-ink-muted transition-transform"
                          style={{ transform: open ? "rotate(180deg)" : "none" }}
                        />
                      </button>
                      <AnimatePresence>
                        {open && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                            className="overflow-hidden"
                          >
                            <div className="space-y-3 border-t border-grid px-4 py-3">
                              <div className="flex flex-wrap gap-3 font-mono text-[11px] text-ink-muted">
                                {f.cve && <span className="text-cyan">{f.cve}</span>}
                                {f.owasp && <span>{f.owasp}</span>}
                                {f.tool && <span>tool: {f.tool}</span>}
                                {f.phase && <span>phase: {f.phase}</span>}
                              </div>
                              {f.description && <Field label="Beschrijving" value={f.description} />}
                              {f.impact && <Field label="Impact" value={f.impact} />}
                              {f.recommendation && <Field label="Aanbeveling" value={f.recommendation} accent />}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </motion.div>
                );
              })
            )}
          </motion.div>
        )}

        {/* ── Tab: AI Report ── */}
        {tab === "report" && (
          <motion.div
            key="report"
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="space-y-5"
          >
            {!aiReport ? (
              <div className="py-12 text-center font-mono text-[13px] text-ink-muted">
                {scan.status === "completed" ? "Rapport laden…" : "Het AI-rapport is beschikbaar na voltooiing van de scan."}
              </div>
            ) : (
              <>
                {/* Risk header */}
                <GlowCard className="flex flex-wrap items-center gap-8 p-6">
                  <RiskGauge score={aiReport.risk_score ?? riskScore} size={150} />
                  <div className="flex-1">
                    <p className="font-mono text-[11px] uppercase tracking-widest text-ink-muted">risk level</p>
                    <p className="mt-1 font-display text-3xl font-bold" style={{ color: severityColor(aiReport.risk_level ?? "info") }}>
                      {aiReport.risk_level ?? "—"}
                    </p>
                  </div>
                </GlowCard>

                {aiReport.management_summary && (
                  <ReportCard title="Managementsamenvatting">
                    <p className="text-[13px] leading-relaxed text-ink">{aiReport.management_summary}</p>
                  </ReportCard>
                )}

                {aiReport.technical_summary && (
                  <ReportCard title="Technische Samenvatting">
                    <p className="font-mono text-[12px] leading-relaxed text-ink-muted">{aiReport.technical_summary}</p>
                  </ReportCard>
                )}

                {aiReport.remediation_roadmap && (
                  <ReportCard title="Herstelplan">
                    <div className="space-y-5">
                      {[
                        { key: "quick_wins", label: "Quick Wins (< 1 dag)", color: "#00FF88" },
                        { key: "short_term", label: "Korte termijn (< 1 week)", color: "#FF8C00" },
                        { key: "long_term",  label: "Lange termijn (< 1 maand)", color: "#0A84FF" },
                      ].map(({ key, label, color }) => {
                        const items = aiReport.remediation_roadmap[key] ?? [];
                        if (!items.length) return null;
                        return (
                          <div key={key}>
                            <p className="mb-2 font-mono text-[11px] font-semibold uppercase tracking-wider" style={{ color }}>
                              {label}
                            </p>
                            <div className="space-y-2">
                              {items.map((item: any, j: number) => (
                                <div key={j} className="rounded-md border-l-2 bg-panel px-3 py-2" style={{ borderColor: color }}>
                                  <p className="text-[13px] font-medium text-ink">{item.title}</p>
                                  {item.effort && <p className="font-mono text-[11px] text-ink-muted">{item.effort}</p>}
                                  {item.steps?.length > 0 && (
                                    <ul className="mt-1.5 space-y-1">
                                      {item.steps.map((s: string, k: number) => (
                                        <li key={k} className="font-mono text-[12px] text-ink-muted">$ {s}</li>
                                      ))}
                                    </ul>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </ReportCard>
                )}

                {aiReport.compliance_mapping && (
                  <ReportCard title="Compliance Mapping">
                    <div className="grid gap-4 md:grid-cols-3">
                      {[
                        { key: "owasp_top10", label: "OWASP Top 10" },
                        { key: "iso27001",    label: "ISO 27001" },
                        { key: "nis2",        label: "NIS2" },
                      ].map(({ key, label }) => {
                        const items: string[] = aiReport.compliance_mapping[key] ?? [];
                        return (
                          <div key={key}>
                            <p className="mb-2 font-mono text-[11px] font-semibold uppercase tracking-wider text-cyan">{label}</p>
                            {items.length === 0
                              ? <p className="text-[12px] text-ink-muted">—</p>
                              : <ul className="space-y-1">{items.map((s, i) => <li key={i} className="text-[12px] text-ink">• {s}</li>)}</ul>}
                          </div>
                        );
                      })}
                    </div>
                  </ReportCard>
                )}
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── 3D Attack surface ── */}
      {scan.status === "completed" && surfaceNodes.length > 0 && (
        <div>
          <div className="mb-3 flex items-center gap-2">
            <Zap className="h-4 w-4 text-cyan" />
            <h2 className="font-display text-[15px] font-semibold text-ink">Attack Surface</h2>
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <AttackSurfacePanel nodes={surfaceNodes} onSelect={setSelectedNode} />
            </div>
            <GlowCard className="p-5">
              <p className="font-mono text-[11px] uppercase tracking-widest text-ink-muted">node detail</p>
              {selectedNode ? (
                <div className="mt-3 space-y-2">
                  <p className="font-mono text-2xl font-bold text-ink">:{selectedNode.port}</p>
                  <p className="font-mono text-[13px] text-cyan">{selectedNode.service}</p>
                  <RiskBadge severity={selectedNode.severity} />
                </div>
              ) : (
                <p className="mt-3 font-mono text-[12px] text-ink-muted">Klik op een node om details te zien.</p>
              )}
            </GlowCard>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Helper components ─────────────────────────────────────────────────────────

function ActionButton({
  children, onClick, disabled, variant = "ghost",
}: {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: "primary" | "danger" | "ghost";
}) {
  const styles =
    variant === "primary" ? { background: "#00D4FF", color: "#000", boxShadow: "0 0 16px rgba(0,212,255,0.3)" } :
    variant === "danger"  ? { background: "#FF2D55", color: "#fff", boxShadow: "0 0 16px rgba(255,45,85,0.3)" } :
                            { background: "#080F18", color: "#E8F4F8", border: "1px solid #0A2035" };
  return (
    <motion.button
      whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
      onClick={onClick} disabled={disabled}
      className="flex items-center gap-1.5 rounded-md px-3.5 py-2 font-mono text-[12px] font-medium uppercase tracking-wider transition-opacity disabled:opacity-50"
      style={styles}
    >
      {children}
    </motion.button>
  );
}

function PhaseIcon({ status }: { status: PhaseState["status"] }) {
  switch (status) {
    case "done":    return <CheckCircle className="h-4 w-4 shrink-0 text-neon-green" />;
    case "running": return <Activity className="h-4 w-4 shrink-0 animate-pulse text-cyan" />;
    case "skipped": return <Circle className="h-4 w-4 shrink-0 text-neon-yellow/50" />;
    case "failed":  return <AlertTriangle className="h-4 w-4 shrink-0 text-neon-red" />;
    default:        return <Circle className="h-4 w-4 shrink-0 text-ink-muted/40" />;
  }
}

function StatusChip({ status }: { status: string }) {
  const map: Record<string, { color: string; label: string; pulse?: boolean }> = {
    completed: { color: "#00FF88", label: "voltooid" },
    running:   { color: "#00D4FF", label: "actief", pulse: true },
    analyzing: { color: "#0A84FF", label: "analyseren", pulse: true },
    pending:   { color: "#FF8C00", label: "wachtend" },
    failed:    { color: "#FF2D55", label: "mislukt" },
    cancelled: { color: "#4A6880", label: "geannuleerd" },
  };
  const c = map[status] ?? { color: "#4A6880", label: status };
  return (
    <span className="flex items-center gap-1.5 rounded border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider"
      style={{ color: c.color, borderColor: `${c.color}44`, background: `${c.color}11` }}>
      <span className={`h-1.5 w-1.5 rounded-full ${c.pulse ? "animate-pulse-dot" : ""}`} style={{ background: c.color }} />
      {c.label}
    </span>
  );
}

function Field({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div>
      <p className="mb-1 font-mono text-[10px] font-semibold uppercase tracking-wider text-ink-muted">{label}</p>
      <p className="text-[13px] leading-relaxed" style={{ color: accent ? "#00FF88" : "#E8F4F8" }}>{value}</p>
    </div>
  );
}

function ReportCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <GlowCard className="p-5">
      <p className="mb-3 font-mono text-[11px] uppercase tracking-widest text-ink-muted">{title}</p>
      {children}
    </GlowCard>
  );
}
