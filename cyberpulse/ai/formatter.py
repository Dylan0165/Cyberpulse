"""AI output formatter — transforms DeepSeek analysis into display-ready formats."""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("cyberpulse.ai.formatter")

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
SEVERITY_COLORS = {
    "critical": "#dc2626",
    "high": "#ea580c",
    "medium": "#d97706",
    "low": "#2563eb",
    "info": "#6b7280",
}
SEVERITY_LABELS_NL = {
    "critical": "Kritiek",
    "high": "Hoog",
    "medium": "Gemiddeld",
    "low": "Laag",
    "info": "Informatie",
}

COMPLEXITY_MAP = {"critical": "hoog", "high": "gemiddeld", "medium": "laag", "low": "laag", "info": "laag"}


def _derive_actieplan(bevindingen: list) -> list:
    """Auto-derive a prioritized action plan from findings when AI didn't provide one."""
    plan = []
    prio = 1
    for ernst in ("critical", "high", "medium", "low"):
        for f in bevindingen:
            if f.get("ernst") == ernst and f.get("aanbeveling"):
                plan.append({
                    "prioriteit": prio,
                    "actie": f.get("aanbeveling", "")[:120],
                    "reden": f"Bevinding: {f.get('titel', '')} ({SEVERITY_LABELS_NL.get(ernst, ernst)})",
                    "complexiteit": COMPLEXITY_MAP.get(ernst, "gemiddeld"),
                })
                prio += 1
                if prio > 10:
                    return plan
    return plan


def format_for_web(analysis: dict, scan_data: dict) -> dict:
    """Format the AI analysis for the web interface.

    Returns a dict with all the data needed to render the report page.
    """
    if "error" in analysis:
        # Try to recover from raw_response if it contains usable JSON
        raw = analysis.get("raw_response", "")
        if raw:
            try:
                stripped = raw.strip()
                if stripped.startswith("```"):
                    stripped = stripped.split("\n", 1)[1] if "\n" in stripped else stripped[3:]
                if stripped.endswith("```"):
                    stripped = stripped.rsplit("```", 1)[0].strip()
                start = stripped.index("{")
                end = stripped.rindex("}") + 1
                recovered = json.loads(stripped[start:end])
                logger.warning("Recovered analysis from raw_response for scan %s", scan_data.get("scan_id"))
                analysis = recovered
            except Exception:
                pass

    if "error" in analysis:
        return {
            "error": True,
            "error_message": analysis["error"],
            "scan_id": scan_data.get("scan_id", ""),
            "target": scan_data.get("target", ""),
        }

    samenvatting = analysis.get("samenvatting", {})
    bevindingen = analysis.get("bevindingen", [])

    # Sort findings by severity
    bevindingen.sort(key=lambda f: SEVERITY_ORDER.get(f.get("ernst", "info"), 5))

    # Count by severity
    severity_counts = {}
    for f in bevindingen:
        s = f.get("ernst", "info")
        severity_counts[s] = severity_counts.get(s, 0) + 1

    # Risicoscore band
    score = samenvatting.get("risicoscore", 0)
    if score >= 80:
        score_class = "critical"
    elif score >= 60:
        score_class = "high"
    elif score >= 40:
        score_class = "medium"
    elif score >= 20:
        score_class = "low"
    else:
        score_class = "safe"

    return {
        "error": False,
        "scan_id": scan_data.get("scan_id", ""),
        "target": scan_data.get("target", ""),
        "scan_type": scan_data.get("scan_type", ""),
        "scan_date": scan_data.get("started_at", datetime.now(timezone.utc).isoformat()),
        "modules_run": scan_data.get("modules_run", []),
        "total_findings": scan_data.get("total_findings", 0),
        "risicoscore": score,
        "risicoscore_class": score_class,
        "niveau": samenvatting.get("niveau", "onbekend"),
        "korte_beschrijving": samenvatting.get("korte_beschrijving", ""),
        "management_samenvatting": analysis.get("management_samenvatting", ""),
        "bevindingen": [
            {
                **f,
                "ernst_nl": SEVERITY_LABELS_NL.get(f.get("ernst", "info"), f.get("ernst", "")),
                "ernst_color": SEVERITY_COLORS.get(f.get("ernst", "info"), "#6b7280"),
            }
            for f in bevindingen
        ],
        "severity_counts": severity_counts,
        "aanbevelingen": analysis.get("aanbevelingen_prioriteit") or _derive_actieplan(bevindingen),
        "technische_details": analysis.get("technische_details", ""),
        "severity_colors": SEVERITY_COLORS,
    }


