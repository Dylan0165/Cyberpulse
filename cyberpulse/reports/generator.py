"""Report Generator — creates professional pentest reports and secure solution documents.

Generates two documents after each scan:
  1. pentest_report.html / pentest_report.pdf  — full penetration test report
  2. secure_solution.html / secure_solution.pdf — remediation guide with commands

Falls back to the legacy report.html template if the new templates are unavailable.
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from config import Config
from ai.formatter import format_for_pdf

logger = logging.getLogger("cyberpulse.reports.generator")

# ── CSS variable substitution (xhtml2pdf can't resolve var()) ─────────────────
_CSS_VARS = {
    "--black": "#000000", "--white": "#ffffff",
    "--gray-1": "#111111", "--gray-2": "#333333", "--gray-3": "#666666",
    "--gray-4": "#999999", "--gray-5": "#cccccc", "--gray-6": "#eeeeee",
    "--critical": "#cc0000", "--high": "#cc6600", "--medium": "#999900", "--low": "#666666",
    "--accent": "#1a3a5c",
}


def _prepare_html_for_pdf(html: str) -> str:
    """Strip CSS features unsupported by xhtml2pdf."""
    html = re.sub(r"@import\s+url\([^)]+\);?", "", html)

    def replace_var(m: re.Match) -> str:
        return _CSS_VARS.get(m.group(1), m.group(0))

    html = re.sub(r"var\((--[\w-]+)\)", replace_var, html)
    html = html.replace("'JetBrains Mono'", "Courier").replace('"JetBrains Mono"', "Courier")
    html = html.replace("'Crimson Pro'", "Times New Roman")
    html = re.sub(r":root\s*\{[^}]*\}", "", html, flags=re.DOTALL)
    html = re.sub(r"display\s*:\s*flex\s*;?", "display: block;", html)
    html = re.sub(r"flex-direction\s*:[^;]+;?", "", html)
    html = re.sub(r"justify-content\s*:[^;]+;?", "", html)
    html = re.sub(r"align-items\s*:[^;]+;?", "", html)
    html = re.sub(r"\bflex\s*:\s*\d+\s*;?", "", html)
    html = re.sub(r"\bgap\s*:[^;]+;?", "", html)
    return html


def _render_to_pdf(html_path: Path) -> Path | None:
    """Convert an HTML file to PDF using xhtml2pdf. Returns PDF path or None."""
    pdf_path = html_path.with_suffix(".pdf")
    try:
        from xhtml2pdf import pisa
        import logging as _logging
        _logging.getLogger("xhtml2pdf").setLevel(_logging.ERROR)

        html_content = html_path.read_text(encoding="utf-8")
        pdf_html = _prepare_html_for_pdf(html_content)
        with open(pdf_path, "wb") as f:
            result = pisa.CreatePDF(pdf_html.encode("utf-8"), dest=f, encoding="utf-8")
        if result.err:
            logger.warning("xhtml2pdf errors for %s: %s", html_path.name, result.err)
            pdf_path.unlink(missing_ok=True)
            return None
        return pdf_path
    except Exception as e:
        logger.error("PDF generation failed for %s: %s", html_path.name, e)
        pdf_path.unlink(missing_ok=True)
        return None


def _load_scan(scan_id: str) -> tuple[dict, dict]:
    """Load scan_data.json and analysis.json; return (scan_data, analysis)."""
    scan_dir = Config.SCANS_DIR / scan_id
    scan_data: dict = {}
    analysis: dict = {}

    sd_file = scan_dir / "scan_data.json"
    if sd_file.exists():
        with open(sd_file, encoding="utf-8") as f:
            scan_data = json.load(f)

    an_file = scan_dir / "analysis.json"
    if an_file.exists():
        with open(an_file, encoding="utf-8") as f:
            analysis = json.load(f)

    return scan_data, analysis


# ── Severity helpers ──────────────────────────────────────────────────────────

def _count_sev(findings: list[dict], sev: str) -> int:
    return sum(1 for f in findings if (f.get("ernst") or f.get("severity") or "").lower() == sev.lower())


def _all_findings(scan_data: dict) -> list[dict]:
    results: list[dict] = []
    for r in scan_data.get("results", []):
        for f in r.get("findings", []):
            results.append({
                "titel":        f.get("title") or f.get("type") or f.get("name") or "Bevinding",
                "ernst":        (f.get("severity") or f.get("ernst") or "info").lower(),
                "beschrijving": f.get("description") or f.get("beschrijving") or f.get("detail") or "",
                "impact":       f.get("impact") or f.get("impact", ""),
                "aanbeveling":  f.get("recommendation") or f.get("aanbeveling") or "",
                "referenties":  f.get("references") or f.get("referenties") or [],
                "cve":          f.get("cve") or "",
                "evidence":     f.get("evidence") or f.get("bewijs") or "",
                "fix_command":  f.get("fix_command") or "",
                "verify_command": f.get("verify_command") or "",
                "estimated_time": f.get("estimated_time") or "",
                "root_cause":   f.get("root_cause") or "",
            })
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    results.sort(key=lambda x: sev_order.get(x["ernst"], 5))
    return results


# ── Remediation roadmap ───────────────────────────────────────────────────────

def _build_remediation(analysis: dict, findings: list[dict]) -> tuple[list, list, list]:
    """Return (quick_wins, short_term, long_term) from analysis or fallback."""
    roadmap = analysis.get("remediation_roadmap") or analysis.get("aanbevelingen_roadmap") or {}

    def normalise(items: list) -> list[dict]:
        out = []
        for item in (items or []):
            if isinstance(item, str):
                out.append({"title": item, "description": item, "command": "", "verify": "", "estimated_time": ""})
            elif isinstance(item, dict):
                out.append({
                    "title": item.get("title") or item.get("titel") or item.get("action") or str(item)[:80],
                    "description": item.get("description") or item.get("beschrijving") or "",
                    "command": item.get("command") or item.get("fix_command") or "",
                    "verify": item.get("verify") or item.get("verify_command") or "",
                    "estimated_time": item.get("estimated_time") or item.get("tijd") or "",
                })
        return out

    quick_wins = normalise(roadmap.get("quick_wins") or roadmap.get("snelle_winst") or [])
    short_term = normalise(roadmap.get("short_term") or roadmap.get("korte_termijn") or [])
    long_term  = normalise(roadmap.get("long_term") or roadmap.get("lange_termijn") or [])

    # If AI didn't provide structured roadmap, build from critical/high findings
    if not quick_wins:
        crit_high = [f for f in findings if f["ernst"] in ("critical", "high")][:5]
        for f in crit_high:
            quick_wins.append({
                "title": f["titel"],
                "description": f["aanbeveling"] or f["beschrijving"],
                "command": f.get("fix_command", ""),
                "verify": f.get("verify_command", ""),
                "estimated_time": "< 4 uur",
            })

    if not short_term:
        medium = [f for f in findings if f["ernst"] == "medium"][:5]
        for f in medium:
            short_term.append({
                "title": f["titel"],
                "description": f["aanbeveling"] or f["beschrijving"],
                "command": f.get("fix_command", ""),
                "verify": f.get("verify_command", ""),
                "estimated_time": "1–3 dagen",
            })

    if not long_term:
        long_term = [
            {"title": "Implementeer een Web Application Firewall (WAF)", "description": "Een WAF filtert kwaadaardig verkeer voordat het de applicatie bereikt.", "command": "", "verify": "", "estimated_time": "1–2 weken"},
            {"title": "Voer periodieke penetratietests uit", "description": "Plan kwartaaltests om nieuwe kwetsbaarheden tijdig te ontdekken.", "command": "", "verify": "", "estimated_time": "doorlopend"},
            {"title": "Implementeer een vulnerability management programma", "description": "Stel een proces in voor het opsporen, beoordelen en verhelpen van kwetsbaarheden.", "command": "", "verify": "", "estimated_time": "2–4 weken"},
        ]

    return quick_wins, short_term, long_term


# ── Main public functions ─────────────────────────────────────────────────────

def generate_pentest_report(scan_id: str) -> Path | None:
    """Generate a professional pentest report (HTML + PDF)."""
    scan_dir = Config.SCANS_DIR / scan_id
    scan_data, analysis = _load_scan(scan_id)

    if not scan_data:
        logger.error("No scan data found for %s", scan_id)
        return None

    if not analysis:
        analysis = _generate_basic_analysis(scan_data)

    report_data = format_for_pdf(analysis, scan_data)
    findings = _all_findings(scan_data)

    risk_score = analysis.get("samenvatting", {}).get("risicoscore", 0) or report_data.get("risk_score", 0) or 0
    risk_level_raw = (analysis.get("samenvatting", {}).get("niveau") or report_data.get("risk_level") or "laag").lower()
    risk_level_map = {"veilig": "low", "laag": "low", "low": "low",
                      "gemiddeld": "medium", "medium": "medium",
                      "hoog": "high", "high": "high",
                      "kritiek": "critical", "critical": "critical"}
    risk_level = risk_level_map.get(risk_level_raw, "low")

    mgmt = (analysis.get("management_samenvatting") or
            analysis.get("executive_summary") or
            report_data.get("management_summary", ""))

    modules_run = [
        {"module_id": r.get("module_id", ""), "name": r.get("name", ""), "phase": r.get("phase", ""), "findings": r.get("findings", [])}
        for r in scan_data.get("results", [])
    ]

    ctx = {
        "target":       scan_data.get("target", ""),
        "scan_type":    scan_data.get("scan_type", ""),
        "scan_mode":    scan_data.get("scan_mode", ""),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "risk_score":   risk_score,
        "risk_level":   risk_level,
        "management_summary": mgmt,
        "bevindingen":  findings,
        "critical_count": _count_sev(findings, "critical"),
        "high_count":     _count_sev(findings, "high"),
        "medium_count":   _count_sev(findings, "medium"),
        "low_count":      _count_sev(findings, "low"),
        "info_count":     _count_sev(findings, "info"),
        "technische_details": report_data.get("technische_details", ""),
        "modules_run":  modules_run,
    }

    template_dir = Config.ROOT_DIR / "reports" / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)
    html_path = scan_dir / "pentest_report.html"

    try:
        tmpl = env.get_template("pentest_report.html")
    except Exception:
        tmpl = env.get_template("report.html")  # fallback
    html = tmpl.render(**ctx)
    html_path.write_text(html, encoding="utf-8")

    pdf = _render_to_pdf(html_path)
    logger.info("Pentest report: %s", pdf or html_path)
    return pdf or html_path


def generate_secure_solution(scan_id: str) -> Path | None:
    """Generate a secure solution / remediation document (HTML + PDF)."""
    scan_dir = Config.SCANS_DIR / scan_id
    scan_data, analysis = _load_scan(scan_id)

    if not scan_data:
        logger.error("No scan data for secure solution %s", scan_id)
        return None

    if not analysis:
        analysis = _generate_basic_analysis(scan_data)

    findings = _all_findings(scan_data)
    quick_wins, short_term, long_term = _build_remediation(analysis, findings)

    ctx = {
        "target":       scan_data.get("target", ""),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "quick_wins":   quick_wins,
        "short_term":   short_term,
        "long_term":    long_term,
        "remediation_findings": [f for f in findings if f["ernst"] in ("critical", "high", "medium")][:30],
    }

    template_dir = Config.ROOT_DIR / "reports" / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)
    html_path = scan_dir / "secure_solution.html"

    try:
        tmpl = env.get_template("secure_solution.html")
    except Exception:
        logger.warning("secure_solution.html template missing — skipping")
        return None
    html = tmpl.render(**ctx)
    html_path.write_text(html, encoding="utf-8")

    pdf = _render_to_pdf(html_path)
    logger.info("Secure solution: %s", pdf or html_path)
    return pdf or html_path


def generate_pdf(scan_id: str) -> Path | None:
    """Legacy entry point — generates pentest_report + secure_solution + legacy report.html."""
    scan_dir = Config.SCANS_DIR / scan_id
    scan_data, analysis = _load_scan(scan_id)

    if not scan_data:
        logger.error("Scan data not found: %s", scan_id)
        return None

    if not analysis:
        analysis = _generate_basic_analysis(scan_data)

    # Generate both new documents
    pentest_path = generate_pentest_report(scan_id)
    secure_path = generate_secure_solution(scan_id)

    # Also generate legacy report.html for backwards compatibility
    try:
        report_data = format_for_pdf(analysis, scan_data)
        report_data["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        template_dir = Config.ROOT_DIR / "reports" / "templates"
        env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)
        try:
            template = env.get_template("report.html")
            html_content = template.render(**report_data)
            legacy_html = scan_dir / "report.html"
            legacy_html.write_text(html_content, encoding="utf-8")
            legacy_pdf = _render_to_pdf(legacy_html)
            if legacy_pdf:
                (scan_dir / "report.pdf").unlink(missing_ok=True)
                legacy_pdf.rename(scan_dir / "report.pdf")
        except Exception:
            pass
    except Exception as e:
        logger.warning("Legacy report generation failed: %s", e)

    return pentest_path or secure_path


# ── Basic analysis fallback ───────────────────────────────────────────────────

def _generate_basic_analysis(scan_data: dict) -> dict:
    """Generate a minimal analysis when DeepSeek is unavailable."""
    results = scan_data.get("results", [])
    all_f: list[dict] = []
    for r in results:
        for f in r.get("findings", []):
            all_f.append({
                "titel":        f.get("title") or f.get("type") or "Bevinding",
                "ernst":        f.get("severity") or f.get("ernst") or "info",
                "beschrijving": f.get("description") or f.get("beschrijving") or f.get("detail") or str(f)[:300],
                "impact":       f.get("impact", ""),
                "aanbeveling":  f.get("recommendation") or f.get("aanbeveling", ""),
                "referenties":  f.get("references") or f.get("referenties", []),
                "cve":          f.get("cve", ""),
            })

    counts: dict[str, int] = {}
    for f in all_f:
        s = (f["ernst"] or "info").lower()
        counts[s] = counts.get(s, 0) + 1

    critical = counts.get("critical", 0)
    high     = counts.get("high", 0)
    medium   = counts.get("medium", 0)
    score    = min(100, critical * 20 + high * 10 + medium * 5)
    niveau   = ("kritiek" if score >= 80 else "hoog" if score >= 60
                else "gemiddeld" if score >= 40 else "laag" if score >= 20 else "veilig")

    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    all_f.sort(key=lambda x: sev_order.get((x["ernst"] or "info").lower(), 5))

    return {
        "samenvatting": {"risicoscore": score, "niveau": niveau,
                         "korte_beschrijving": f"{len(all_f)} bevindingen gevonden ({critical}K / {high}H / {medium}M)."},
        "management_samenvatting": (
            f"De penetratietest heeft {len(all_f)} bevindingen opgeleverd voor {scan_data.get('target', 'het doelwit')}. "
            f"Hiervan zijn er {critical} kritiek, {high} hoog en {medium} gemiddeld. "
            f"Aanbevolen wordt de kritieke en hoge bevindingen zo spoedig mogelijk te verhelpen."
        ),
        "bevindingen": all_f,
        "aanbevelingen_prioriteit": [],
        "technische_details": (
            f"Scan: {scan_data.get('target')}\n"
            f"Type: {scan_data.get('scan_type','')}\n"
            f"Modus: {scan_data.get('scan_mode','')}\n"
            f"Modules: {len(results)}\n"
        ),
    }
