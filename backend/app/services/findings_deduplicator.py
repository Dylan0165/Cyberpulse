"""Deduplicate raw scan findings before AI analysis.

Multiple modules can report the same issue (same type+target+port). We collapse
those into one, keep the most severe severity, and record how many times it was
seen (duplicate_count).
"""

from __future__ import annotations

import hashlib

_SEV_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]


def _sev_index(sev) -> int:
    try:
        return _SEV_ORDER.index(str(sev or "INFO").upper())
    except ValueError:
        return _SEV_ORDER.index("INFO")


def finding_key(f: dict) -> str:
    """Stable dedupe key: type:target:port."""
    return f"{f.get('type','')}:{f.get('target','')}:{f.get('port','')}"


def stable_finding_id(scan_id: str, f: dict) -> str:
    """Deterministic id for a finding within a scan (used by FindingStatus)."""
    h = hashlib.sha1(f"{scan_id}:{finding_key(f)}".encode("utf-8")).hexdigest()
    return h[:32]


class FindingsDeduplicator:
    @staticmethod
    def deduplicate(findings: list[dict]) -> list[dict]:
        """Collapse duplicates by type+target+port, keeping the worst severity."""
        seen: dict[str, dict] = {}
        for f in findings or []:
            if not isinstance(f, dict):
                continue
            key = finding_key(f)
            if key not in seen:
                seen[key] = {**f, "duplicate_count": 1}
            else:
                seen[key]["duplicate_count"] += 1
                if _sev_index(f.get("severity")) < _sev_index(seen[key].get("severity")):
                    seen[key]["severity"] = f.get("severity")
        return list(seen.values())
