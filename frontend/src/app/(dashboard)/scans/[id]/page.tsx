"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { scansApi, reportsApi, findingsApi, analyticsApi } from "@/lib/api";
import { FindingStatusBadge, STATUS_META } from "@/components/findings/FindingStatusBadge";
import { FindingMetaBadges } from "@/components/findings/FindingMetaBadges";
import { ScanDiffView } from "@/components/scan/ScanDiffView";
import { getToken } from "@/lib/auth";
import { useParams } from "next/navigation";
import { useState, useEffect, useRef, useMemo } from "react";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import {
  Shield, ArrowLeft, ArrowRight, Play, StopCircle, Download, FileText,
  CheckCircle, AlertTriangle, Activity, Clock, Circle,
  ChevronDown, Cpu, Zap, Wrench, Loader2,
} from "lucide-react";
import Link from "next/link";

import { scanTypeLabel, statusLabel, riskBand, severityLabel } from "@/lib/labels";
import MatrixRain from "@/components/animations/MatrixRain";
import AnimatedCheckmark from "@/components/animations/AnimatedCheckmark";
import Confetti from "@/components/animations/Confetti";
import { usePrefersReducedMotion } from "@/hooks/useAnimation";
import { useAuth } from "@/contexts/auth-context";
import { GlowCard } from "@/components/cyber/glow-card";
import { RiskBadge, severityColor } from "@/components/cyber/risk-badge";
import { RiskGauge } from "@/components/cyber/risk-gauge";
import { TerminalOutput, type TermLine } from "@/components/cyber/terminal-output";
import { TopProgressBar } from "@/components/cyber/top-progress-bar";
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
  recon:       { display: "Fase 1 — Verkenning",                    tools: ["nmap","httpx-pd","whatweb"] },
  vuln_scan:   { display: "Fase 2 — Zwakke plekken zoeken",         tools: ["nuclei"] },
  webapp:      { display: "Fase 3 — Website testen",                tools: ["nikto","sqlmap","ffuf"] },
  network:     { display: "Fase 4 — Netwerk controleren",           tools: ["nmap"] },
  auth:        { display: "Fase 5 — Wachtwoorden testen",           tools: ["hydra"] },
  ssl:         { display: "Fase 6 — Beveiligde verbinding checken", tools: ["testssl.sh"] },
  osint:       { display: "Fase 7 — Openbare informatie check",     tools: ["theharvester","gitleaks"] },
  // Custom modules run after the Kali phases…
  m09: { display: "M09 — Toegangspunten testen",           tools: ["custom"] },
  m10: { display: "M10 — Bekende lekken opzoeken",         tools: ["NVD API"] },
  m11: { display: "M11 — Gevoelige bestanden checken",     tools: ["Playwright"] },
  m12: { display: "M12 — Wachtwoordcheck",                 tools: ["hydra"] },
  m13: { display: "M13 — Slimme vervolgtest",              tools: ["DeepSeek"] },
  m14: { display: "M14 — Vergelijking met vorige meting",  tools: ["diff"] },
  m15: { display: "M15 — Aanvalssimulatie",                tools: ["DeepSeek"] },
  m16: { display: "M16 — Bewijs van risico",               tools: ["Metasploit"] },
  m17: { display: "M17 — Cloud beveiliging check",         tools: ["AWS","Azure","GCP"] },
  // …and AI Analysis is ALWAYS the final step.
  ai_analysis: { display: "Fase 8 — AI-analyse",                    tools: ["DeepSeek"] },
};

