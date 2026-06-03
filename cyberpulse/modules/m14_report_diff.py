"""Module 14-RD — Report Differentiator / Scan Comparator.

Compares the current scan against the most recent previous scan on the same
target and reports new, resolved, and unchanged vulnerabilities.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("cyberpulse.modules.m14_report_diff")


def _finding_key(finding: dict) -> str:
    """Stable key for deduplication across scans."""
    return (
        f"{finding.get('type','unknown')}:"
        f"{finding.get('title', finding.get('type',''))[:80]}:"
        f"{finding.get('port','')}"
    )


class Scanner:
    name = "Scan Comparator"
    phase = "custom"
    description = "Diffs current scan against previous scan for the same target"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config or {}

    # ── data helpers ──────────────────────────────────────────────────────────

    def _load_current_findings(self) -> list[dict]:
        scan_data_file = self.output_dir / "scan_data.json"
        if not scan_data_file.exists():
            return []
        try:
            with open(scan_data_file, encoding="utf-8") as f:
                data = json.load(f)
            findings = []
            for result in data.get("results", []):
                findings.extend(result.get("findings", []))
            return findings
        except Exception as e:
            logger.warning("Could not read current scan_data.json: %s", e)
            return []

    def _find_previous_scan(self) -> dict | None:
        """Find the most recent previous scan for the same target."""
        try:
            from config import Config  # type: ignore
            scans_dir = Config.SCANS_DIR
        except ImportError:
            # Fallback: guess scans dir from output_dir location
            scans_dir = self.output_dir.parent

        current_id = self.output_dir.name
        best: dict | None = None
        best_time: datetime | None = None

        for scan_dir in sorted(scans_dir.iterdir()):
            if not scan_dir.is_dir() or scan_dir.name == current_id:
                continue
            scan_data_file = scan_dir / "scan_data.json"
            if not scan_data_file.exists():
                continue
            try:
                with open(scan_data_file, encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("target", "").rstrip("/") != self.target.rstrip("/"):
                    continue
                ts_str = data.get("started_at") or data.get("created_at", "")
                ts = None
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    except Exception:
                        pass
                if ts is None:
                    # Parse from directory name (YYYYMMDD_HHMMSS_...)
                    try:
                        ts = datetime.strptime(scan_dir.name[:15], "%Y%m%d_%H%M%S")
                        ts = ts.replace(tzinfo=timezone.utc)
                    except Exception:
                        continue

                if best_time is None or ts > best_time:
                    best_time = ts
                    best = data
                    best["_scan_dir"] = str(scan_dir)
                    best["_scan_id"] = scan_dir.name
            except Exception:
                continue

        return best

    # ── main ──────────────────────────────────────────────────────────────────

    def run(self) -> dict:
        findings: list[dict] = []
        raw_lines: list[str] = []

        raw_lines.append(f"[+] Scan Comparator — target: {self.target}")

        previous_scan = self._find_previous_scan()
        if not previous_scan:
            raw_lines.append("[*] No previous scan found for this target — first scan baseline established")
            return {
                "findings": [{
                    "type": "scan_baseline",
                    "severity": "INFO",
                    "title": "First scan — baseline established",
                    "description": "No previous scan found for this target. This scan establishes the baseline for future comparisons.",
                    "impact": "N/A",
                    "recommendation": "Run subsequent scans regularly to track security posture changes.",
                    "evidence": "",
                }],
                "raw_output": "\n".join(raw_lines),
                "is_first_scan": True,
            }

        prev_id = previous_scan.get("_scan_id", "unknown")
        prev_date = previous_scan.get("started_at", "unknown")[:10]
        raw_lines.append(f"[*] Comparing against previous scan: {prev_id} ({prev_date})")

        # Load findings
        current_findings = self._load_current_findings()
        prev_findings: list[dict] = []
        for result in previous_scan.get("results", []):
            prev_findings.extend(result.get("findings", []))

        raw_lines.append(f"[*] Current: {len(current_findings)} findings, Previous: {len(prev_findings)} findings")

        # Build key sets
        prev_keys = {_finding_key(f): f for f in prev_findings}
        curr_keys = {_finding_key(f): f for f in current_findings}

        new_vulns = [curr_keys[k] for k in curr_keys if k not in prev_keys]
        resolved_vulns = [prev_keys[k] for k in prev_keys if k not in curr_keys]
        persisting_count = sum(1 for k in curr_keys if k in prev_keys)

        # Severity counts
        def count_sev(lst: list[dict], sev: str) -> int:
            return sum(1 for f in lst if (f.get("severity") or "").lower() == sev.lower())

        prev_crit = count_sev(prev_findings, "CRITICAL")
        curr_crit = count_sev(current_findings, "CRITICAL")
        trend = "improving" if len(resolved_vulns) > len(new_vulns) else "worsening" if len(new_vulns) > len(resolved_vulns) else "stable"

        raw_lines.append(f"[*] New vulnerabilities: {len(new_vulns)}")
        raw_lines.append(f"[*] Resolved vulnerabilities: {len(resolved_vulns)}")
        raw_lines.append(f"[*] Persisting vulnerabilities: {persisting_count}")
        raw_lines.append(f"[*] Security trend: {trend}")

        # Create comparison findings
        if new_vulns:
            for v in new_vulns[:20]:  # cap list
                findings.append({
                    "type": "new_vulnerability",
                    "severity": v.get("severity", "MEDIUM"),
                    "title": f"[NEW] {v.get('title', v.get('type', 'Unknown'))}",
                    "description": f"This vulnerability was NOT present in the previous scan ({prev_date}). {v.get('description', '')}",
                    "impact": v.get("impact", ""),
                    "recommendation": v.get("recommendation", ""),
                    "evidence": v.get("evidence", ""),
                })

        if resolved_vulns:
            findings.append({
                "type": "resolved_vulnerabilities",
                "severity": "INFO",
                "title": f"{len(resolved_vulns)} vulnerabilities resolved since {prev_date}",
                "description": f"The following findings from the previous scan are no longer present: " +
                               "; ".join(v.get("title", v.get("type", ""))[:50] for v in resolved_vulns[:10]),
                "impact": "Security posture improved.",
                "recommendation": "Continue monitoring to ensure vulnerabilities remain resolved.",
                "evidence": json.dumps([v.get("title", "") for v in resolved_vulns[:10]]),
            })

        findings.append({
            "type": "scan_comparison_summary",
            "severity": "INFO",
            "title": f"Scan comparison summary — trend: {trend.upper()}",
            "description": (
                f"Compared to scan from {prev_date}: "
                f"{len(new_vulns)} new vulnerabilities, "
                f"{len(resolved_vulns)} resolved, "
                f"{persisting_count} persisting. "
                f"Critical count: {prev_crit} → {curr_crit} "
                f"({'↑ worse' if curr_crit > prev_crit else '↓ better' if curr_crit < prev_crit else '= unchanged'})."
            ),
            "impact": "Security posture tracking.",
            "recommendation": "Address new vulnerabilities immediately; maintain resolved items.",
            "evidence": (
                f"Previous scan: {prev_id}\n"
                f"New: {len(new_vulns)}, Resolved: {len(resolved_vulns)}, Persisting: {persisting_count}"
            ),
        })

        raw_lines.append(f"[+] Done — {len(findings)} comparison findings")
        return {
            "findings": findings,
            "raw_output": "\n".join(raw_lines),
            "comparison": {
                "previous_scan_id": prev_id,
                "previous_scan_date": prev_date,
                "new_vulnerabilities": len(new_vulns),
                "resolved_vulnerabilities": len(resolved_vulns),
                "persisting_vulnerabilities": persisting_count,
                "critical_change": curr_crit - prev_crit,
                "trend": trend,
            },
        }
