"""Module 50 — Evidence Collection & Reporting Engine.

Aggregates all findings from previous modules, classifies by severity,
validates critical findings, and generates a structured evidence package.
"""

import json
import logging
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m50")


class Scanner:
    name = "Evidence Collection & Reporting"
    phase = "reporting"
    description = "Aggregates findings, validates criticals, and generates evidence packages"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"Evidence collection & reporting for {self.target}"]
        raw_lines.append(f"Timestamp: {datetime.now().isoformat()}")

        # Phase 1: Collect all previous module outputs
        raw_lines.append("\n[Phase 1: Aggregating Module Results]")
        all_findings = []
        module_files = sorted(self.output_dir.glob("*.json"))
        for mfile in module_files:
            if mfile.name == "50_evidence.json":
                continue
            try:
                with open(mfile, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    module_findings = data.get("findings", [])
                    all_findings.extend(module_findings)
                    raw_lines.append(f"  {mfile.name}: {len(module_findings)} findings")
            except Exception as e:
                raw_lines.append(f"  {mfile.name}: error reading — {e}")

        raw_lines.append(f"\n  Total findings aggregated: {len(all_findings)}")

        # Phase 2: Classify by severity
        raw_lines.append("\n[Phase 2: Severity Classification]")
        severity_counts = Counter(f.get("severity", "unknown") for f in all_findings)
        for sev in ["critical", "high", "medium", "low", "info"]:
            count = severity_counts.get(sev, 0)
            raw_lines.append(f"  {sev.upper()}: {count}")
            findings.append({
                "type": "severity_summary",
                "severity_level": sev,
                "count": count,
                "detail": f"{sev.upper()}: {count} findings",
                "severity": "info",
            })

        # Phase 3: Classify by type
        raw_lines.append("\n[Phase 3: Finding Type Distribution]")
        type_counts = Counter(f.get("type", "unknown") for f in all_findings)
        for ftype, count in type_counts.most_common(20):
            raw_lines.append(f"  {ftype}: {count}")

        # Phase 4: Validate critical findings
        raw_lines.append("\n[Phase 4: Critical Finding Validation]")
        criticals = [f for f in all_findings if f.get("severity") == "critical"]
        validated_criticals = []
        for critical in criticals[:10]:
            validated = self._validate_finding(critical)
            status = "CONFIRMED" if validated else "NEEDS_REVIEW"
            validated_criticals.append({**critical, "validation_status": status})
            raw_lines.append(f"  {status}: {critical.get('detail', 'Unknown')[:80]}")

        findings.append({
            "type": "critical_validation",
            "total_criticals": len(criticals),
            "validated": len([v for v in validated_criticals if v.get("validation_status") == "CONFIRMED"]),
            "detail": f"Validated {len(validated_criticals)} of {len(criticals)} critical findings",
            "severity": "info",
        })

        # Phase 5: Risk score calculation
        raw_lines.append("\n[Phase 5: Risk Score Calculation]")
        weights = {"critical": 10, "high": 5, "medium": 2, "low": 1, "info": 0}
        risk_score = sum(weights.get(f.get("severity", "info"), 0) for f in all_findings)
        max_possible = len(all_findings) * 10
        risk_percentage = (risk_score / max_possible * 100) if max_possible > 0 else 0

        if risk_percentage >= 70:
            risk_level = "CRITICAL"
        elif risk_percentage >= 40:
            risk_level = "HIGH"
        elif risk_percentage >= 20:
            risk_level = "MEDIUM"
        elif risk_percentage >= 5:
            risk_level = "LOW"
        else:
            risk_level = "MINIMAL"

        findings.append({
            "type": "risk_score",
            "score": risk_score,
            "max_possible": max_possible,
            "percentage": round(risk_percentage, 1),
            "risk_level": risk_level,
            "detail": f"Risk Score: {risk_score}/{max_possible} ({risk_percentage:.1f}%) — {risk_level}",
            "severity": "info",
        })
        raw_lines.append(f"  Risk Score: {risk_score}/{max_possible} ({risk_percentage:.1f}%)")
        raw_lines.append(f"  Risk Level: {risk_level}")

        # Phase 6: Generate structured evidence file
        raw_lines.append("\n[Phase 6: Evidence Package Generation]")
        evidence = {
            "target": self.target,
            "scan_timestamp": datetime.now().isoformat(),
            "total_findings": len(all_findings),
            "severity_summary": dict(severity_counts),
            "risk_score": {
                "score": risk_score,
                "max_possible": max_possible,
                "percentage": round(risk_percentage, 1),
                "level": risk_level,
            },
            "critical_findings": validated_criticals,
            "high_findings": [f for f in all_findings if f.get("severity") == "high"],
            "medium_findings": [f for f in all_findings if f.get("severity") == "medium"],
            "low_findings": [f for f in all_findings if f.get("severity") == "low"],
            "type_distribution": dict(type_counts.most_common(30)),
            "all_findings": all_findings,
        }

        evidence_file = self.output_dir / "evidence_report.json"
        with open(evidence_file, "w", encoding="utf-8") as f:
            json.dump(evidence, f, indent=2, default=str)
        raw_lines.append(f"  Evidence report saved: {evidence_file}")

        # Phase 7: Executive summary
        raw_lines.append("\n[Phase 7: Executive Summary]")
        raw_lines.append(f"  Target: {self.target}")
        raw_lines.append(f"  Total Issues: {len(all_findings)}")
        raw_lines.append(f"  Critical: {severity_counts.get('critical', 0)}")
        raw_lines.append(f"  High: {severity_counts.get('high', 0)}")
        raw_lines.append(f"  Medium: {severity_counts.get('medium', 0)}")
        raw_lines.append(f"  Low: {severity_counts.get('low', 0)}")
        raw_lines.append(f"  Informational: {severity_counts.get('info', 0)}")
        raw_lines.append(f"  Overall Risk: {risk_level} ({risk_percentage:.1f}%)")
        raw_lines.append(f"  Modules Executed: {len(module_files)}")

        # Top recommendations
        raw_lines.append("\n  Top Recommendations:")
        if severity_counts.get("critical", 0) > 0:
            raw_lines.append("  1. URGENT: Address all critical findings immediately")
        if severity_counts.get("high", 0) > 0:
            raw_lines.append("  2. HIGH PRIORITY: Remediate high-severity issues within 7 days")
        if severity_counts.get("medium", 0) > 0:
            raw_lines.append("  3. MEDIUM: Plan remediation within 30 days")
        if severity_counts.get("low", 0) > 0:
            raw_lines.append("  4. LOW: Address in next maintenance cycle")

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "50_evidence.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("Evidence collection %s: %d total findings aggregated", self.target, len(all_findings))
        return {"findings": findings, "raw_output": raw_output}

    def _validate_finding(self, finding: dict) -> bool:
        """Re-test a critical finding to confirm it's valid."""
        ftype = finding.get("type", "")
        base_url = self._get_base_url()

        if "rce" in ftype:
            # Re-check RCE
            param = finding.get("parameter", "cmd")
            try:
                resp = self.session.get(
                    f"{base_url}/?{param}=;echo cyberpulse_validate",
                    timeout=8,
                )
                return "cyberpulse_validate" in resp.text
            except Exception:
                return False

        if "sqli" in ftype or "injection" in ftype:
            # Re-check injection
            param = finding.get("parameter", "id")
            try:
                resp = self.session.get(
                    f"{base_url}/?{param}=' OR '1'='1",
                    timeout=8,
                )
                return any(e in resp.text.lower()
                           for e in ["sql", "mysql", "sqlite", "error"])
            except Exception:
                return False

        if "lfi" in ftype or "traversal" in ftype:
            param = finding.get("parameter", "file")
            try:
                resp = self.session.get(
                    f"{base_url}/?{param}=../../../etc/passwd",
                    timeout=8,
                )
                return "root:" in resp.text
            except Exception:
                return False

        # Default: trust the original finding
        return True

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
