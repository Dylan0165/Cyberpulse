"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { scansApi, reportsApi } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useParams } from "next/navigation";
import { useState, useEffect, useRef } from "react";
import { toast } from "sonner";
import {
  Shield, ArrowLeft, Play, StopCircle, Download, FileText,
  CheckCircle, AlertTriangle, Activity, Clock, Circle,
  ChevronDown, ChevronRight, Terminal, Cpu,
} from "lucide-react";
import Link from "next/link";

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
  // Custom modules
  m09: { display: "M09 — Business Logic Tester",    tools: ["custom"] },
  m10: { display: "M10 — CVE Correlator",           tools: ["NVD API"] },
  m11: { display: "M11 — Visual Recon",             tools: ["Playwright"] },
  m12: { display: "M12 — Smart Credential Attack",  tools: ["hydra"] },
  m13: { display: "M13 — AI Adaptive Scanner",      tools: ["DeepSeek"] },
  m14: { display: "M14 — Scan Comparator",          tools: ["diff"] },
};

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: "bg-red-600 text-white",
  HIGH:     "bg-orange-500 text-white",
  MEDIUM:   "bg-yellow-500 text-black",
  LOW:      "bg-blue-500 text-white",
  INFO:     "bg-gray-500 text-white",
};

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ScanDetailPage() {
  const params = useParams();
  const scanId = params.id as string;
  const queryClient = useQueryClient();

  const [tab, setTab] = useState<"live" | "findings" | "report">("live");
  const [phases, setPhases] = useState<PhaseState[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [terminalLines, setTerminalLines] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const termRef = useRef<HTMLDivElement>(null);

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
  const CUSTOM_MODULE_KEYS = new Set(["m09", "m10", "m11", "m12", "m13", "m14"]);
  useEffect(() => {
    const scanPhaseSet = new Set<string>(scan?.phases ?? []);
    setPhases(
      Object.entries(PHASE_META)
        // Only include custom modules that were actually selected for this scan
        .filter(([name]) => !CUSTOM_MODULE_KEYS.has(name) || scanPhaseSet.has(name))
        .map(([name, meta], i) => ({
          name, display: meta.display, num: i + 1,
          status: "pending",
          tools: meta.tools.map(t => ({ name: t, done: false, success: true, output: "" })),
          expanded: false,
        }))
    );
  }, [scan?.phases?.join(",")]); // re-run when phases list changes (scan loads)

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
  }, [scanId]);

  // Auto-scroll terminal
  useEffect(() => {
    termRef.current?.scrollTo({ top: termRef.current.scrollHeight, behavior: "smooth" });
  }, [terminalLines]);

  function handleWsEvent(ev: WsEvent) {
    const ts = ev.timestamp ? new Date(ev.timestamp * 1000).toLocaleTimeString() : "";

    switch (ev.type) {
      case "scan_start":
        addTermLine(`[${ts}] ▶ Scan gestart — target: ${ev.message ?? ""}`, "text-green-400");
        break;

      case "phase_start":
        addTermLine(`[${ts}] ═══ ${ev.display ?? ev.phase} ═══`, "text-cyan-400");
        setPhases(prev => prev.map(p =>
          p.name === ev.phase ? { ...p, status: "running", expanded: true } : p
        ));
        break;

      case "phase_skip":
        addTermLine(`[${ts}] ⊘ ${ev.phase} overgeslagen: ${ev.reason ?? ""}`, "text-yellow-500");
        setPhases(prev => prev.map(p =>
          p.name === ev.phase ? { ...p, status: "skipped" } : p
        ));
        break;

      case "tool_start":
        addTermLine(`[${ts}]   ⏳ ${ev.tool}...`, "text-blue-400");
        break;

      case "tool_done":
        addTermLine(
          `[${ts}]   ${ev.success ? "✓" : "✗"} ${ev.tool} (${ev.duration ?? 0}s)`,
          ev.success ? "text-green-400" : "text-red-400"
        );
        if (ev.output) {
          // Show first 3 lines of output
          const preview = ev.output.split("\n").slice(0, 3).join("\n");
          if (preview.trim()) addTermLine(`         ${preview}`, "text-gray-400");
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
        addTermLine(`[${ts}] ✓ Scan voltooid — risicoscore: ${ev.risk_score}/100 (${ev.risk_level})`, "text-green-300");
        addTermLine(`         Bevindingen: ${ev.findings ?? 0} (${ev.critical ?? 0} kritiek, ${ev.high ?? 0} hoog)`, "text-green-300");
        queryClient.invalidateQueries({ queryKey: ["scan", scanId] });
        queryClient.invalidateQueries({ queryKey: ["scan-report", scanId] });
        setTab("report");
        break;

      case "error":
        addTermLine(`[${ts}] ✗ FOUT: ${ev.message ?? "onbekende fout"}`, "text-red-400");
        break;
    }
  }

  function addTermLine(line: string, _color: string = "") {
    setTerminalLines(prev => [...prev.slice(-500), line]); // max 500 lines
  }

  if (isLoading) {
    return <div className="text-center py-16 text-muted-foreground">Laden...</div>;
  }
  if (!scan) {
    return <div className="text-center py-16 text-muted-foreground">Scan niet gevonden</div>;
  }

  const findings = report?.report_data?.findings ?? report?.findings ?? [];
  const aiReport = report?.report_data ?? report ?? null;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/scans">
          <Button variant="ghost" size="sm" className="text-[12px] uppercase">
            <ArrowLeft className="mr-2 h-3.5 w-3.5" />Terug
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-[18px] font-bold flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />Scan Details
          </h1>
          <p className="text-[12px] text-muted-foreground">
            {scan.scan_type?.replace("_"," ")} &bull; aangemaakt {new Date(scan.created_at).toLocaleString()}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {wsConnected && (
            <span className="flex items-center gap-1 text-[11px] text-green-500">
              <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />Live
            </span>
          )}
          {scan.status === "pending" && (
            <Button size="sm" onClick={() => startMutation.mutate()} disabled={startMutation.isPending} className="text-[12px]">
              <Play className="mr-1.5 h-3.5 w-3.5" />Scan Starten
            </Button>
          )}
          {scan.status === "running" && (
            <Button size="sm" variant="destructive" onClick={() => cancelMutation.mutate()} className="text-[12px]">
              <StopCircle className="mr-1.5 h-3.5 w-3.5" />Stoppen
            </Button>
          )}
          {scan.status === "completed" && (
            <>
              <Button size="sm" variant="outline" className="text-[12px]"
                onClick={async () => {
                  const res = await reportsApi.downloadJson(scanId);
                  const url = URL.createObjectURL(new Blob([res.data]));
                  Object.assign(document.createElement("a"), {href:url, download:`scan-${scanId}.json`}).click();
                  URL.revokeObjectURL(url);
                }}>
                <FileText className="mr-1.5 h-3.5 w-3.5" />JSON
              </Button>
              <Button size="sm" variant="outline" className="text-[12px]"
                onClick={async () => {
                  const res = await reportsApi.downloadPdf(scanId);
                  const url = URL.createObjectURL(new Blob([res.data]));
                  Object.assign(document.createElement("a"), {href:url, download:`scan-${scanId}.pdf`}).click();
                  URL.revokeObjectURL(url);
                }}>
                <Download className="mr-1.5 h-3.5 w-3.5" />PDF
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Status row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Status", value: <StatusBadge status={scan.status} /> },
          { label: "Voortgang", value: <span className="text-lg font-bold">{scan.progress}%</span> },
          { label: "Huidige fase", value: <span className="text-sm capitalize">{scan.current_phase?.replace("_"," ") ?? "—"}</span> },
          { label: "Bevindingen", value: <FindingBadges scan={scan} /> },
        ].map(({ label, value }) => (
          <Card key={label}>
            <CardContent className="pt-4 pb-3">
              <p className="text-[11px] text-muted-foreground uppercase tracking-wider mb-1">{label}</p>
              {value}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Progress bar */}
      <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
        <div
          className="h-full bg-primary transition-all duration-700"
          style={{ width: `${scan.progress}%` }}
        />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {[
          { key: "live",     label: "Live Output" },
          { key: "findings", label: `Bevindingen (${findings.length})` },
          { key: "report",   label: "AI Rapport" },
        ].map(t => (
          <button key={t.key}
            onClick={() => setTab(t.key as any)}
            className={`px-4 py-2 text-[12px] font-medium border-b-2 transition-colors ${
              tab === t.key
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Tab: Live Output ── */}
      {tab === "live" && (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          {/* Phase sidebar */}
          <div className="lg:col-span-2 space-y-1.5">
            {phases.map(phase => (
              <div key={phase.name}
                className={`rounded-lg border transition-colors ${
                  phase.status === "running" ? "border-blue-500/50 bg-blue-500/5" :
                  phase.status === "done"    ? "border-green-500/30 bg-green-500/5" :
                  phase.status === "skipped" ? "border-yellow-500/20 opacity-50" :
                  "border-border"
                }`}>
                <button
                  onClick={() => setPhases(prev => prev.map(p => p.name === phase.name ? {...p, expanded: !p.expanded} : p))}
                  className="w-full flex items-center gap-2 px-3 py-2.5 text-left">
                  <PhaseIcon status={phase.status} />
                  <span className="flex-1 text-[12px] font-medium">{phase.display}</span>
                  {phase.expanded ? <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" /> : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
                </button>
                {phase.expanded && (
                  <div className="px-3 pb-2 space-y-1">
                    {phase.tools.map(tool => (
                      <div key={tool.name} className="flex items-center gap-2 text-[11px]">
                        {tool.done
                          ? tool.success
                            ? <CheckCircle className="h-3 w-3 text-green-500 shrink-0" />
                            : <AlertTriangle className="h-3 w-3 text-red-400 shrink-0" />
                          : phase.status === "running"
                            ? <Cpu className="h-3 w-3 text-blue-400 animate-pulse shrink-0" />
                            : <Circle className="h-3 w-3 text-muted-foreground shrink-0" />
                        }
                        <span className="font-mono">{tool.name}</span>
                        {tool.duration && <span className="text-muted-foreground">{tool.duration}s</span>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Terminal */}
          <div className="lg:col-span-3 rounded-lg border bg-black overflow-hidden">
            <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-800 bg-gray-900">
              <Terminal className="h-3.5 w-3.5 text-green-400" />
              <span className="text-[11px] text-gray-400 font-mono">scan output</span>
              {wsConnected && <span className="ml-auto text-[10px] text-green-500">● live</span>}
            </div>
            <div ref={termRef} className="h-96 overflow-y-auto p-3 space-y-0.5 font-mono text-[11px]">
              {terminalLines.length === 0 ? (
                <p className="text-gray-600">Wachten op scan output...</p>
              ) : (
                terminalLines.map((line, i) => (
                  <div key={i} className={`leading-5 whitespace-pre-wrap break-all ${
                    line.includes("✓") ? "text-green-400" :
                    line.includes("✗") ? "text-red-400" :
                    line.includes("═══") ? "text-cyan-400" :
                    line.includes("⏳") ? "text-blue-400" :
                    line.includes("⊘") ? "text-yellow-500" :
                    "text-gray-300"
                  }`}>{line}</div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Findings ── */}
      {tab === "findings" && (
        <div className="space-y-3">
          {findings.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground text-[13px]">
              {scan.status === "completed"
                ? "Geen bevindingen — je target lijkt veilig!"
                : "Bevindingen verschijnen hier zodra de scan klaar is."}
            </div>
          ) : (
            findings.map((f: any, i: number) => (
              <Card key={i}>
                <CardContent className="pt-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${SEVERITY_COLORS[f.severity] ?? "bg-gray-500 text-white"}`}>
                          {f.severity}
                        </span>
                        {f.cvss && (
                          <span className="text-[10px] font-mono bg-secondary px-2 py-0.5 rounded">
                            CVSS {f.cvss}
                          </span>
                        )}
                        {f.cve && (
                          <span className="text-[10px] font-mono text-blue-400">{f.cve}</span>
                        )}
                        {f.owasp && (
                          <span className="text-[10px] text-muted-foreground">{f.owasp}</span>
                        )}
                      </div>
                      <h3 className="font-semibold text-[14px] mt-1.5">{f.title}</h3>
                      <p className="text-[12px] text-muted-foreground mt-1">{f.description}</p>
                    </div>
                    <div className="text-[10px] text-muted-foreground text-right shrink-0">
                      <div className="font-mono">{f.tool}</div>
                      <div>{f.phase}</div>
                    </div>
                  </div>
                  {f.recommendation && (
                    <div className="mt-3 border-t pt-3">
                      <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider mb-1">Aanbeveling</p>
                      <p className="text-[12px]">{f.recommendation}</p>
                    </div>
                  )}
                  {f.impact && (
                    <div className="mt-2">
                      <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider mb-1">Impact</p>
                      <p className="text-[12px]">{f.impact}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {/* ── Tab: AI Report ── */}
      {tab === "report" && (
        <div className="space-y-5">
          {!aiReport ? (
            <div className="text-center py-12 text-muted-foreground text-[13px]">
              {scan.status === "completed"
                ? "Rapport laden..."
                : "Het AI-rapport is beschikbaar nadat de scan en analyse zijn voltooid."}
            </div>
          ) : (
            <>
              {/* Risk gauge */}
              <Card>
                <CardContent className="pt-5">
                  <div className="flex items-center gap-6">
                    <div className="text-center">
                      <div className={`text-5xl font-black ${
                        (aiReport.risk_score ?? 0) >= 70 ? "text-red-500" :
                        (aiReport.risk_score ?? 0) >= 40 ? "text-orange-500" :
                        (aiReport.risk_score ?? 0) >= 20 ? "text-yellow-500" :
                        "text-green-500"
                      }`}>
                        {aiReport.risk_score ?? "—"}
                      </div>
                      <div className="text-[11px] text-muted-foreground uppercase tracking-wider">Risicoscore</div>
                      <div className={`text-[12px] font-bold mt-1 ${
                        (aiReport.risk_level ?? "") === "CRITICAL" ? "text-red-500" :
                        (aiReport.risk_level ?? "") === "HIGH"     ? "text-orange-500" :
                        (aiReport.risk_level ?? "") === "MEDIUM"   ? "text-yellow-500" :
                        "text-green-500"
                      }`}>{aiReport.risk_level ?? ""}</div>
                    </div>
                    <div className="flex-1 grid grid-cols-5 gap-2 text-center">
                      {[
                        { label: "Kritiek", count: scan.critical_count, color: "text-red-500" },
                        { label: "Hoog",    count: scan.high_count,     color: "text-orange-500" },
                        { label: "Gemiddeld", count: scan.medium_count, color: "text-yellow-500" },
                        { label: "Laag",    count: scan.low_count,      color: "text-blue-500" },
                        { label: "Info",    count: scan.info_count,     color: "text-gray-500" },
                      ].map(b => (
                        <div key={b.label}>
                          <div className={`text-2xl font-bold ${b.color}`}>{b.count ?? 0}</div>
                          <div className="text-[10px] text-muted-foreground">{b.label}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Management summary */}
              {aiReport.management_summary && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-[12px] uppercase tracking-wider text-muted-foreground font-normal">Managementsamenvatting</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-[13px] leading-relaxed">{aiReport.management_summary}</p>
                  </CardContent>
                </Card>
              )}

              {/* Technical summary */}
              {aiReport.technical_summary && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-[12px] uppercase tracking-wider text-muted-foreground font-normal">Technische Samenvatting</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-[13px] leading-relaxed">{aiReport.technical_summary}</p>
                  </CardContent>
                </Card>
              )}

              {/* Remediation roadmap */}
              {aiReport.remediation_roadmap && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-[12px] uppercase tracking-wider text-muted-foreground font-normal">Herstelplan</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {[
                      { key: "quick_wins", label: "Quick Wins (< 1 dag)", color: "border-l-green-500" },
                      { key: "short_term", label: "Korte termijn (< 1 week)", color: "border-l-yellow-500" },
                      { key: "long_term",  label: "Lange termijn (< 1 maand)", color: "border-l-blue-500" },
                    ].map(({ key, label, color }) => {
                      const items = aiReport.remediation_roadmap[key] ?? [];
                      if (!items.length) return null;
                      return (
                        <div key={key}>
                          <p className="text-[11px] font-semibold uppercase tracking-wider mb-2">{label}</p>
                          <div className="space-y-2">
                            {items.map((item: any, i: number) => (
                              <div key={i} className={`border-l-2 ${color} pl-3 py-1`}>
                                <p className="text-[13px] font-medium">{item.title}</p>
                                {item.effort && <p className="text-[11px] text-muted-foreground">{item.effort}</p>}
                                {item.steps?.length > 0 && (
                                  <ul className="mt-1 space-y-0.5">
                                    {item.steps.map((s: string, j: number) => (
                                      <li key={j} className="text-[12px] text-muted-foreground">• {s}</li>
                                    ))}
                                  </ul>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </CardContent>
                </Card>
              )}

              {/* Compliance mapping */}
              {aiReport.compliance_mapping && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-[12px] uppercase tracking-wider text-muted-foreground font-normal">Compliance Mapping</CardTitle>
                  </CardHeader>
                  <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {[
                      { key: "owasp_top10", label: "OWASP Top 10" },
                      { key: "iso27001",    label: "ISO 27001" },
                      { key: "nis2",        label: "NIS2" },
                    ].map(({ key, label }) => {
                      const items: string[] = aiReport.compliance_mapping[key] ?? [];
                      return (
                        <div key={key}>
                          <p className="text-[11px] font-semibold uppercase tracking-wider mb-2">{label}</p>
                          {items.length === 0
                            ? <p className="text-[12px] text-muted-foreground">—</p>
                            : <ul className="space-y-1">
                                {items.map((s, i) => <li key={i} className="text-[12px]">• {s}</li>)}
                              </ul>
                          }
                        </div>
                      );
                    })}
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ── Helper components ─────────────────────────────────────────────────────────

function PhaseIcon({ status }: { status: PhaseState["status"] }) {
  switch (status) {
    case "done":    return <CheckCircle className="h-4 w-4 text-green-500 shrink-0" />;
    case "running": return <Activity className="h-4 w-4 text-blue-400 animate-pulse shrink-0" />;
    case "skipped": return <Circle className="h-4 w-4 text-yellow-500/50 shrink-0" />;
    case "failed":  return <AlertTriangle className="h-4 w-4 text-red-400 shrink-0" />;
    default:        return <Circle className="h-4 w-4 text-muted-foreground/40 shrink-0" />;
  }
}

function StatusBadge({ status }: { status: string }) {
  const cfg: Record<string, { cls: string; icon: React.ReactNode }> = {
    completed: { cls: "text-green-500 border-green-500", icon: <CheckCircle className="mr-1 h-3 w-3" /> },
    running:   { cls: "text-blue-500 border-blue-500",  icon: <Activity className="mr-1 h-3 w-3 animate-pulse" /> },
    analyzing: { cls: "text-purple-500 border-purple-500", icon: <Activity className="mr-1 h-3 w-3 animate-pulse" /> },
    pending:   { cls: "text-yellow-500 border-yellow-500", icon: <Clock className="mr-1 h-3 w-3" /> },
    failed:    { cls: "text-red-500 border-red-500",    icon: <AlertTriangle className="mr-1 h-3 w-3" /> },
  };
  const c = cfg[status] ?? { cls: "", icon: <Clock className="mr-1 h-3 w-3" /> };
  return (
    <Badge variant="outline" className={`flex items-center w-fit text-[12px] ${c.cls}`}>
      {c.icon}{status.replace("_"," ")}
    </Badge>
  );
}

function FindingBadges({ scan }: { scan: any }) {
  const counts = [
    { v: scan.critical_count, cls: "bg-red-600 text-white" },
    { v: scan.high_count,     cls: "bg-orange-500 text-white" },
    { v: scan.medium_count,   cls: "bg-yellow-500 text-black" },
    { v: scan.low_count,      cls: "bg-blue-500 text-white" },
  ].filter(c => c.v > 0);
  if (!counts.length) return <span className="text-muted-foreground text-sm">—</span>;
  return (
    <div className="flex gap-1 flex-wrap">
      {counts.map((c, i) => (
        <span key={i} className={`text-[11px] font-bold px-1.5 py-0.5 rounded ${c.cls}`}>{c.v}</span>
      ))}
    </div>
  );
}
