"""PDF Report Generator — creates professional pentest reports using xhtml2pdf."""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from config import Config
from ai.formatter import format_for_pdf

logger = logging.getLogger("cyberpulse.reports.generator")

# CSS custom property values (mirrors the :root block in report.html)
_CSS_VARS = {
    "--black":    "#000000",
    "--white":    "#ffffff",
    "--gray-1":   "#111111",
    "--gray-2":   "#333333",
    "--gray-3":   "#666666",
    "--gray-4":   "#999999",
    "--gray-5":   "#cccccc",
    "--gray-6":   "#eeeeee",
    "--critical": "#cc0000",
    "--high":     "#cc6600",
    "--medium":   "#999900",
    "--low":      "#666666",
}


def _prepare_html_for_pdf(html: str) -> str:
    """Strip features unsupported by xhtml2pdf: CSS variables, Google Fonts, flex."""
    # Remove Google Fonts @import (xhtml2pdf can't fetch external URLs)
    html = re.sub(r"@import\s+url\([^)]+\);?", "", html)

    # Replace var(--name) with literal values
    def replace_var(m: re.Match) -> str:
        return _CSS_VARS.get(m.group(1), m.group(0))

    html = re.sub(r"var\((--[\w-]+)\)", replace_var, html)

    # Replace web fonts with safe system fallbacks
    html = html.replace("'JetBrains Mono'", "Courier")
    html = html.replace("'Crimson Pro'", "Times New Roman")
    html = html.replace('"JetBrains Mono"', "Courier")

    # Remove :root block (no longer needed)
    html = re.sub(r":root\s*\{[^}]*\}", "", html, flags=re.DOTALL)

    # Replace display:flex with display:block (xhtml2pdf doesn't support flex)
    html = re.sub(r"display\s*:\s*flex\s*;?", "display: block;", html)
    html = re.sub(r"flex-direction\s*:[^;]+;?", "", html)
    html = re.sub(r"justify-content\s*:[^;]+;?", "", html)
    html = re.sub(r"align-items\s*:[^;]+;?", "", html)
    html = re.sub(r"\bflex\s*:\s*\d+\s*;?", "", html)
    html = re.sub(r"\bgap\s*:[^;]+;?", "", html)

    return html

def generate_pdf(scan_id: str) -> Path | None:
    """Generate a PDF report for a completed scan.

    Args:
        scan_id: The scan identifier (directory name under SCANS_DIR).

    Returns:
        Path to the generated PDF, or None on failure.
    """
    scan_dir = Config.SCANS_DIR / scan_id

    # Load scan data
    scan_data_file = scan_dir / "scan_data.json"
    if not scan_data_file.exists():
        logger.error("Scan data not found: %s", scan_data_file)
        return None

    with open(scan_data_file, "r", encoding="utf-8") as f:
        scan_data = json.load(f)

    # Load AI analysis
    analysis_file = scan_dir / "analysis.json"
    analysis = {}
    if analysis_file.exists():
        with open(analysis_file, "r", encoding="utf-8") as f:
            analysis = json.load(f)
    else:
        logger.warning("No AI analysis found for scan %s, generating basic report", scan_id)
        analysis = _generate_basic_analysis(scan_data)

    # Format data for PDF
    report_data = format_for_pdf(analysis, scan_data)
    report_data["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Render HTML from template
    template_dir = Config.ROOT_DIR / "reports" / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)
    template = env.get_template("report.html")
    html_content = template.render(**report_data)

    # Save HTML version
    html_path = scan_dir / "report.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Generate PDF
    pdf_path = scan_dir / "report.pdf"
    try:
        from xhtml2pdf import pisa
        import logging as _logging
        _logging.getLogger("xhtml2pdf").setLevel(_logging.ERROR)

        pdf_html = _prepare_html_for_pdf(html_content)
        with open(pdf_path, "wb") as pdf_file:
            result = pisa.CreatePDF(
                pdf_html.encode("utf-8"),
                dest=pdf_file,
                encoding="utf-8",
            )
        if result.err:
            logger.error("xhtml2pdf reported errors: %s", result.err)
            pdf_path.unlink(missing_ok=True)
            return html_path
        logger.info("PDF report generated: %s", pdf_path)
        return pdf_path
    except Exception as e:
        logger.error("PDF generation failed: %s", e)
        if pdf_path.exists():
            pdf_path.unlink(missing_ok=True)
        return html_path


def _generate_basic_analysis(scan_data: dict) -> dict:
    """Generate a basic analysis without AI when DeepSeek is unavailable."""
    results = scan_data.get("results", [])
    all_findings = []
    for result in results:
        mod_id = result.get("module_id", result.get("name", ""))
        for f in result.get("findings", []):
            # Normalise field names so the PDF template always has 'titel', 'ernst', etc.
            all_findings.append({
                "titel":        f.get("title") or f.get("type") or f.get("name", "Bevinding"),
                "module":       mod_id,
                "ernst":        f.get("severity") or f.get("ernst", "info"),
                "beschrijving": f.get("description") or f.get("beschrijving") or f.get("detail") or str(f)[:300],
                "impact":       f.get("impact", ""),
                "aanbeveling":  f.get("recommendation") or f.get("aanbeveling", ""),
                "referenties":  f.get("references") or f.get("referenties", []),
                "cve":          f.get("cve", ""),
            })

    # Count severities
    counts: dict[str, int] = {}
    for f in all_findings:
        s = f["ernst"]
        counts[s] = counts.get(s, 0) + 1

    critical = counts.get("critical", 0)
    high = counts.get("high", 0)
    medium = counts.get("medium", 0)

    score = min(100, critical * 20 + high * 10 + medium * 5)
    niveau = "kritiek" if score >= 80 else "hoog" if score >= 60 else "gemiddeld" if score >= 40 else "laag" if score >= 20 else "veilig"

    # Sort by severity
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    all_findings.sort(key=lambda x: sev_order.get(x["ernst"], 5))

    return {
        "samenvatting": {
            "risicoscore": score,
            "niveau": niveau,
            "korte_beschrijving": f"Er zijn {len(all_findings)} bevindingen gevonden, waarvan {critical} kritiek en {high} hoog.",
        },
        "management_samenvatting": (
            f"De penetratietest heeft {len(all_findings)} bevindingen opgeleverd voor {scan_data.get('target', 'het doelwit')}. "
            f"Hiervan zijn er {critical} als kritiek, {high} als hoog en {medium} als gemiddeld geclassificeerd. "
            f"Het wordt aanbevolen om de kritieke en hoge bevindingen zo snel mogelijk te verhelpen. "
            f"AI-analyse was niet beschikbaar; dit rapport bevat de volledige ruwe scanresultaten."
        ),
        "bevindingen": all_findings,   # all findings, not capped at 20
        "aanbevelingen_prioriteit": [],
        "technische_details": f"Scan uitgevoerd op: {scan_data.get('target')}\n"
                              f"Modules: {len(results)}\n"
                              f"Scantype: {scan_data.get('scan_type', '')}\n"
                              f"Modus: {scan_data.get('scan_mode', '')}\n",
    }
