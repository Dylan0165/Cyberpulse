"""Findings deduplicator — removes duplicate findings before AI analysis.

Deduplication key: (type, target, port).
When duplicates exist the most detailed version is kept (highest description
length + total number of populated keys).
"""

import logging

logger = logging.getLogger("cyberpulse.engine.deduplicator")


def _finding_key(finding: dict) -> str:
    """Build a stable dedup key from (type, target, port)."""
    ftype = (
        finding.get("type") or finding.get("category") or "unknown"
    ).lower().strip()
    target = (
        finding.get("target") or finding.get("url") or finding.get("host") or ""
    ).lower().strip()
    port = str(finding.get("port") or "")
    return f"{ftype}|{target}|{port}"


def _detail_score(finding: dict) -> int:
    """Score a finding by how much detail it contains.

    Higher score = richer finding that should win when deduplicating.
    """
    desc = (
        finding.get("description") or finding.get("beschrijving") or ""
    )
    populated_keys = sum(1 for v in finding.values() if v)
    return len(str(desc)) + populated_keys * 5


def deduplicate_findings(results: list[dict]) -> list[dict]:
    """Remove duplicate findings from module results.

    Args:
        results: List of module result dicts, each with a ``findings`` key.

    Returns:
        New list of module result dicts with duplicates removed.  The most
        detailed version of each finding is kept and placed in the first
        module that contained that key.
    """
    # Pass 1 — find the most detailed finding for every key
    best: dict[str, dict] = {}
    for module_result in results:
        for finding in module_result.get("findings", []):
            key = _finding_key(finding)
            if key not in best or _detail_score(finding) > _detail_score(best[key]):
                best[key] = finding

    # Pass 2 — rebuild results keeping each key exactly once
    seen_keys: set[str] = set()
    deduped_results: list[dict] = []
    total_before = 0
    total_after = 0

    for module_result in results:
        deduped_findings: list[dict] = []
        for finding in module_result.get("findings", []):
            total_before += 1
            key = _finding_key(finding)
            if key not in seen_keys:
                seen_keys.add(key)
                deduped_findings.append(best[key])  # use the richest version
                total_after += 1
        # Preserve all other module fields, replace findings list
        module_copy = {**module_result, "findings": deduped_findings}
        deduped_results.append(module_copy)

    removed = total_before - total_after
    if removed:
        logger.info(
            "Deduplicator: %d findings → %d (removed %d duplicates)",
            total_before, total_after, removed,
        )

    return deduped_results


def deduplicate_scan_data(scan_data: dict) -> dict:
    """Convenience wrapper that operates on a full scan_data dict in-place.

    Mutates and returns the dict with ``results`` deduplicated and
    ``total_findings`` updated.
    """
    results = scan_data.get("results", [])
    deduped = deduplicate_findings(results)
    scan_data["results"] = deduped
    scan_data["total_findings"] = sum(
        len(m.get("findings", [])) for m in deduped
    )
    return scan_data
