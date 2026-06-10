"""PDF report generation using reportlab (pure Python, no system deps)."""

import io
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Severity colour map
_SEV_COLORS = {
    "critical": (0.86, 0.08, 0.24),
    "high":     (0.95, 0.43, 0.05),
    "medium":   (0.85, 0.65, 0.13),
    "low":      (0.13, 0.55, 0.13),
    "info":     (0.40, 0.40, 0.40),
}


def generate_pdf_report(
    report_data: dict,
    target: str,
    scan_type: str,
    white_label: bool = False,
    company_name: str = "",
) -> bytes:
    """Generate a PDF security report using reportlab.

    Falls back to returning HTML bytes if reportlab is not installed
    (should never happen in the Docker image).
    """
    try:
        return _build_pdf(report_data, target, scan_type, white_label, company_name)
    except ImportError:
        logger.warning("reportlab not available — returning HTML fallback")
        return _build_html_fallback(report_data, target, scan_type).encode("utf-8")
    except Exception as exc:
        logger.error("PDF generation failed: %s", exc)
        return _build_html_fallback(report_data, target, scan_type).encode("utf-8")


def _build_pdf(report_data: dict, target: str, scan_type: str,
               white_label: bool, company_name: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title="CyberPulse Security Report",
        author=company_name or "CyberPulse",
    )

    base = getSampleStyleSheet()
    styles = {
        "title":    ParagraphStyle("title",    fontSize=28, leading=34, textColor=colors.HexColor("#1e3a5f"),  spaceAfter=6,  alignment=TA_CENTER, fontName="Helvetica-Bold"),
        "subtitle": ParagraphStyle("subtitle", fontSize=14, leading=18, textColor=colors.HexColor("#6b7280"),  spaceAfter=20, alignment=TA_CENTER),
        "h1":       ParagraphStyle("h1",       fontSize=16, leading=20, textColor=colors.HexColor("#1e3a5f"),  spaceAfter=8,  spaceBefore=16, fontName="Helvetica-Bold"),
        "h2":       ParagraphStyle("h2",       fontSize=12, leading=16, textColor=colors.HexColor("#2563eb"),  spaceAfter=6,  spaceBefore=10, fontName="Helvetica-Bold"),
        "body":     ParagraphStyle("body",     fontSize=9,  leading=13, textColor=colors.HexColor("#1f2937"),  spaceAfter=6),
        "small":    ParagraphStyle("small",    fontSize=8,  leading=11, textColor=colors.HexColor("#6b7280"),  spaceAfter=4),
        "code":     ParagraphStyle("code",     fontSize=8,  leading=11, textColor=colors.HexColor("#111827"),  fontName="Courier", spaceAfter=4),
    }

    story = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    brand = company_name if (white_label and company_name) else "CyberPulse"

    # ── Cover page ──────────────────────────────────────────────────────────────
    story.append(Spacer(1, 5*cm))
    story.append(Paragraph(brand, styles["title"]))
    story.append(Paragraph("Security Assessment Report", styles["subtitle"]))
    story.append(HRFlowable(width="80%", thickness=1, color=colors.HexColor("#1e3a5f"), hAlign="CENTER"))
    story.append(Spacer(1, 1*cm))

    meta_data = [
        ["Target:", target or "—"],
        ["Scan Type:", (scan_type or "").replace("_", " ").title()],
        ["Report Date:", now],
        ["Classification:", "CONFIDENTIAL"],
    ]
    meta_tbl = Table(meta_data, colWidths=[4*cm, 12*cm])
    meta_tbl.setStyle(TableStyle([
        ("FONTSIZE",   (0,0), (-1,-1), 9),
        ("FONTNAME",   (0,0), (0,-1), "Helvetica-Bold"),
        ("TEXTCOLOR",  (0,0), (0,-1), colors.HexColor("#374151")),
        ("TEXTCOLOR",  (1,3), (1,3),  colors.HexColor("#dc2626")),
        ("FONTNAME",   (1,3), (1,3),  "Helvetica-Bold"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(meta_tbl)
    story.append(PageBreak())

    # ── Executive Summary ───────────────────────────────────────────────────────
    story.append(Paragraph("Executive Summary", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1e3a5f")))
    story.append(Spacer(1, 0.3*cm))

    # Risk score gauge
    risk_score  = report_data.get("risk_score", 0)
    risk_level  = (report_data.get("risk_level") or "LOW").upper()
    sec_score   = 100 - risk_score

    score_color = colors.HexColor(
        "#dc2626" if risk_score >= 70 else
        "#ea580c" if risk_score >= 40 else
        "#16a34a"
    )
    score_data = [["Security Score", "Risk Score", "Risk Level"]]
    score_data.append([f"{sec_score}/100", f"{risk_score}/100", risk_level])
    score_tbl = Table(score_data, colWidths=[6*cm, 6*cm, 6*cm])
    score_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0),  colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR",   (0,0), (-1,0),  colors.white),
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 11),
        ("FONTNAME",    (0,1), (-1,1),  "Helvetica-Bold"),
        ("FONTSIZE",    (0,1), (-1,1),  16),
        ("TEXTCOLOR",   (2,1), (2,1),   score_color),
        ("ALIGN",       (0,0), (-1,-1), "CENTER"),
        ("TOPPADDING",  (0,0), (-1,-1), 10),
        ("BOTTOMPADDING",(0,0),(-1,-1), 10),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
    ]))
    story.append(score_tbl)
    story.append(Spacer(1, 0.5*cm))

    # Finding counts table
    crit = report_data.get("critical_count", 0) or len([f for f in report_data.get("findings",[]) if (f.get("severity") or "").upper() == "CRITICAL"])
    high = report_data.get("high_count",     0) or len([f for f in report_data.get("findings",[]) if (f.get("severity") or "").upper() == "HIGH"])
    med  = report_data.get("medium_count",   0) or len([f for f in report_data.get("findings",[]) if (f.get("severity") or "").upper() == "MEDIUM"])
    low  = report_data.get("low_count",      0) or len([f for f in report_data.get("findings",[]) if (f.get("severity") or "").upper() == "LOW"])

    # Also pull from finding_counts if present
    fc = report_data.get("finding_counts") or {}
    crit = crit or fc.get("critical", 0)
    high = high or fc.get("high", 0)
    med  = med  or fc.get("medium", 0)
    low  = low  or fc.get("low", 0)

    findings_tbl = Table(
        [["Severity", "Count"],
         ["CRITICAL", str(crit)],
         ["HIGH",     str(high)],
         ["MEDIUM",   str(med)],
         ["LOW",      str(low)]],
        colWidths=[8*cm, 8*cm],
    )
    findings_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0),  colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR",    (0,0), (-1,0),  colors.white),
        ("FONTNAME",     (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 10),
        ("TEXTCOLOR",    (0,1), (0,1),   colors.HexColor("#dc2626")),
        ("TEXTCOLOR",    (0,2), (0,2),   colors.HexColor("#ea580c")),
        ("TEXTCOLOR",    (0,3), (0,3),   colors.HexColor("#ca8a04")),
        ("TEXTCOLOR",    (0,4), (0,4),   colors.HexColor("#2563eb")),
        ("FONTNAME",     (0,1), (0,-1),  "Helvetica-Bold"),
        ("ALIGN",        (1,0), (1,-1),  "CENTER"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, colors.HexColor("#f9fafb")]),
        ("GRID",         (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
        ("TOPPADDING",   (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0), (-1,-1), 6),
    ]))
    story.append(findings_tbl)
    story.append(Spacer(1, 0.5*cm))

    # Management summary
    mgmt = (
        report_data.get("management_summary") or
        report_data.get("executive_summary") or
        report_data.get("managementsamenvatting") or
        report_data.get("samenvatting", {}).get("korte_beschrijving", "") or
        ""
    )
    if mgmt:
        story.append(Paragraph("Management Summary", styles["h2"]))
        story.append(Paragraph(str(mgmt)[:2000], styles["body"]))

    # Technical summary
    tech = (
        report_data.get("technical_summary") or
        report_data.get("technische_details") or
        ""
    )
    if tech:
        story.append(Paragraph("Technical Summary", styles["h2"]))
        story.append(Paragraph(str(tech)[:2000], styles["body"]))

    # ── Detailed Findings ───────────────────────────────────────────────────────
    findings = report_data.get("findings") or report_data.get("bevindingen") or []
    if findings:
        story.append(PageBreak())
        story.append(Paragraph("Detailed Findings", styles["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1e3a5f")))

        for i, f in enumerate(findings[:30], 1):  # cap at 30
            sev = (f.get("severity") or f.get("ernst") or "info").upper()
            sev_color = colors.HexColor({
                "CRITICAL": "#dc2626", "HIGH": "#ea580c",
                "MEDIUM": "#ca8a04", "LOW": "#2563eb",
            }.get(sev, "#6b7280"))

            title = f.get("title") or f.get("titel") or f.get("type") or f"Finding {i}"
            desc  = f.get("description") or f.get("beschrijving") or f.get("detail") or ""
            rec   = f.get("recommendation") or f.get("aanbeveling") or ""
            impact = f.get("impact") or ""
            cve   = f.get("cve") or f.get("CVE") or ""

            story.append(Spacer(1, 0.3*cm))
            # Finding header row
            hdr = Table(
                [[f"{i}. {title}", sev]],
                colWidths=[14*cm, 2.5*cm],
            )
            hdr.setStyle(TableStyle([
                ("BACKGROUND",   (0,0), (-1,-1), colors.HexColor("#f9fafb")),
                ("FONTNAME",     (0,0), (0,0),   "Helvetica-Bold"),
                ("FONTSIZE",     (0,0), (-1,-1),  9),
                ("TEXTCOLOR",    (1,0), (1,0),   sev_color),
                ("FONTNAME",     (1,0), (1,0),   "Helvetica-Bold"),
                ("ALIGN",        (1,0), (1,0),   "CENTER"),
                ("TOPPADDING",   (0,0), (-1,-1),  6),
                ("BOTTOMPADDING",(0,0), (-1,-1),  6),
                ("LEFTPADDING",  (0,0), (-1,-1),  8),
                ("BOX",          (0,0), (-1,-1),  0.5, colors.HexColor("#e5e7eb")),
            ]))
            story.append(hdr)

            if cve:
                story.append(Paragraph(f"<b>CVE:</b> {cve}", styles["small"]))
            if desc:
                story.append(Paragraph(f"<b>Description:</b> {str(desc)[:500]}", styles["body"]))
            if impact:
                story.append(Paragraph(f"<b>Impact:</b> {str(impact)[:300]}", styles["body"]))
            if rec:
                story.append(Paragraph(f"<b>Recommendation:</b> {str(rec)[:500]}", styles["body"]))

    # ── Remediation Roadmap ─────────────────────────────────────────────────────
    roadmap = report_data.get("remediation_roadmap") or {}
    if roadmap:
        story.append(PageBreak())
        story.append(Paragraph("Remediation Roadmap", styles["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1e3a5f")))

        for section_key, section_label in [
            ("quick_wins", "Quick Wins (< 1 day)"),
            ("short_term", "Short Term (< 1 week)"),
            ("long_term",  "Long Term (< 1 month)"),
        ]:
            items = roadmap.get(section_key, [])
            if not items:
                continue
            story.append(Paragraph(section_label, styles["h2"]))
            for item in items:
                if isinstance(item, dict):
                    t = item.get("title", "")
                    steps = item.get("steps", [])
                    story.append(Paragraph(f"<b>{t}</b>", styles["body"]))
                    for s in steps:
                        story.append(Paragraph(f"  • {s}", styles["body"]))
                else:
                    story.append(Paragraph(f"• {item}", styles["body"]))

    doc.build(story)
    return buf.getvalue()


def _build_html_fallback(report_data: dict, target: str, scan_type: str) -> str:
    """Minimal HTML fallback when reportlab fails."""
    findings = report_data.get("findings") or []
    rows = "".join(
        f"<tr><td>{f.get('title','')}</td><td>{f.get('severity','')}</td>"
        f"<td>{f.get('description','')[:200]}</td></tr>"
        for f in findings
    )
    return f"""<!DOCTYPE html><html><head><meta charset='utf-8'>
<title>CyberPulse Report — {target}</title>
<style>body{{font-family:sans-serif;padding:2em}}table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ccc;padding:.5em}}</style></head><body>
<h1>CyberPulse Security Report</h1>
<p><b>Target:</b> {target} &nbsp; <b>Type:</b> {scan_type}</p>
<p><b>Risk Score:</b> {report_data.get('risk_score',0)}/100 — {report_data.get('risk_level','')}</p>
<p>{report_data.get('management_summary','')}</p>
<h2>Findings ({len(findings)})</h2>
<table><tr><th>Title</th><th>Severity</th><th>Description</th></tr>{rows}</table>
</body></html>"""
