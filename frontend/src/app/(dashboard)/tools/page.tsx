"use client";

import { useState, useEffect } from "react";
import { Search, Wifi, WifiOff, CheckCircle2, XCircle, Bug, Database, Camera, KeyRound, BrainCircuit, GitCompare } from "lucide-react";

interface KaliTool {
  name: string;
  available: boolean;
  phase: number;
  category: string;
}

interface ToolsResponse {
  tools: KaliTool[];
  total: number;
  available_count: number;
  kali_vm: string;
}

const PHASE_LABELS: Record<number, string> = {
  1: "Reconnaissance",
  2: "Vulnerability Scan",
  3: "Web Application",
  4: "Network",
  5: "Authentication",
  6: "SSL / TLS",
  7: "OSINT",
  0: "Other",
};

const TOOL_DESCRIPTIONS: Record<string, string> = {
  nmap: "Netwerkpoorten en diensten scannen",
  httpx: "HTTP-diensten verkennen en analyseren",
  subfinder: "Subdomeinen ontdekken",
  whatweb: "Web technologieën identificeren",
  masscan: "Snelle massale poortscanner",
  nuclei: "Kwetsbaarheden detecteren met templates",
  nikto: "Webserver kwetsbaarheden scannen",
  sqlmap: "SQL-injectie testen en exploiteren",
  ffuf: "Verborgen webpagina's en parameters vinden",
  gobuster: "Directory en bestanden brute-force",
  feroxbuster: "Snelle recursieve content discovery",
  hydra: "Wachtwoord brute-force aanvallen",
  "testssl.sh": "SSL/TLS configuratie analyseren",
  theharvester: "E-mails en domeinen verzamelen",
  gitleaks: "Geheimen in Git repositories zoeken",
};

