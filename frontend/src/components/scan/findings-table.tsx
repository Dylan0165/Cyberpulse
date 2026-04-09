"use client";

import { Badge } from "@/components/ui/badge";
import type { Finding } from "@/types";
import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

interface FindingsTableProps {
  findings: Finding[];
}

const severityOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFO: 4 };

export function FindingsTable({ findings }: FindingsTableProps) {
  const [filter, setFilter] = useState<string>("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const filtered =
    filter === "all"
      ? findings
      : findings.filter((f) => f.risk_level === filter);

  const sorted = [...filtered].sort(
    (a, b) =>
      (severityOrder[a.risk_level] ?? 5) - (severityOrder[b.risk_level] ?? 5)
  );

  const severityVariant = (level: string) => {
    const map: Record<string, any> = {
      CRITICAL: "critical",
      HIGH: "high",
      MEDIUM: "medium",
      LOW: "low",
      INFO: "info",
    };
    return map[level] || "default";
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-2">
        {["all", "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"].map((level) => (
          <button
            key={level}
            onClick={() => setFilter(level)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              filter === level
                ? "bg-primary text-primary-foreground"
                : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
            }`}
          >
            {level === "all" ? "All" : level}
            {level !== "all" && (
              <span className="ml-1">
                ({findings.filter((f) => f.risk_level === level).length})
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="rounded-lg border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="p-3 text-left w-8"></th>
              <th className="p-3 text-left">Finding</th>
              <th className="p-3 text-left">Severity</th>
              <th className="p-3 text-left">CVSS</th>
              <th className="p-3 text-left">Asset</th>
              <th className="p-3 text-left">Phase</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((finding) => (
              <>
                <tr
                  key={finding.id}
                  className="border-b hover:bg-muted/30 cursor-pointer"
                  onClick={() =>
                    setExpandedId(expandedId === finding.id ? null : finding.id)
                  }
                >
                  <td className="p-3">
                    {expandedId === finding.id ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                  </td>
                  <td className="p-3 font-medium">{finding.title}</td>
                  <td className="p-3">
                    <Badge variant={severityVariant(finding.risk_level)}>
                      {finding.risk_level}
                    </Badge>
                  </td>
                  <td className="p-3">{finding.cvss_score ?? "-"}</td>
                  <td className="p-3 text-muted-foreground">
                    {finding.affected_asset}
                  </td>
                  <td className="p-3 text-muted-foreground">{finding.phase}</td>
                </tr>
                {expandedId === finding.id && (
                  <tr key={`${finding.id}-detail`}>
                    <td colSpan={6} className="bg-muted/20 p-6">
                      <div className="space-y-4">
                        <div>
                          <h4 className="font-medium mb-1">Description</h4>
                          <p className="text-sm text-muted-foreground">
                            {finding.description}
                          </p>
                        </div>
                        {finding.cve_ids.length > 0 && (
                          <div>
                            <h4 className="font-medium mb-1">CVE References</h4>
                            <div className="flex gap-2">
                              {finding.cve_ids.map((cve) => (
                                <Badge key={cve} variant="outline">
                                  {cve}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}
                        <div>
                          <h4 className="font-medium mb-1">Business Impact</h4>
                          <p className="text-sm text-muted-foreground">
                            {finding.business_impact}
                          </p>
                        </div>
                        <div>
                          <h4 className="font-medium mb-1">Evidence</h4>
                          <pre className="rounded bg-black p-3 text-xs text-green-300 overflow-x-auto">
                            {finding.evidence}
                          </pre>
                        </div>
                        <div>
                          <h4 className="font-medium mb-1">
                            Remediation (Est. {finding.estimated_fix_time})
                          </h4>
                          <ul className="list-disc pl-5 space-y-1 text-sm">
                            {finding.remediation_steps.map((step, i) => (
                              <li key={i}>{step}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>

        {sorted.length === 0 && (
          <div className="p-8 text-center text-muted-foreground">
            No findings match the current filter
          </div>
        )}
      </div>
    </div>
  );
}
