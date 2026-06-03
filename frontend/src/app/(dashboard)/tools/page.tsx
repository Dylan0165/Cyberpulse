"use client";

import { useState, useEffect } from "react";
import { Loader2, Search, CheckCircle2, XCircle, Wifi, WifiOff } from "lucide-react";

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

const PHASE_COLORS: Record<number, string> = {
  1: "text-blue-400 bg-blue-400/10 border-blue-400/20",
  2: "text-orange-400 bg-orange-400/10 border-orange-400/20",
  3: "text-purple-400 bg-purple-400/10 border-purple-400/20",
  4: "text-cyan-400 bg-cyan-400/10 border-cyan-400/20",
  5: "text-yellow-400 bg-yellow-400/10 border-yellow-400/20",
  6: "text-green-400 bg-green-400/10 border-green-400/20",
  7: "text-pink-400 bg-pink-400/10 border-pink-400/20",
  0: "text-muted-foreground bg-muted border-border",
};

export default function ToolsPage() {
  const [data, setData] = useState<ToolsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selectedPhase, setSelectedPhase] = useState<number | null>(null);

  useEffect(() => {
    fetch("/api/tools/available")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d: ToolsResponse) => {
        setData(d);
        setLoading(false);
      })
      .catch((e) => {
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-5 w-5 animate-spin text-primary mr-3" />
        <span className="text-sm text-muted-foreground">Verbinding met Kali VM...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Kali Tools</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Beveiligingstools beschikbaar op de Kali VM
          </p>
        </div>
      </div>

      {/* Connection banner */}
      <div
        className={`flex items-center gap-3 rounded-lg border px-4 py-3 text-sm ${
          error
            ? "border-red-500/30 bg-red-500/5 text-red-400"
            : data
            ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-400"
            : "border-border bg-card text-muted-foreground"
        }`}
      >
        {error ? (
          <WifiOff className="h-4 w-4 flex-shrink-0" />
        ) : (
          <Wifi className="h-4 w-4 flex-shrink-0" />
        )}
        <span>
          {error
            ? `Kali VM niet bereikbaar — ${error}`
            : data
            ? `Kali VM verbonden · ${data.kali_vm} · `
            : "Verbinden..."}
          {data && (
            <strong>
              {data.available_count}/{data.total} tools beschikbaar
            </strong>
          )}
        </span>
      </div>

      {/* Search + Phase filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Zoek tool of categorie..."
            className="w-full rounded-md border border-border bg-card pl-9 pr-4 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
        <div className="flex gap-1.5 flex-wrap">
          <button
            onClick={() => setSelectedPhase(null)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium border transition-colors ${
              selectedPhase === null
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-card border-border text-muted-foreground hover:text-foreground hover:border-primary/50"
            }`}
          >
            Alle
          </button>
          {allPhases.map((ph) => (
            <button
              key={ph}
              onClick={() => setSelectedPhase(selectedPhase === ph ? null : ph)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium border transition-colors ${
                selectedPhase === ph
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-card border-border text-muted-foreground hover:text-foreground hover:border-primary/50"
              }`}
            >
              {ph > 0 ? `Phase ${ph}` : "Other"}
            </button>
          ))}
        </div>
      </div>

      {/* Tools per phase */}
      {phases.length === 0 && !loading && (
        <div className="text-center py-16 text-muted-foreground text-sm">
          {error ? "Kan tools niet laden." : "Geen tools gevonden."}
        </div>
      )}

      {phases.map((ph) => {
        const phaseTools = byPhase.get(ph) ?? [];
        const avail = phaseTools.filter((t) => t.available).length;
        const phaseColor = PHASE_COLORS[ph] ?? PHASE_COLORS[0];

        return (
          <div key={ph} className="space-y-3">
            {/* Phase header */}
            <div className="flex items-center gap-3">
              <span className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium ${phaseColor}`}>
                {ph > 0 ? `Phase ${ph}` : "Other"}
              </span>
              <h2 className="text-sm font-semibold text-foreground">
                {PHASE_LABELS[ph] ?? "Other"}
              </h2>
              <span className="text-xs text-muted-foreground">
                {avail}/{phaseTools.length} beschikbaar
              </span>
            </div>

            {/* Tool cards */}
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 gap-2">
              {phaseTools.map((tool) => (
                <div
                  key={tool.name}
                  className={`rounded-md border p-3 flex items-start gap-2.5 transition-colors ${
                    tool.available
                      ? "border-border bg-card hover:border-primary/40"
                      : "border-border bg-card opacity-40"
                  }`}
                >
                  <span
                    className={`mt-0.5 h-2 w-2 rounded-full flex-shrink-0 ${
                      tool.available ? "bg-emerald-500" : "bg-red-500"
                    }`}
                  />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-foreground leading-tight truncate">
                      {tool.name}
                    </p>
                    <p className="text-[11px] text-muted-foreground mt-0.5 truncate">
                      {tool.category}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