const CUSTOM_MODULE_KEYS = new Set(["m09", "m10", "m11", "m12", "m13", "m14", "m15", "m16", "m17"]);

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ScanDetailPage() {
  const params = useParams();
  const scanId = params.id as string;
  const queryClient = useQueryClient();

  const [tab, setTab] = useState<"live" | "findings" | "report" | "remediation">("live");
  const [phases, setPhases] = useState<PhaseState[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [terminalLines, setTerminalLines] = useState<string[]>([]);
  const [secureBusy, setSecureBusy] = useState(false);
  const [sevFilter, setSevFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [statusOverrides, setStatusOverrides] = useState<Record<string, string>>({});
  const [compareWith, setCompareWith] = useState<{ id: string; date: string } | null>(null);
  const [findingSort, setFindingSort] = useState<"severity" | "cvss">("severity");
  const [expandedFinding, setExpandedFinding] = useState<number | null>(null);
  const [selectedNode, setSelectedNode] = useState<SurfaceNode | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reducedMotion = usePrefersReducedMotion();
  const { planInfo } = useAuth();
  // Trial accounts get a limited report: no PDF, no Secure Solution Rapport.
  const isTrial = String(planInfo?.plan ?? "").toLowerCase() === "trial";

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

  // Findings merged with triage status (open/resolved/false_positive/accepted_risk).
  const { data: findingsData } = useQuery({
    queryKey: ["scan-findings", scanId],
    queryFn: () => findingsApi.forScan(scanId).then(r => r.data),
    enabled: scan?.status === "completed",
    retry: false,
  });

  // Sibling completed scans on the same target (for the compare/diff feature).
  const { data: trendData } = useQuery({
    queryKey: ["scan-siblings", (scan as any)?.target_id],
    queryFn: () => analyticsApi.trend((scan as any).target_id).then((r) => r.data),
    enabled: !!(scan as any)?.target_id && scan?.status === "completed",
    retry: false,
  });
  const siblingScans = ((trendData?.points ?? []) as any[])
    .filter((p) => p.scan_id !== scanId)
    .reverse(); // newest first

  const scanActive = scan?.status === "running" || scan?.status === "analyzing";

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

  // Initialise phases from PHASE_META, filtered by which phases this scan has.
  // For historical/completed scans, mark phases that already produced output
  // (or are in phases_completed) as done so the sidebar isn't all "pending".
  useEffect(() => {
    const scanPhaseSet = new Set<string>(scan?.phases ?? []);
    const completedSet = new Set<string>((scan as any)?.phases_completed ?? []);
    const outputs = (scan as any)?.tool_outputs as Record<string, unknown> | undefined;
    const scanDone = scan?.status === "completed";
    setPhases(
      Object.entries(PHASE_META)
        .filter(([name]) => !CUSTOM_MODULE_KEYS.has(name) || scanPhaseSet.has(name))
        .map(([name, meta], i) => {
          const hasOutput = !!(outputs && outputs[name]);
          // A completed scan = every selected phase is done (green). Never show
          // a pending circle on a completed scan. While running, a phase is done
          // once it's in phases_completed or has produced output.
          const done = scanDone || completedSet.has(name) || hasOutput;
          return {
            name, display: meta.display, num: i + 1,
            status: (done ? "done" : "pending") as PhaseState["status"],
            tools: meta.tools.map(t => ({ name: t, done, success: true, output: "" })),
            expanded: false,
          };
        })
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scan?.phases?.join(","), scan?.status, (scan as any)?.phases_completed?.join?.(",")]);

  // WebSocket connection
  useEffect(() => {
    if (!scanId) return;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    // Pass the JWT so the backend can verify scan ownership. The httpOnly
    // cookie is also sent automatically, but the token param works even if
    // cookies are blocked. Demo/student scans are accepted without a token.
    const token = getToken();
    const base = `${proto}://${window.location.host}/ws/scan/${scanId}`;
    const wsUrl = token ? `${base}?token=${encodeURIComponent(token)}` : base;
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
          // Custom modules (m09–m14) get their full curated output rendered;
          // raw Kali tool output stays capped at a 3-line preview.
          const isCustom = /^m\d\d$/.test(ev.phase ?? "");
          const outLines = ev.output.split("\n");
          const shown = isCustom ? outLines : outLines.slice(0, 3);
          for (const ln of shown) {
            if (ln.trim()) addTermLine(`         ${ln}`);
          }
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
        // Mark every remaining phase node green immediately — no reload needed.
        setPhases(prev => prev.map(p =>
          p.status === "failed" ? p : {
            ...p,
            status: "done",
            tools: p.tools.map(t => ({ ...t, done: true })),
          }
        ));
        queryClient.invalidateQueries({ queryKey: ["scan", scanId] });
        queryClient.invalidateQueries({ queryKey: ["scan-report", scanId] });
        setTab("report");
        // Secure Solution Report is auto-generated by the worker — offer it.
        if (((ev.critical ?? 0) + (ev.high ?? 0)) > 0) {
          toast("Secure Solution Rapport is klaar", {
            description: "Download de fix-instructies per bevinding",
            duration: 12000,
            action: { label: "Download", onClick: () => downloadSecureSolution() },
          });
        }
        break;

      case "error":
        addTermLine(`[${ts}] ✗ FOUT: ${ev.message ?? "onbekende fout"}`);
        break;
    }
  }

  function addTermLine(line: string) {
    setTerminalLines(prev => [...prev.slice(-500), line]);
  }

  function lineKind(line: string): TermLine["kind"] {
    if (line.includes("✓") || line.includes("GEVONDEN") || line.includes("voltooid")) return "success";
    if (line.includes("✗") || /fout|mislukt|refused|geweigerd|error/i.test(line)) return "error";
    if (line.includes("═══")) return "phase";
    if (line.includes("⚠️") || line.includes("⊘") || line.includes("NIET GEDETECTEERD")) return "warn";
    if (line.includes("⏳") || line.startsWith("  ")) return "dim";
    return "out";
  }

  // Convert raw terminal strings → styled TermLines for <TerminalOutput/>
  const termLines: TermLine[] = useMemo(
    () => terminalLines.map((line): TermLine => ({ text: line, kind: lineKind(line) })),
    [terminalLines]
  );

  // Historical fallback: rebuild the terminal from stored tool_outputs so a
  // completed scan (no live events) still shows every phase + custom module.
  const historicalTermLines: TermLine[] = useMemo(() => {
    const outputs = (scan as any)?.tool_outputs as Record<string, Record<string, string>> | undefined;
    if (!outputs) return [];
    const lines: TermLine[] = [];
    const orderedKeys = [
      ...Object.keys(PHASE_META),                       // recon..ai_analysis, m09..m14
      ...Object.keys(outputs).filter(k => !(k in PHASE_META)), // anything else
    ];
    const seen = new Set<string>();
    for (const phase of orderedKeys) {
      if (seen.has(phase)) continue;
      seen.add(phase);
      const tools = outputs[phase];
      if (!tools) continue;
      const display = PHASE_META[phase]?.display ?? phase;
      lines.push({ text: `═══ ${display} ═══`, kind: "phase" });
      for (const [toolName, text] of Object.entries(tools)) {
        if (!text) continue;
        if (toolName !== "module") lines.push({ text: `  ${toolName}:`, kind: "dim" });
        for (const ln of String(text).split("\n")) {
          if (ln.trim()) lines.push({ text: `  ${ln}`, kind: lineKind(ln) });
        }
      }
    }
    return lines;
  }, [scan]);

  // Prefer the live stream; fall back to the stored output for historical scans.
  const displayLines = termLines.length > 0 ? termLines : historicalTermLines;

  // Prefer the status-merged findings (they carry id + triage status + OWASP/CWE
  // enrichment); fall back to the raw report findings until that query loads.
  const findings = findingsData?.findings ?? report?.report_data?.findings ?? report?.findings ?? [];
  const aiReport = report?.report_data ?? report ?? null;

  const effStatus = (f: any): string => statusOverrides[f.id] ?? f.status ?? "open";

  // After the AI analysis, append a "Snelle fixes" block to the terminal with a
  // one-liner fix hint per critical/high finding (comes from the AI report).
  const snelleFixes: string[] = ((aiReport as any)?.snelle_fixes ?? []).filter(Boolean);
  const renderLines: TermLine[] = snelleFixes.length
    ? [
        ...displayLines,
        { text: "", kind: "out" as TermLine["kind"] },
        { text: "═══ Snelle fixes ═══", kind: "phase" as TermLine["kind"] },
        ...snelleFixes.map((f: string): TermLine => ({
          text: f,
          kind: /secure solution/i.test(f) ? "warn" : "success",
        })),
      ]
    : displayLines;

  // The Secure Solution report only makes sense if there is something to fix.
  const hasFixable = (findings ?? []).some((f: any) =>
    ["critical", "high", "medium"].includes(String(f.severity ?? f.ernst ?? "").toLowerCase())
  );

  async function downloadSecureSolution() {
    if (isTrial) {
      toast.error("Het Secure Solution Rapport vereist credits. Koop een pakket voor het volledige rapport.");
      return;
    }
    setSecureBusy(true);
    const t = toast.loading("Secure Solution Rapport wordt gegenereerd… (10-30s)");
    try {
      const res = await reportsApi.downloadSecureSolution(scanId);
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      Object.assign(document.createElement("a"), {
        href: url, download: `scanix-secure-solution-${scanId}.pdf`,
      }).click();
      URL.revokeObjectURL(url);
      toast.success("Secure Solution Rapport gedownload", { id: t });
    } catch {
      toast.error("Rapport kon niet worden gegenereerd", { id: t });
    } finally {
      setSecureBusy(false);
    }
  }

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
    if (statusFilter !== "all") {
      list = list.filter((f: any) => (statusOverrides[f.id] ?? f.status ?? "open") === statusFilter);
    }
    list.sort((a: any, b: any) => {
      if (findingSort === "cvss") return (b.cvss ?? 0) - (a.cvss ?? 0);
      return (SEV_ORDER[(a.severity ?? "INFO").toUpperCase()] ?? 5) - (SEV_ORDER[(b.severity ?? "INFO").toUpperCase()] ?? 5);
    });
    return list;
  }, [findings, sevFilter, statusFilter, statusOverrides, findingSort]);

  // Counts per triage status for the status filter chips.
  const statusCounts = useMemo(() => {
    const c: Record<string, number> = { all: findings.length, open: 0, resolved: 0, false_positive: 0, accepted_risk: 0 };
    for (const f of findings as any[]) {
      const s = statusOverrides[f.id] ?? f.status ?? "open";
      c[s] = (c[s] ?? 0) + 1;
    }
    return c;
  }, [findings, statusOverrides]);

  const riskScore = aiReport?.risk_score ?? (scan ? Math.round((100 - (scan.security_score ?? 100))) : 0);

  const providerLabel = (() => {
    switch ((scan as any)?.ai_provider_used) {
      case "anthropic": return "Geanalyseerd door Claude (Anthropic)";
      case "runpod":    return "Geanalyseerd door Scanix AI";
      case "deepseek":  return "Geanalyseerd door DeepSeek";
      default:          return null;
    }
  })();

  if (isLoading) {
    return <div className="py-16 text-center font-mono text-sm text-ink-muted">Laden…</div>;
  }
  if (!scan) {
    return <div className="py-16 text-center font-mono text-sm text-ink-muted">Scan niet gevonden</div>;
  }

  return (
    <div className="space-y-6">
      <style>{`
        @keyframes sxd2-term-glow {
          0%, 100% { box-shadow: 0 0 0 1px rgba(0,212,255,0.15), 0 0 12px rgba(0,212,255,0.15); }
          50%      { box-shadow: 0 0 0 1px rgba(0,212,255,0.45), 0 0 26px rgba(0,212,255,0.40); }
        }
        .sxd2-terminal-active { animation: sxd2-term-glow 2.4s ease-in-out infinite; }

        @keyframes sxd2-phase-pulse {
          0%, 100% { transform: scale(1); filter: drop-shadow(0 0 2px rgba(0,212,255,0.5)); }
          50%      { transform: scale(1.18); filter: drop-shadow(0 0 8px rgba(0,212,255,0.9)); }
        }
        .sxd2-phase-pulse { display: inline-flex; animation: sxd2-phase-pulse 1.4s ease-in-out infinite; }

        @keyframes sxd2-slide-in {
          from { opacity: 0; transform: translateX(28px); }
          to   { opacity: 1; transform: translateX(0); }
        }
        .sxd2-finding-slide { animation: sxd2-slide-in 0.5s cubic-bezier(0.2,0.7,0.2,1) both; }

        @keyframes sxd2-badge-breathe {
          0%, 100% { box-shadow: 0 0 0 0 var(--sxd2-sev, #00D4FF); filter: drop-shadow(0 0 2px var(--sxd2-sev, #00D4FF)); }
          50%      { filter: drop-shadow(0 0 7px var(--sxd2-sev, #00D4FF)); }
        }
        .sxd2-badge-breathe { display: inline-flex; animation: sxd2-badge-breathe 2.2s ease-in-out infinite; }

        @keyframes sxd2-crit-flash {
          0%   { opacity: 0; transform: translateX(28px); }
          12%  { opacity: 1; transform: translateX(0); }
          24%  { background-color: rgba(255,45,85,0.22); transform: translateX(-3px); }
          32%  { transform: translateX(3px); }
          40%  { transform: translateX(-2px); }
          48%  { transform: translateX(0); background-color: rgba(255,45,85,0.10); }
          100% { background-color: transparent; }
        }
        .sxd2-critical-flash { animation: sxd2-crit-flash 1.2s ease-out 1 both; }

        @keyframes sxd2-shine-sweep {
          0%   { transform: translateX(-130%) skewX(-18deg); }
          60%, 100% { transform: translateX(230%) skewX(-18deg); }
        }
        .sxd2-shine::after {
          content: "";
          position: absolute;
          top: 0; left: 0; bottom: 0;
          width: 45%;
          pointer-events: none;
          background: linear-gradient(90deg, transparent, rgba(255,255,255,0.55), transparent);
          animation: sxd2-shine-sweep 3s ease-in-out infinite;
        }
        @media (prefers-reduced-motion: reduce) {
          .sxd2-terminal-active,
          .sxd2-phase-pulse,
          .sxd2-finding-slide,
          .sxd2-badge-breathe,
          .sxd2-critical-flash { animation: none !important; }
          .sxd2-shine::after { animation: none !important; display: none; }
        }
      `}</style>
      <TopProgressBar
        active={["running", "analyzing", "pending"].includes(scan.status)}
        progress={scan.progress ?? 0}
        complete={scan.status === "completed"}
      />
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
            Scandetails
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
          <p className="font-mono text-[11px] uppercase tracking-widest text-ink-muted">doelwit</p>
          <p className="mt-1 break-all font-mono text-xl font-semibold text-ink">{scan.target_value ?? scan.target_id ?? "—"}</p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="rounded border border-grid bg-panel px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-cyan">
              {scanTypeLabel(scan.scan_mode ?? "blackbox")}
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
        <GlowCard className="flex flex-col items-center justify-center p-6">
          <RiskGauge score={riskScore} />
          {(() => {
            const band = riskBand(riskScore);
            return (
              <>
                <p className="mt-2 font-display text-[15px] font-semibold text-ink">{band.label}</p>
                <p className="font-mono text-[11px] text-ink-muted">{band.subtext}</p>
              </>
            );
          })()}
          {providerLabel && (
            <p className="mt-3 font-mono text-[11px] text-ink-muted">
              {providerLabel}
            </p>
          )}
        </GlowCard>

        {/* Right: finding counts */}
        <GlowCard className="p-6">
          <p className="font-mono text-[11px] uppercase tracking-widest text-ink-muted">bevindingen</p>
          <div className="mt-3 grid grid-cols-2 gap-3">
            {[
              { label: "Zeer ernstig", count: scan.critical_count, color: "#FF2D55" },
              { label: "Ernstig",      count: scan.high_count,     color: "#FF8C00" },
              { label: "Gemiddeld",    count: scan.medium_count,   color: "#FFD60A" },
              { label: "Laag risico",  count: scan.low_count,      color: "#0A84FF" },
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
          { key: "live",     label: "Live weergave" },
          { key: "findings", label: `Bevindingen (${findings.length})` },
          { key: "report",   label: "AI Rapport" },
          { key: "remediation", label: "Herstelplan" },
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
                    <span
                      className={
                        phase.status === "running"
                          ? "rounded-full animate-pulse-ring motion-reduce:animate-none sxd2-phase-pulse"
                          : ""
                      }
                    >
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
            <div
              className={`relative overflow-hidden rounded-lg lg:col-span-3 ${
                scanActive && !reducedMotion ? "sxd2-terminal-active" : ""
              }`}
            >
              {!reducedMotion && (
                <>
                  {/* Low-opacity SOC ambience behind the matrix rain (md+ only). */}
                  <video
                    src="/videos/animatie2.mp4"
                    poster="/videos/posters/poster2.jpg"
                    autoPlay
                    muted
                    loop
                    playsInline
                    preload="none"
                    aria-hidden="true"
                    tabIndex={-1}
                    className="pointer-events-none absolute inset-0 z-0 hidden h-full w-full object-cover opacity-[0.08] md:block"
                  />
                  <MatrixRain className="pointer-events-none absolute inset-0 z-0 opacity-40 motion-reduce:hidden" />
                </>
              )}
              <div className="relative z-10">
                <TerminalOutput lines={renderLines} complete={scan.status === "completed"} />
              </div>
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
                    {s === "all" ? "Alles" : severityLabel(s)}
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
                    sorteer: {s === "severity" ? "ernst" : "cvss"}
                  </button>
                ))}
              </div>
            )}

            {/* Status filter */}
            {findings.length > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                {([
                  ["all", "Alle"],
                  ["open", "Open"],
                  ["resolved", "Opgelost"],
                  ["false_positive", "False positive"],
                  ["accepted_risk", "Geaccepteerd"],
                ] as const).map(([key, label]) => {
                  const active = statusFilter === key;
                  return (
                    <button
                      key={key}
                      onClick={() => setStatusFilter(key)}
                      className={`rounded-md border px-2.5 py-1 font-mono text-[11px] transition-colors ${
                        active ? "border-cyan/60 bg-cyan/10 text-cyan" : "border-grid text-ink-muted hover:text-ink"
                      }`}
                    >
                      {label} ({statusCounts[key] ?? 0})
                    </button>
                  );
                })}
              </div>
            )}

            {/* Compare with a previous scan */}
            {siblingScans.length > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-[12px] text-ink-muted">↔ Vergelijk met:</span>
                <select
                  value={compareWith?.id ?? ""}
                  onChange={(e) => {
                    const p = siblingScans.find((s) => s.scan_id === e.target.value);
                    setCompareWith(p ? { id: p.scan_id, date: p.date } : null);
                  }}
                  className="rounded-md border border-grid bg-card2 px-3 py-1.5 font-mono text-[12px] text-ink outline-none focus:border-cyan/60"
                >
                  <option value="">— kies een vorige scan —</option>
                  {siblingScans.map((s) => (
                    <option key={s.scan_id} value={s.scan_id}>{s.date} (score {s.risk_score})</option>
                  ))}
                </select>
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
                const fStatus = effStatus(f);
                const isResolved = fStatus === "resolved" || fStatus === "false_positive";
                const sMeta = STATUS_META[fStatus] ?? STATUS_META.open;
                return (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: Math.min(i * 0.03, 0.3) }}
                  >
                    <div
                      className={`overflow-hidden rounded-lg border border-grid ${isResolved ? "bg-card2/50 opacity-70" : "bg-card2"} ${
                        reducedMotion
                          ? ""
                          : critical && !isResolved
                          ? "sxd2-critical-flash"
                          : "sxd2-finding-slide"
                      }`}
                      style={{
                        ...(isResolved
                          ? {}
                          : sev === "critical"
                          ? { borderLeft: "2px solid #FF2D55" }
                          : sev === "high"
                          ? { borderLeft: "2px solid #FF8C00" }
                          : {}),
                        ...(reducedMotion ? {} : { animationDelay: `${i * 80}ms` }),
                      }}
                    >
                      <button
                        onClick={() => setExpandedFinding(open ? null : i)}
                        className="flex w-full items-center gap-3 px-4 py-3 text-left"
                      >
                        <span
                          className={reducedMotion ? "" : "sxd2-badge-breathe"}
                          style={
                            { "--sxd2-sev": severityColor(sev) } as React.CSSProperties
                          }
                        >
                          <RiskBadge severity={sev} />
                        </span>
                        <span className={`flex-1 text-[14px] font-medium text-ink ${isResolved ? "line-through decoration-ink-muted/60" : ""}`}>{f.title}</span>
                        <span className={`hidden items-center rounded-full border px-2 py-0.5 font-mono text-[10px] font-semibold sm:inline-flex ${sMeta.cls}`}>
                          {sMeta.label}
                        </span>
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
                              <FindingMetaBadges
                                owasp_category={f.owasp_category}
                                owasp_label={f.owasp_label}
                                cwe={f.cwe}
                                cwe_url={f.cwe_url}
                                cve_id={f.cve_id}
                                cve_url={f.cve_url}
                                mitre_technique={f.mitre_technique}
                              />
                              <div className="flex flex-wrap gap-3 font-mono text-[11px] text-ink-muted">
                                {f.tool && <span>tool: {f.tool}</span>}
                                {f.phase && <span>fase: {f.phase}</span>}
                                {f.duplicate_count > 1 && <span>gevonden door {f.duplicate_count} modules</span>}
                              </div>
                              {f.description && <Field label="Beschrijving" value={f.description} />}
                              {f.impact && <Field label="Impact" value={f.impact} />}
                              {f.recommendation && <Field label="Aanbeveling" value={f.recommendation} accent />}
                              {f.evidence && (
                                <Field
                                  label="Bewijs"
                                  value={typeof f.evidence === "string" ? f.evidence : JSON.stringify(f.evidence, null, 2)}
                                />
                              )}
                              {f.id && (
                                <div className="flex items-center justify-end border-t border-grid pt-3">
                                  <FindingStatusBadge
                                    findingId={f.id}
                                    currentStatus={fStatus}
                                    currentNote={f.status_note}
                                    onUpdate={(status) => setStatusOverrides((prev) => ({ ...prev, [f.id]: status }))}
                                  />
                                </div>
                              )}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </motion.div>
                );
              })
            )}

            {/* Scan diff (rendered onder de bevindingen) */}
            {compareWith && (
              <ScanDiffView
                currentScanId={scanId}
                previousScanId={compareWith.id}
                previousDate={compareWith.date}
                onClose={() => setCompareWith(null)}
              />
            )}
          </motion.div>
        )}

        {/* ── Tab: Remediation checklist ── */}
        {tab === "remediation" && (
          <motion.div key="remediation" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-4">
            {(() => {
              const FIX_TIME: Record<string, string> = { critical: "2 uur", high: "1 uur", medium: "30 min", low: "15 min", info: "5 min" };
              const all = (findings as any[]).filter((f) => f.id);
              const openItems = all.filter((f) => !["resolved", "false_positive"].includes(effStatus(f)));
              const doneCount = all.length - openItems.length;
              const pct = all.length ? Math.round((doneCount / all.length) * 100) : 0;
              const order: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
              const sorted = [...openItems].sort((a, b) => (order[(a.severity ?? "info").toLowerCase()] ?? 5) - (order[(b.severity ?? "info").toLowerCase()] ?? 5));
              const csv = () => {
                const rows = [["severity", "title", "status", "fix_time"], ...all.map((f) => [f.severity ?? "", (f.title ?? "").replace(/[",\n]/g, " "), effStatus(f), FIX_TIME[(f.severity ?? "info").toLowerCase()] ?? ""])];
                const blob = new Blob([rows.map((r) => r.join(",")).join("\n")], { type: "text/csv" });
                const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = `herstelplan_${scanId}.csv`; a.click(); URL.revokeObjectURL(url);
              };
              return (
                <>
                  <div className="rounded-lg border border-grid bg-card2 p-4">
                    <div className="flex items-center justify-between font-mono text-[12px]">
                      <span className="text-ink">{doneCount} van {all.length} opgelost ({pct}%)</span>
                      <button onClick={csv} className="rounded-md border border-grid px-2.5 py-1 text-ink-muted hover:border-cyan/50 hover:text-cyan">Exporteer CSV</button>
                    </div>
                    <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-app">
                      <div className="h-full rounded-full bg-neon-green transition-all" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                  {sorted.length === 0 ? (
                    <div className="py-10 text-center font-mono text-[13px] text-ink-muted">Alles opgelost — geen open bevindingen 🎉</div>
                  ) : sorted.map((f) => (
                    <div key={f.id} className="flex items-start gap-3 rounded-lg border border-grid bg-card2 p-3">
                      <button
                        onClick={() => { findingsApi.setStatus(f.id, "resolved").then(() => { setStatusOverrides((p) => ({ ...p, [f.id]: "resolved" })); toast.success("Gemarkeerd als opgelost"); }).catch(() => toast.error("Mislukt")); }}
                        className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded border border-grid hover:border-neon-green"
                        aria-label="Markeer als opgelost"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <RiskBadge severity={(f.severity ?? "info").toLowerCase()} />
                          <span className="text-[13px] font-medium text-ink">{f.title}</span>
                          <span className="ml-auto font-mono text-[11px] text-ink-muted">{FIX_TIME[(f.severity ?? "info").toLowerCase()] ?? "30 min"}</span>
                        </div>
                        {(f.fix_command || f.recommendation) && (
                          <pre className="mt-2 overflow-x-auto rounded bg-app p-2 font-mono text-[11px] text-ink-muted">{f.fix_command || f.recommendation}</pre>
                        )}
                      </div>
                    </div>
                  ))}
                </>
              );
            })()}
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
                {/* Scan voltooid banner */}
                <div className="flex items-center justify-center gap-2.5 font-mono text-[13px] uppercase tracking-wider text-neon-green">
                  <AnimatedCheckmark size={28} />
                  <span>Scan voltooid</span>
                </div>
                {!reducedMotion && riskScore < 30 && <Confetti trigger={true} />}

                {/* Trial report banner — PDF & Secure Solution are credit-only */}
                {isTrial && (
                  <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-orange/50 bg-orange/10 px-4 py-3">
                    <p className="font-mono text-[12px] leading-relaxed text-orange">
                      Dit is een trial rapport. Koop credits voor het volledige rapport inclusief
                      PDF en Secure Solution.
                    </p>
                    <Link
                      href="/billing"
                      className="inline-flex items-center gap-1.5 rounded-lg bg-orange px-3 py-1.5 text-[12px] font-bold text-app transition-transform hover:scale-[1.02]"
                    >
                      Volledig rapport €49 <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                )}

                {/* Executive summary (plain-language, for management) */}
                {((aiReport as any)?.executive_summary || ((aiReport as any)?.top_3_actions?.length)) && (
                  <div className="rounded-lg border border-cyan/30 bg-cyan/[0.04] p-4">
                    <p className="mb-2 font-mono text-[11px] uppercase tracking-wider text-cyan">Samenvatting voor management</p>
                    {(aiReport as any)?.executive_summary && (
                      <p className="text-[13px] leading-relaxed text-ink">{(aiReport as any).executive_summary}</p>
                    )}
                    {Array.isArray((aiReport as any)?.top_3_actions) && (aiReport as any).top_3_actions.length > 0 && (
                      <ol className="mt-3 space-y-1.5">
                        {(aiReport as any).top_3_actions.slice(0, 3).map((a: any, idx: number) => (
                          <li key={idx} className="flex items-start gap-2 font-mono text-[12px] text-ink-muted">
                            <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-cyan/15 text-[11px] font-bold text-cyan">{idx + 1}</span>
                            <span><span className="text-ink">{a.action ?? a}</span>{a.time_estimate ? ` — ${a.time_estimate}` : ""}</span>
                          </li>
                        ))}
                      </ol>
                    )}
                  </div>
                )}

                {/* OWASP Top 10 coverage */}
                {Array.isArray((aiReport as any)?.owasp_coverage) && (aiReport as any).owasp_coverage.length > 0 && (
                  <div className="overflow-hidden rounded-lg border border-grid">
                    <div className="border-b border-grid bg-card2 px-4 py-2.5 font-mono text-[11px] uppercase tracking-wider text-ink-muted">
                      OWASP Top 10 — dekking
                    </div>
                    <table className="w-full text-left">
                      <tbody>
                        {[...((aiReport as any).owasp_coverage as any[])]
                          .sort((a, b) => {
                            const o = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"];
                            return o.indexOf(a.worst) - o.indexOf(b.worst);
                          })
                          .map((row) => (
                            <tr key={row.owasp} className="border-b border-grid/60">
                              <td className="px-4 py-2 font-mono text-[12px] text-ink">{row.owasp}</td>
                              <td className="px-4 py-2 font-mono text-[12px] text-ink-muted">{row.label}</td>
                              <td className="px-4 py-2 font-mono text-[12px] tabular-nums text-ink">
                                {row.count} {row.count === 1 ? "bevinding" : "bevindingen"}
                              </td>
                              <td className="px-4 py-2 text-right">
                                <span className="font-mono text-[11px] font-semibold" style={{ color: severityColor(String(row.worst).toLowerCase()) }}>
                                  {severityLabel(String(row.worst).toLowerCase())}
                                </span>
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Risk header */}
                <GlowCard className="flex flex-wrap items-center gap-8 p-6">
                  <RiskGauge score={aiReport.risk_score ?? riskScore} size={150} />
                  <div className="flex-1">
                    <p className="font-mono text-[11px] uppercase tracking-widest text-ink-muted">risico niveau</p>
                    <p className="mt-1 font-display text-3xl font-bold" style={{ color: severityColor(aiReport.risk_level ?? "info") }}>
                      {aiReport.risk_level ?? "—"}
                    </p>
                  </div>
                  {/* Export buttons */}
                  <div className="flex flex-wrap gap-2">
                    <span className="relative inline-block overflow-hidden rounded-md sxd2-shine">
                      <ActionButton variant="primary" onClick={async () => {
                        if (isTrial) {
                          toast.error("PDF-download vereist credits. Koop een pakket voor het volledige rapport.");
                          return;
                        }
                        const res = await reportsApi.downloadPdf(scanId);
                        const url = URL.createObjectURL(new Blob([res.data]));
                        Object.assign(document.createElement("a"), { href: url, download: `rapport-${scanId}.pdf` }).click();
                        URL.revokeObjectURL(url);
                      }}>
                        <FileText className="h-3.5 w-3.5" />PDF
                      </ActionButton>
                    </span>
                    <ActionButton variant="ghost" onClick={async () => {
                      const res = await reportsApi.downloadJson(scanId);
                      const url = URL.createObjectURL(new Blob([res.data]));
                      Object.assign(document.createElement("a"), { href: url, download: `rapport-${scanId}.json` }).click();
                      URL.revokeObjectURL(url);
                    }}>
                      JSON
                    </ActionButton>
                    <ActionButton variant="ghost" onClick={async () => {
                      try {
                        const res = await reportsApi.downloadNis2(scanId);
                        const url = URL.createObjectURL(new Blob([res.data]));
                        Object.assign(document.createElement("a"), { href: url, download: `nis2-${scanId}.pdf` }).click();
                        URL.revokeObjectURL(url);
                      } catch {
                        toast.error("NIS2-rapport kon niet worden gedownload");
                      }
                    }}>
                      <Shield className="h-3.5 w-3.5" />NIS2 Rapport
                    </ActionButton>
                    {hasFixable && (
                      <button
                        onClick={downloadSecureSolution}
                        disabled={secureBusy}
                        title="Download fix-instructies per bevinding"
                        className="inline-flex items-center gap-1.5 rounded-lg border border-orange/50 bg-orange/10 px-3 py-1.5 text-[12px] font-medium text-orange transition-all hover:bg-orange/20 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {secureBusy ? (
                          <><Loader2 className="h-3.5 w-3.5 animate-spin" />Rapport wordt gegenereerd…</>
                        ) : (
                          <><Wrench className="h-3.5 w-3.5" />Secure Solution Rapport</>
                        )}
                      </button>
                    )}
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
            <h2 className="font-display text-[15px] font-semibold text-ink">Aanvalsoppervlak</h2>
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <AttackSurfacePanel nodes={surfaceNodes} onSelect={setSelectedNode} />
            </div>
            <GlowCard className="p-5">
              <p className="font-mono text-[11px] uppercase tracking-widest text-ink-muted">details onderdeel</p>
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
      whileHover={{ filter: "brightness(1.08)" }}
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
  const map: Record<string, { color: string; pulse?: boolean }> = {
    completed: { color: "#00FF88" },
    running:   { color: "#00D4FF", pulse: true },
    analyzing: { color: "#0A84FF", pulse: true },
    pending:   { color: "#FF8C00" },
    failed:    { color: "#FF2D55" },
    cancelled: { color: "#4A6880" },
  };
  const c = map[status] ?? { color: "#4A6880" };
  return (
    <span className="flex items-center gap-1.5 rounded border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider"
      style={{ color: c.color, borderColor: `${c.color}44`, background: `${c.color}11` }}>
      <span className={`h-1.5 w-1.5 rounded-full ${c.pulse ? "animate-pulse-dot" : ""}`} style={{ background: c.color }} />
      {statusLabel(status)}
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