def format_for_pdf(analysis: dict, scan_data: dict) -> dict:
    """Format analysis data for PDF report generation."""
    web_data = format_for_web(analysis, scan_data)
    web_data["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Template aliases — report.html uses different variable names
    web_data["risk_class"]   = web_data.get("risicoscore_class", "low")
    web_data["niveau"]       = web_data.get("niveau", "onbekend").upper()
    web_data["modules_count"] = len(web_data.get("modules_run", []))
    web_data["findings_count"] = web_data.get("total_findings", 0)

    sev = web_data.get("severity_counts", {})
    web_data["critical_count"] = sev.get("critical", 0)
    web_data["high_count"]     = sev.get("high", 0)
    web_data["medium_count"]   = sev.get("medium", 0)
    web_data["low_count"]      = sev.get("low", 0)

    # Template uses aanbevelingen_prioriteit
    web_data["aanbevelingen_prioriteit"] = web_data.get("aanbevelingen", [])

    # Ensure all finding fields exist to prevent Jinja errors
    clean = []
    for f in web_data.get("bevindingen", []):
        clean.append({
            "titel":       f.get("titel") or f.get("title") or f.get("type", "Bevinding"),
            "module":      f.get("module") or f.get("module_id", ""),
            "ernst":       f.get("ernst") or f.get("severity", "info"),
            "beschrijving": f.get("beschrijving") or f.get("description") or f.get("detail", ""),
            "impact":      f.get("impact", ""),
            "aanbeveling": f.get("aanbeveling") or f.get("recommendation", ""),
            "referenties": f.get("referenties") or f.get("references", []),
            "cve":         f.get("cve", ""),
        })
    web_data["bevindingen"] = clean
    return web_data


def format_for_cli(analysis: dict) -> str:
    """Format the analysis as a colored text summary for CLI output."""
    if "error" in analysis:
        return f"\n[FOUT] AI analyse mislukt: {analysis['error']}\n"

    lines = []
    samenvatting = analysis.get("samenvatting", {})
    lines.append("\n" + "=" * 60)
    lines.append("  CYBERPULSE AI ANALYSE")
    lines.append("=" * 60)

    score = samenvatting.get("risicoscore", 0)
    niveau = samenvatting.get("niveau", "onbekend")
    lines.append(f"\n  Risicoscore: {score}/100 ({niveau})")
    lines.append(f"  {samenvatting.get('korte_beschrijving', '')}")

    lines.append("\n" + "-" * 60)
    lines.append("  MANAGEMENT SAMENVATTING")
    lines.append("-" * 60)
    lines.append(f"  {analysis.get('management_samenvatting', 'Geen samenvatting beschikbaar')}")

    bevindingen = analysis.get("bevindingen", [])
    if bevindingen:
        lines.append("\n" + "-" * 60)
        lines.append("  TOP BEVINDINGEN")
        lines.append("-" * 60)
        for i, f in enumerate(bevindingen[:10], 1):
            ernst = f.get("ernst", "info").upper()
            titel = f.get("titel", "Onbekend")
            lines.append(f"\n  {i}. [{ernst}] {titel}")
            lines.append(f"     {f.get('beschrijving', '')[:150]}")
            lines.append(f"     Aanbeveling: {f.get('aanbeveling', '')[:150]}")

    aanbevelingen = analysis.get("aanbevelingen_prioriteit", [])
    if aanbevelingen:
        lines.append("\n" + "-" * 60)
        lines.append("  GEPRIORITEERDE AANBEVELINGEN")
        lines.append("-" * 60)
        for a in aanbevelingen[:10]:
            prio = a.get("prioriteit", "?")
            actie = a.get("actie", "")
            complexiteit = a.get("complexiteit", "")
            lines.append(f"\n  #{prio} {actie}")
            lines.append(f"     Complexiteit: {complexiteit}")
            lines.append(f"     Reden: {a.get('reden', '')[:120]}")

    lines.append("\n" + "=" * 60 + "\n")
    return "\n".join(lines)
