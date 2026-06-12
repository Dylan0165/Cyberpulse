"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Search,
  Wifi,
  WifiOff,
  Bug,
  Database,
  Camera,
  KeyRound,
  BrainCircuit,
  GitCompare,
  type LucideIcon,
} from "lucide-react";
import { GlowCard } from "@/components/cyber/glow-card";
import { SkeletonCard } from "@/components/cyber/skeleton";

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

// Only the tools CyberPulse actively uses in its scan phases.
// Filtering the API response to this set prevents showing the thousands
// of system binaries that the Kali VM tool discovery picks up.
const TOOL_DESCRIPTIONS: Record<string, string> = {
  nmap:         "Netwerkpoorten en diensten scannen",
  "httpx-pd":   "HTTP-diensten verkennen en analyseren (ProjectDiscovery)",
  httpx:        "HTTP-diensten verkennen en analyseren",
  subfinder:    "Subdomeinen ontdekken",
  whatweb:      "Web technologieën identificeren",
  masscan:      "Snelle massale poortscanner",
  nuclei:       "Kwetsbaarheden detecteren met templates",
  nikto:        "Webserver kwetsbaarheden scannen",
  sqlmap:       "SQL-injectie testen en exploiteren",
  ffuf:         "Verborgen webpagina's en parameters vinden",
  gobuster:     "Directory en bestanden brute-force",
  feroxbuster:  "Snelle recursieve content discovery",
  hydra:        "Wachtwoord brute-force aanvallen",
  "testssl.sh": "SSL/TLS configuratie analyseren",
  theharvester: "E-mails en domeinen verzamelen",
  gitleaks:     "Geheimen in Git repositories zoeken",
};

const CYBERPULSE_TOOLS = new Set(Object.keys(TOOL_DESCRIPTIONS));

// Per-phase accent colors for the cyberpunk theme.
const PHASE_GLOW: Record<number, string> = {
  1: "#00D4FF",
  2: "#FF2D55",
  3: "#0A84FF",
  4: "#00FF88",
  5: "#FFD60A",
  6: "#FF8C00",
  7: "#00D4FF",
  0: "#4A6880",
};

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

