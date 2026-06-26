"use client";

import { ExternalLink } from "lucide-react";

/** OWASP / CWE / CVE / MITRE reference badges shown under a finding title. */
export function FindingMetaBadges({
  owasp_category,
  owasp_label,
  cwe,
  cwe_url,
  cve_id,
  cve_url,
  mitre_technique,
}: {
  owasp_category?: string;
  owasp_label?: string;
  cwe?: string;
  cwe_url?: string;
  cve_id?: string;
  cve_url?: string;
  mitre_technique?: string;
}) {
  const hasAny = owasp_category || cwe || cve_id || mitre_technique;
  if (!hasAny) return null;

  return (
    <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
      {owasp_category && (
        <span className="inline-flex items-center rounded-md border border-blue-500/40 bg-blue-500/10 px-2 py-0.5 font-mono text-[10px] font-semibold text-blue-300">
          {owasp_category}{owasp_label ? ` — ${owasp_label}` : ""}
        </span>
      )}
      {cwe && (
        <a
          href={cwe_url || "#"}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 rounded-md border border-violet-500/40 bg-violet-500/10 px-2 py-0.5 font-mono text-[10px] font-semibold text-violet-300 transition-colors hover:border-violet-400"
        >
          {cwe} <ExternalLink className="h-2.5 w-2.5" />
        </a>
      )}
      {cve_id && (
        <a
          href={cve_url || "#"}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 rounded-md border border-neon-red/40 bg-neon-red/10 px-2 py-0.5 font-mono text-[10px] font-semibold text-neon-red transition-colors hover:border-neon-red"
        >
          {cve_id} <ExternalLink className="h-2.5 w-2.5" />
        </a>
      )}
      {mitre_technique && (
        <span className="inline-flex items-center rounded-md border border-grid bg-card2 px-2 py-0.5 font-mono text-[10px] font-semibold text-ink-muted">
          {mitre_technique}
        </span>
      )}
    </div>
  );
}

export default FindingMetaBadges;