export default function ToolsPage() {
  const [data, setData] = useState<ToolsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selectedPhase, setSelectedPhase] = useState<number | null>(null);

  useEffect(() => {
    console.log("[Tools] fetching /api/tools/available");
    fetch("/api/tools/available", { cache: "no-store" })
      .then((r) => {
        console.log("[Tools] response status:", r.status, r.statusText);
        if (!r.ok) {
          return r.text().then((body) => {
            throw new Error(`HTTP ${r.status} ${r.statusText} — body: ${body.slice(0, 200)}`);
          });
        }
        return r.json();
      })
      .then((d: ToolsResponse) => {
        console.log("[Tools] data received:", d.total, "tools,", d.available_count, "available");
        setData(d);
        setLoading(false);
      })
      .catch((e) => {
        console.error("[Tools] fetch error:", e);
        setError(String(e));
        setLoading(false);
      });
  }, []);

  const tools = data?.tools ?? [];
  const filtered = tools.filter((t) => {
    const q = search.toLowerCase();
    const matchSearch =
      !search ||
      t.name.toLowerCase().includes(q) ||
      t.category.toLowerCase().includes(q) ||
      (PHASE_LABELS[t.phase] ?? "").toLowerCase().includes(q);
    const matchPhase = selectedPhase === null || t.phase === selectedPhase;
    return matchSearch && matchPhase;
  });

  const byPhase = new Map<number, KaliTool[]>();
  filtered.forEach((t) => {
    if (!byPhase.has(t.phase)) byPhase.set(t.phase, []);
    byPhase.get(t.phase)!.push(t);
  });
  const phases = Array.from(byPhase.keys()).sort((a, b) => (a === 0 ? 1 : b === 0 ? -1 : a - b));
  const allPhases = Array.from(new Set(tools.map((t) => t.phase))).sort(
    (a, b) => (a === 0 ? 1 : b === 0 ? -1 : a - b)
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-[28px] font-bold" style={{ letterSpacing: "-0.03em" }}>
          Kali Tools
        </h1>
        <p className="text-[15px] text-muted-foreground mt-0.5">
          Beveiligingstools beschikbaar op de Kali VM
        </p>
      </div>

      {/* Connection banner */}
      {!loading && (
        <div
          className="flex items-center gap-3 rounded-2xl border px-5 py-4"
          style={
            error
              ? { borderColor: "rgba(255,59,48,0.3)", background: "rgba(255,59,48,0.04)" }
              : { borderColor: "rgba(52,199,89,0.3)", background: "rgba(52,199,89,0.04)" }
          }
        >
          {error ? (
            <WifiOff className="h-5 w-5 flex-shrink-0" style={{ color: "#ff3b30" }} />
          ) : (
            <Wifi className="h-5 w-5 flex-shrink-0" style={{ color: "#34c759" }} />
          )}
          <div className="flex-1">
            {error ? (
              <div>
                <p className="text-[14px] font-semibold" style={{ color: "#ff3b30" }}>
                  Kali VM niet bereikbaar
                </p>
                <p className="text-[12px] mt-1 font-mono break-all" style={{ color: "#ff3b30", opacity: 0.8 }}>
                  {error}
                </p>
                <p className="text-[11px] mt-1 text-muted-foreground">
                  Controleer de browser console (F12) voor meer details.
                </p>
              </div>
            ) : (
              <>
                <p className="text-[14px] font-semibold" style={{ color: "#1d1d1f" }}>
                  Kali VM verbonden
                  <span className="font-normal text-muted-foreground ml-2 font-mono text-[13px]">
                    {data?.kali_vm}
                  </span>
                </p>
                <p className="text-[13px] text-muted-foreground mt-0.5">
                  <span className="font-semibold" style={{ color: "#34c759" }}>
                    {data?.available_count}
                  </span>
                  /{data?.total} tools beschikbaar
                </p>
              </>
            )}
          </div>
        </div>
      )}

      {/* Search + filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Zoek tool of categorie..."
            className="w-full rounded-xl border border-border bg-card pl-10 pr-4 py-2.5 text-[14px] placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
        </div>
        <div className="flex gap-1.5 flex-wrap">
          <button
            onClick={() => setSelectedPhase(null)}
            className="rounded-xl px-3.5 py-2 text-[13px] font-medium border transition-colors"
            style={{
              background: selectedPhase === null ? "#0071e3" : "#fff",
              color: selectedPhase === null ? "#fff" : "#6e6e73",
              borderColor: selectedPhase === null ? "#0071e3" : "#e5e5ea",
            }}
          >
            Alle
          </button>
          {allPhases.map((ph) => (
            <button
              key={ph}
              onClick={() => setSelectedPhase(selectedPhase === ph ? null : ph)}
              className="rounded-xl px-3.5 py-2 text-[13px] font-medium border transition-colors"
              style={{
                background: selectedPhase === ph ? "#0071e3" : "#fff",
                color: selectedPhase === ph ? "#fff" : "#6e6e73",
                borderColor: selectedPhase === ph ? "#0071e3" : "#e5e5ea",
              }}
            >
              {ph > 0 ? PHASE_LABELS[ph] : "Other"}
            </button>
          ))}
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="grid grid-cols-3 gap-4">
          {[...Array(12)].map((_, i) => (
            <div key={i} className="rounded-2xl border border-border bg-card p-5 shadow-apple animate-pulse">
              <div className="h-4 w-24 rounded bg-muted mb-3" />
              <div className="h-3 w-16 rounded bg-muted mb-2" />
              <div className="h-3 w-full rounded bg-muted" />
            </div>
          ))}
        </div>
      )}

      {/* Tools per phase */}
      {!loading && phases.length === 0 && (
        <div className="text-center py-16 text-muted-foreground text-[14px]">
          {error ? "Kan tools niet laden." : "Geen tools gevonden."}
        </div>
      )}

      {!loading &&
        phases.map((ph) => {
          const phaseTools = byPhase.get(ph) ?? [];
          const avail = phaseTools.filter((t) => t.available).length;

          return (
            <div key={ph} className="space-y-3">
              {/* Phase header */}
              <div className="flex items-center gap-3">
                <h2 className="text-[17px] font-semibold">
                  {ph > 0 ? `Phase ${ph} — ${PHASE_LABELS[ph]}` : PHASE_LABELS[0]}
                </h2>
                <span className="text-[13px] text-muted-foreground">
                  {avail}/{phaseTools.length} beschikbaar
                </span>
              </div>

              {/* Cards grid */}
              <div className="grid grid-cols-3 gap-4">
                {phaseTools.map((tool) => (
                  <div
                    key={tool.name}
                    className="rounded-2xl border border-border bg-card p-5 shadow-apple hover:shadow-apple-md transition-shadow"
                    style={tool.available ? {} : { opacity: 0.5 }}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="min-w-0">
                        <p className="text-[15px] font-semibold truncate">{tool.name}</p>
                        <p className="text-[12px] text-muted-foreground mt-0.5">{tool.category}</p>
                      </div>
                      {tool.available ? (
                        <CheckCircle2 className="h-5 w-5 flex-shrink-0 mt-0.5" style={{ color: "#34c759" }} />
                      ) : (
                        <XCircle className="h-5 w-5 flex-shrink-0 mt-0.5" style={{ color: "#ff3b30" }} />
                      )}
                    </div>

                    {TOOL_DESCRIPTIONS[tool.name] && (
                      <p className="text-[13px] text-muted-foreground leading-relaxed">
                        {TOOL_DESCRIPTIONS[tool.name]}
                      </p>
                    )}

                    <div className="flex items-center justify-between mt-4">
                      <span
                        className="rounded-full px-2.5 py-1 text-[11px] font-semibold"
                        style={{ background: "rgba(0,113,227,0.08)", color: "#0071e3" }}
                      >
                        Phase {ph > 0 ? ph : "—"}
                      </span>
                      <span
                        className="text-[12px] font-medium"
                        style={{ color: tool.available ? "#34c759" : "#ff3b30" }}
                      >
                        {tool.available ? "Beschikbaar" : "Niet geïnstalleerd"}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}

      {/* ── Custom Modules ─────────────────────────────────────── */}
      <div className="space-y-3 pt-4" style={{ borderTop: "1px solid #e5e5ea" }}>
        <div className="flex items-center gap-3">
          <h2 className="text-[17px] font-semibold">Custom Modules</h2>
          <span className="text-[13px] text-muted-foreground">
            CyberPulse post-scan analyse modules
          </span>
        </div>
        <div className="grid grid-cols-3 gap-4">
          {CUSTOM_MODULES.map((mod) => (
            <div key={mod.id} className="rounded-2xl border border-border bg-card p-5 shadow-apple hover:shadow-apple-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div className="min-w-0">
                  <p className="text-[15px] font-semibold truncate">{mod.name}</p>
                  <p className="text-[12px] text-muted-foreground mt-0.5">{mod.category}</p>
                </div>
                <div className="h-9 w-9 rounded-xl flex items-center justify-center flex-shrink-0 ml-3"
                     style={{ background: mod.iconBg }}>
                  <mod.icon className="h-4 w-4" style={{ color: mod.iconColor }} />
                </div>
              </div>
              <p className="text-[13px] text-muted-foreground leading-relaxed">{mod.description}</p>
              <div className="flex items-center justify-between mt-4">
                <span className="rounded-full px-2.5 py-1 text-[11px] font-semibold"
                      style={{ background: "rgba(191,90,242,0.08)", color: "#bf5af2" }}>
                  Module {mod.id}
                </span>
                <span className="text-[12px] font-medium" style={{ color: "#34c759" }}>
                  Actief
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const CUSTOM_MODULES = [
  {
    id: "M09", name: "Business Logic Tester", category: "Exploitation",
    description: "Test IDOR-kwetsbaarheden, rate limiting en blootgestelde admin-endpoints zonder authenticatie.",
    icon: Bug, iconColor: "#ff3b30", iconBg: "rgba(255,59,48,0.08)",
  },
  {
    id: "M10", name: "CVE Correlator", category: "Vulnerability Intelligence",
    description: "Koppelt gedetecteerde service-versies aan bekende CVEs via de NVD REST API met CVSS-scores.",
    icon: Database, iconColor: "#ff9500", iconBg: "rgba(255,149,0,0.08)",
  },
  {
    id: "M11", name: "Visual Recon", category: "Reconnaissance",
    description: "Maakt screenshots van alle webdiensten via Playwright voor visuele herkenning van aanvalsoppervlak.",
    icon: Camera, iconColor: "#0071e3", iconBg: "rgba(0,113,227,0.08)",
  },
  {
    id: "M12", name: "Smart Credential Attack", category: "Authentication",
    description: "Genereert doelspecifieke wachtwoordlijsten op basis van bedrijfsnaam en test credentials via Hydra.",
    icon: KeyRound, iconColor: "#c69b00", iconBg: "rgba(255,204,0,0.10)",
  },
  {
    id: "M13", name: "AI Adaptive Scanner", category: "AI-Directed",
    description: "DeepSeek analyseert alle bevindingen en bepaalt automatisch gerichte follow-up scans.",
    icon: BrainCircuit, iconColor: "#bf5af2", iconBg: "rgba(191,90,242,0.08)",
  },
  {
    id: "M14", name: "Scan Comparator", category: "Reporting",
    description: "Vergelijkt huidige scan met vorige scan op hetzelfde target en rapporteert nieuw/opgelost/persistent.",
    icon: GitCompare, iconColor: "#34c759", iconBg: "rgba(52,199,89,0.08)",
  },
];
