"use client";

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/lib/api";
import Link from "next/link";
import { Search, Shield, ExternalLink, AlertTriangle, Loader2 } from "lucide-react";

interface CveResult {
  id: string;
  score: number;
  severity: string;
  description: string;
  service?: string;
  version?: string;
  port?: string;
  scan_id?: string;
}

export default function VulnerabilitiesPage() {
  const [search, setSearch] = useState("");
  const [cveSearch, setCveSearch] = useState("");
  const [cveData, setCveData] = useState<any | null>(null);
  const [cveLoading, setCveLoading] = useState(false);
  const [cveError, setCveError] = useState<string | null>(null);

  // Load CVE findings from completed scans
  const { data: scansData, isLoading } = useQuery({
    queryKey: ["scans-completed"],
    queryFn: () => dashboardApi.listScans(1, 50),
  });

  const cveFindings: CveResult[] = [];
  for (const scan of (scansData?.items ?? [])) {
    const findings = (scan as any).findings ?? [];
    for (const f of findings) {
      if (f.cve && f.cve.startsWith("CVE-")) {
        cveFindings.push({
          id: f.cve,
          score: f.cvss ?? 0,
          severity: f.severity ?? "MEDIUM",
          description: f.description ?? f.detail ?? "",
          service: f.service,
          version: f.version,
          port: f.port,
          scan_id: (scan as any).id,
        });
      }
    }
  }

  const filtered = cveFindings.filter((c) =>
    !search ||
    c.id.toLowerCase().includes(search.toLowerCase()) ||
    (c.service ?? "").toLowerCase().includes(search.toLowerCase()) ||
    (c.description ?? "").toLowerCase().includes(search.toLowerCase())
  );

  // CVE lookup via backend threat-intel endpoint
  const lookupCve = async () => {
    const id = cveSearch.trim().toUpperCase();
    if (!id.startsWith("CVE-")) return;
    setCveLoading(true);
    setCveError(null);
    setCveData(null);
    try {
      const r = await fetch(`/api/threat-intel/${id}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setCveData(await r.json());
    } catch (e) {
      setCveError(String(e));
    } finally {
      setCveLoading(false);
    }
  };

  const severityColor = (s: string) => {
    const m: Record<string, string> = {
      CRITICAL: "#ff3b30", HIGH: "#ff9500", MEDIUM: "#c69b00",
      LOW: "#34c759", INFO: "#8e8e93",
    };
    return m[s?.toUpperCase()] ?? "#8e8e93";
  };

  const severityBg = (s: string) => {
    const m: Record<string, string> = {
      CRITICAL: "rgba(255,59,48,0.10)", HIGH: "rgba(255,149,0,0.10)",
      MEDIUM: "rgba(255,204,0,0.12)", LOW: "rgba(52,199,89,0.08)", INFO: "rgba(142,142,147,0.10)",
    };
    return m[s?.toUpperCase()] ?? "rgba(142,142,147,0.10)";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-[28px] font-bold" style={{ letterSpacing: "-0.03em" }}>
          CVE Database
        </h1>
        <p className="text-[15px] text-muted-foreground mt-0.5">
          CVE-bevindingen uit scans + directe CVE-lookup via NVD
        </p>
      </div>

      {/* CVE Lookup */}
      <div className="rounded-2xl border border-border bg-card shadow-apple p-5">
        <h2 className="text-[15px] font-semibold mb-3">CVE Opzoeken</h2>
        <div className="flex gap-3">
          <input
            type="text"
            value={cveSearch}
            onChange={(e) => setCveSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && lookupCve()}
            placeholder="Bijv. CVE-2021-44228"
            className="flex-1 rounded-xl border border-border bg-secondary px-4 py-2.5 text-[14px] font-mono placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
          <button
            onClick={lookupCve}
            disabled={cveLoading || !cveSearch.trim()}
            className="inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-[14px] font-semibold transition-opacity hover:opacity-90 disabled:opacity-40"
            style={{ background: "#0071e3", color: "#fff" }}
          >
            {cveLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Opzoeken
          </button>
        </div>

        {cveError && (
          <p className="mt-3 text-[13px]" style={{ color: "#ff3b30" }}>
            Fout: {cveError}
          </p>
        )}

        {cveData && (
          <div className="mt-4 rounded-xl border border-border bg-secondary p-4 space-y-3">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[15px] font-semibold font-mono">{cveData.cve_id ?? cveSearch}</p>
                <p className="text-[13px] text-muted-foreground mt-1">{cveData.description?.slice(0, 300)}</p>
              </div>
              {cveData.cvss_score != null && (
                <div className="text-center flex-shrink-0">
                  <p className="text-[11px] text-muted-foreground uppercase tracking-wider">CVSS</p>
                  <p className="text-[28px] font-bold" style={{ color: severityColor(cveData.severity ?? "MEDIUM"), letterSpacing: "-0.03em" }}>
                    {cveData.cvss_score}
                  </p>
                </div>
              )}
            </div>
            {cveData.references?.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {cveData.references.slice(0, 3).map((ref: string, i: number) => (
                  <a key={i} href={ref} target="_blank" rel="noreferrer"
                     className="inline-flex items-center gap-1 text-[12px] text-primary hover:underline">
                    <ExternalLink className="h-3 w-3" /> Referentie {i + 1}
                  </a>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* CVE findings from scans */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[17px] font-semibold">
            CVE-bevindingen uit scans
            {cveFindings.length > 0 && (
              <span className="ml-2 text-[13px] font-normal text-muted-foreground">
                ({cveFindings.length} gevonden)
              </span>
            )}
          </h2>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter CVEs..."
              className="rounded-xl border border-border bg-card pl-9 pr-4 py-2 text-[13px] placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/30 w-48"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12 text-muted-foreground text-[14px]">
            <Loader2 className="h-5 w-5 animate-spin mr-2" /> Laden...
          </div>
        ) : filtered.length === 0 ? (
          <div className="rounded-2xl border border-border bg-card shadow-apple p-12 text-center">
            <Shield className="h-10 w-10 text-muted-foreground/20 mx-auto mb-3" />
            <p className="text-[15px] font-semibold mb-1">Geen CVE-bevindingen</p>
            <p className="text-[13px] text-muted-foreground mb-4">
              Voer een scan uit met de CVE Correlator module om CVEs te detecteren.
            </p>
            <Link href="/scans/new"
              className="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-[13px] font-semibold transition-opacity hover:opacity-90"
              style={{ background: "#0071e3", color: "#fff" }}>
              Scan starten
            </Link>
          </div>
        ) : (
          <div className="rounded-2xl border border-border bg-card shadow-apple overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border" style={{ background: "#f5f5f7" }}>
                  {["CVE ID", "Ernst / CVSS", "Service", "Beschrijving", "Scan"].map((h) => (
                    <th key={h} className="text-left text-[11px] font-semibold text-muted-foreground uppercase tracking-wider px-4 py-3">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((cve, i) => (
                  <tr key={i} className={`hover:bg-secondary/60 transition-colors ${i < filtered.length - 1 ? "border-b border-border" : ""}`}>
                    <td className="px-4 py-3">
                      <span className="font-mono text-[13px] font-semibold">{cve.id}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="rounded-full px-2.5 py-0.5 text-[11px] font-semibold"
                          style={{ background: severityBg(cve.severity), color: severityColor(cve.severity) }}>
                          {cve.severity}
                        </span>
                        {cve.score > 0 && (
                          <span className="text-[12px] text-muted-foreground font-mono">{cve.score}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[13px]">{cve.service ?? "—"}</span>
                      {cve.version && <span className="text-[11px] text-muted-foreground ml-1">{cve.version}</span>}
                      {cve.port && <span className="text-[11px] text-muted-foreground">:{cve.port}</span>}
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-[13px] text-muted-foreground line-clamp-2 max-w-xs">{cve.description}</p>
                    </td>
                    <td className="px-4 py-3">
                      {cve.scan_id ? (
                        <Link href={`/scans/${cve.scan_id}`}
                          className="text-[12px] text-primary hover:underline font-mono">
                          {cve.scan_id.slice(0, 12)}…
                        </Link>
                      ) : <span className="text-[12px] text-muted-foreground">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