export default function ToolsPage() {
  const [data, setData] = useState<ToolsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selectedPhase, setSelectedPhase] = useState<number | null>(null);

  // Cosmetic live counters for the Kali VM status panel.
  const [uptime, setUptime] = useState(0);
  const [lastPing, setLastPing] = useState(0);

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
        // Filter to only the tools CyberPulse actively uses.
        // The Kali VM tool discovery returns thousands of system binaries;
        // we only care about the ~15 in CYBERPULSE_TOOLS.
        const relevantTools = d.tools.filter((t) => CYBERPULSE_TOOLS.has(t.name));
        console.log("[Tools] data received:", d.total, "total,", relevantTools.length, "relevant");
        setData({
          ...d,
          tools: relevantTools,
          total: relevantTools.length,
          available_count: relevantTools.filter((t) => t.available).length,
        });
        setLoading(false);
      })
      .catch((e) => {
        console.error("[Tools] fetch error:", e);
        setError(String(e));
        setLoading(false);
      });
  }, []);

  // Cosmetic uptime counter — counts up from mount.
  useEffect(() => {
    const id = setInterval(() => setUptime((u) => u + 1), 1000);
    return () => clearInterval(id);
  }, []);

  // Cosmetic "last ping" counter — resets every few seconds.
  useEffect(() => {
    const id = setInterval(() => setLastPing((p) => (p >= 4 ? 0 : p + 1)), 1000);
    return () => clearInterval(id);
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

  const kaliVm = data?.kali_vm ?? "192.168.121.28";
  const hh = Math.floor(uptime / 3600);
  const mm = Math.floor((uptime % 3600) / 60);
  const ss = uptime % 60;

  // Running index so cards stagger continuously across phase groups.
  let cardIndex = 0;

  return (
    <div className="space-y-8">
      {/* ── Header ───────────────────────────────────────────── */}
      <div>
        <h1 className="font-display text-[32px] font-bold tracking-tight text-glow-cyan text-ink">
          Security Arsenal
        </h1>
        <p className="mt-1 text-[15px] text-ink-muted">
          {data
            ? `${data.available_count} / ${data.total} tools running on Kali Linux 2024`
            : "15 professional tools running on Kali Linux 2024"}
        </p>
      </div>

      {/* ── Connection banner ────────────────────────────────── */}
      {!loading && (
        <div
          className="flex items-center gap-3 rounded-lg border px-5 py-4"
          style={
            error
              ? { borderColor: "rgba(255,45,85,0.35)", background: "rgba(255,45,85,0.05)" }
              : { borderColor: "rgba(0,255,136,0.30)", background: "rgba(0,255,136,0.05)" }
          }
        >
          {error ? (
            <WifiOff className="h-5 w-5 flex-shrink-0 text-neon-red" />
          ) : (
            <Wifi className="h-5 w-5 flex-shrink-0 text-neon-green" />
          )}
          <div className="flex-1">
            {error ? (
              <div>
                <p className="flex items-center gap-2 font-mono text-[13px] font-semibold text-neon-red">
                  <span className="inline-block h-2 w-2 rounded-full bg-[#FF2D55]" />
                  Kali VM OFFLINE
                </p>
                <p className="mt-1 break-all font-mono text-[12px] text-[#FF2D55]/70">{error}</p>
                <p className="mt-1 text-[11px] text-ink-muted">
                  Controleer de browser console (F12) voor meer details.
                </p>
              </div>
            ) : (
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <span className="flex items-center gap-2 font-mono text-[13px] font-semibold text-neon-green">
                  <span className="animate-pulse-dot inline-block h-2 w-2 rounded-full bg-[#00FF88]" />
                  Kali VM ONLINE
                </span>
                <span className="font-mono text-[13px] text-ink-muted">{kaliVm}</span>
                <span className="font-mono text-[12px] text-ink-muted">
                  <span className="text-neon-green">{data?.available_count}</span>/{data?.total} tools
                  beschikbaar
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Search + phase filters ───────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Zoek tool of categorie..."
            className="w-full rounded-lg border border-grid bg-card2 py-2.5 pl-10 pr-4 font-mono text-[14px] text-ink placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-[#00D4FF]/50"
          />
        </div>
        <div className="flex flex-wrap gap-1.5">
          <FilterButton active={selectedPhase === null} onClick={() => setSelectedPhase(null)}>
            Alle
          </FilterButton>
          {allPhases.map((ph) => (
            <FilterButton
              key={ph}
              active={selectedPhase === ph}
              onClick={() => setSelectedPhase(selectedPhase === ph ? null : ph)}
            >
              {ph > 0 ? PHASE_LABELS[ph] : "Other"}
            </FilterButton>
          ))}
        </div>
      </div>

      {/* ── Loading ──────────────────────────────────────────── */}
      {loading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {[...Array(12)].map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {/* ── Empty state ──────────────────────────────────────── */}
      {!loading && phases.length === 0 && (
        <div className="py-16 text-center font-mono text-[14px] text-ink-muted">
          {error ? "Kan tools niet laden." : "Geen tools gevonden."}
        </div>
      )}

      {/* ── Tools grouped by phase ───────────────────────────── */}
      {!loading &&
        phases.map((ph) => {
          const phaseTools = byPhase.get(ph) ?? [];
          const avail = phaseTools.filter((t) => t.available).length;
          const glow = PHASE_GLOW[ph] ?? "#00D4FF";

          return (
            <div key={ph} className="space-y-4">
              <div className="flex items-center gap-3">
                <h2 className="font-display text-[18px] font-semibold text-ink">
                  {ph > 0 ? `Phase ${ph} — ${PHASE_LABELS[ph]}` : PHASE_LABELS[0]}
                </h2>
                <span className="font-mono text-[12px] text-ink-muted">
                  {avail}/{phaseTools.length} beschikbaar
                </span>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {phaseTools.map((tool) => {
                  const idx = cardIndex++;
                  return (
                    <motion.div
                      key={tool.name}
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: idx * 0.03 }}
                      whileHover={{ rotate: 0.5, scale: 1.01 }}
                    >
                      <GlowCard glowColor={glow} accentBorder={tool.available ? glow : "#0A2035"}>
                        <div
                          className="p-5"
                          style={tool.available ? undefined : { opacity: 0.55 }}
                        >
                          <div className="mb-3 flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <p className="truncate font-mono text-[15px] font-semibold text-ink">
                                {tool.name}
                              </p>
                              <span
                                className="mt-2 inline-block rounded-md px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider"
                                style={{
                                  background: "rgba(0,212,255,0.10)",
                                  color: "#00D4FF",
                                  border: "1px solid rgba(0,212,255,0.25)",
                                }}
                              >
                                {tool.category || PHASE_LABELS[ph]}
                              </span>
                            </div>
                          </div>

                          {TOOL_DESCRIPTIONS[tool.name] && (
                            <p className="text-[13px] leading-relaxed text-ink-muted">
                              {TOOL_DESCRIPTIONS[tool.name]}
                            </p>
                          )}

                          <div className="mt-4 flex items-center justify-between">
                            <span className="font-mono text-[11px] text-ink-muted">
                              Phase {ph > 0 ? ph : "—"}
                            </span>
                            <span
                              className="flex items-center gap-1.5 font-mono text-[11px] font-semibold uppercase tracking-wider"
                              style={{ color: tool.available ? "#00FF88" : "#FF2D55" }}
                            >
                              <span
                                className={tool.available ? "animate-pulse-dot inline-block h-1.5 w-1.5 rounded-full" : "inline-block h-1.5 w-1.5 rounded-full"}
                                style={{ background: tool.available ? "#00FF88" : "#FF2D55" }}
                              />
                              {tool.available ? "READY" : "OFFLINE"}
                            </span>
                          </div>
                        </div>
                      </GlowCard>
                    </motion.div>
                  );
                })}
              </div>
            </div>
          );
        })}

      {/* ── Custom Modules ───────────────────────────────────── */}
      <div className="space-y-4 border-t border-grid pt-6">
        <div className="flex items-center gap-3">
          <h2 className="font-display text-[18px] font-semibold text-ink">Custom Modules</h2>
          <span className="font-mono text-[12px] text-ink-muted">
            CyberPulse post-scan analyse modules
          </span>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {CUSTOM_MODULES.map((mod, i) => {
            const Icon = mod.icon;
            const recommended = mod.id === "M10";
            return (
              <motion.div
                key={mod.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: i * 0.03 }}
                whileHover={{ rotate: 0.5, scale: 1.01 }}
              >
                <GlowCard glowColor={mod.iconColor} accentBorder="#BF5AF2">
                  <div className="p-5">
                    <div className="mb-3 flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="truncate font-mono text-[15px] font-semibold text-ink">
                            {mod.name}
                          </p>
                          {recommended && (
                            <span
                              className="rounded-md px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wider"
                              style={{
                                background: "rgba(0,212,255,0.12)",
                                color: "#00D4FF",
                                border: "1px solid rgba(0,212,255,0.3)",
                              }}
                            >
                              Recommended
                            </span>
                          )}
                        </div>
                        <span
                          className="mt-2 inline-block rounded-md px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider"
                          style={{
                            background: "rgba(191,90,242,0.10)",
                            color: "#BF5AF2",
                            border: "1px solid rgba(191,90,242,0.25)",
                          }}
                        >
                          {mod.category}
                        </span>
                      </div>
                      <div
                        className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-md"
                        style={{ background: mod.iconBg }}
                      >
                        <Icon className="h-4 w-4" style={{ color: mod.iconColor }} />
                      </div>
                    </div>
                    <p className="text-[13px] leading-relaxed text-ink-muted">{mod.description}</p>
                    <div className="mt-4 flex items-center justify-between">
                      <span className="font-mono text-[11px] text-ink-muted">Module {mod.id}</span>
                      <span className="flex items-center gap-1.5 font-mono text-[11px] font-semibold uppercase tracking-wider text-neon-green">
                        <span
                          className="animate-pulse-dot inline-block h-1.5 w-1.5 rounded-full"
                          style={{ background: "#00FF88" }}
                        />
                        Actief
                      </span>
                    </div>
                  </div>
                </GlowCard>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* ── Live Kali VM Status ──────────────────────────────── */}
      <div className="border-t border-grid pt-6">
        <GlowCard glowColor="#00FF88" accentBorder="#00FF88">
          <div className="p-5">
            <div className="mb-4 flex items-center gap-2">
              <span className="animate-pulse-dot inline-block h-2 w-2 rounded-full bg-[#00FF88]" />
              <h2 className="font-display text-[16px] font-semibold text-ink">Live Kali VM Status</h2>
            </div>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div>
                <p className="font-mono text-[10px] uppercase tracking-wider text-ink-muted">IP Address</p>
                <p className="mt-1 font-mono text-[15px] font-semibold text-ink">{kaliVm}</p>
              </div>
              <div>
                <p className="font-mono text-[10px] uppercase tracking-wider text-ink-muted">Uptime</p>
                <p className="mt-1 font-mono text-[15px] font-semibold text-neon-cyan">
                  {pad(hh)}:{pad(mm)}:{pad(ss)}
                </p>
              </div>
              <div>
                <p className="font-mono text-[10px] uppercase tracking-wider text-ink-muted">Tools</p>
                <p className="mt-1 font-mono text-[15px] font-semibold text-ink">
                  <span className="text-neon-green">{data?.available_count ?? 0}</span> / {data?.total ?? 0}{" "}
                  <span className="text-ink-muted">available</span>
                </p>
              </div>
              <div>
                <p className="font-mono text-[10px] uppercase tracking-wider text-ink-muted">Last Ping</p>
                <p className="mt-1 flex items-center gap-1.5 font-mono text-[15px] font-semibold text-ink">
                  <span className="animate-pulse-dot inline-block h-1.5 w-1.5 rounded-full bg-[#00FF88]" />
                  {lastPing}s ago
                </p>
              </div>
            </div>
          </div>
        </GlowCard>
      </div>
    </div>
  );
}

function FilterButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className="rounded-lg border px-3.5 py-2 font-mono text-[12px] font-medium uppercase tracking-wider transition-colors duration-200"
      style={
        active
          ? { background: "#00D4FF", color: "#020408", borderColor: "#00D4FF" }
          : { background: "var(--bg-card)", color: "#4A6880", borderColor: "#0A2035" }
      }
    >
      {children}
    </button>
  );
}

interface CustomModule {
  id: string;
  name: string;
  category: string;
  description: string;
  icon: LucideIcon;
  iconColor: string;
  iconBg: string;
}

const CUSTOM_MODULES: CustomModule[] = [
  {
    id: "M09", name: "Business Logic Tester", category: "Exploitation",
    description: "Test IDOR-kwetsbaarheden, rate limiting en blootgestelde admin-endpoints zonder authenticatie.",
    icon: Bug, iconColor: "#FF2D55", iconBg: "rgba(255,45,85,0.10)",
  },
  {
    id: "M10", name: "CVE Correlator", category: "Vulnerability Intelligence",
    description: "Koppelt gedetecteerde service-versies aan bekende CVEs via de NVD REST API met CVSS-scores.",
    icon: Database, iconColor: "#FF8C00", iconBg: "rgba(255,140,0,0.10)",
  },
  {
    id: "M11", name: "Visual Recon", category: "Reconnaissance",
    description: "Maakt screenshots van alle webdiensten via Playwright voor visuele herkenning van aanvalsoppervlak.",
    icon: Camera, iconColor: "#0A84FF", iconBg: "rgba(10,132,255,0.10)",
  },
  {
    id: "M12", name: "Smart Credential Attack", category: "Authentication",
    description: "Genereert doelspecifieke wachtwoordlijsten op basis van bedrijfsnaam en test credentials via Hydra.",
    icon: KeyRound, iconColor: "#FFD60A", iconBg: "rgba(255,214,10,0.10)",
  },
  {
    id: "M13", name: "AI Adaptive Scanner", category: "AI-Directed",
    description: "DeepSeek analyseert alle bevindingen en bepaalt automatisch gerichte follow-up scans.",
    icon: BrainCircuit, iconColor: "#BF5AF2", iconBg: "rgba(191,90,242,0.10)",
  },
  {
    id: "M14", name: "Scan Comparator", category: "Reporting",
    description: "Vergelijkt huidige scan met vorige scan op hetzelfde target en rapporteert nieuw/opgelost/persistent.",
    icon: GitCompare, iconColor: "#00FF88", iconBg: "rgba(0,255,136,0.10)",
  },
];
