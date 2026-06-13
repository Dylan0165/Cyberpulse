"""NIS2 compliance PDF report generation using reportlab (pure Python, no system deps).

All report text is in Dutch. Findings are mapped to NIS2 articles (Art. 21(2))
and each article receives a compliance status.
"""

import io
import logging

logger = logging.getLogger(__name__)

# Status colours (RGB hex)
_STATUS_COLOR = {
    "COMPLIANT": "#16a34a",      # green
    "AANDACHT": "#ea580c",       # orange
    "NON-COMPLIANT": "#dc2626",  # red
}

# Dutch label for overall status
_OVERALL_LABEL = {
    "COMPLIANT": "VOLDOET",
    "AANDACHT": "GEDEELTELIJK",
    "NON-COMPLIANT": "VOLDOET NIET",
}

# Worst-of ordering (higher = worse)
_STATUS_RANK = {"COMPLIANT": 0, "AANDACHT": 1, "NON-COMPLIANT": 2}


def generate_nis2_report(report_data: dict, target: str, scan_date: str) -> bytes:
    """Generate a NIS2 compliance PDF report.

    Always returns PDF bytes. On any error a minimal fallback PDF is returned.
    """
    try:
        return _build_nis2_pdf(report_data, target, scan_date)
    except Exception as exc:  # noqa: BLE001 - never raise, always return bytes
        logger.error("NIS2 PDF generation failed: %s", exc)
        try:
            return _build_fallback_pdf(target, scan_date)
        except Exception as exc2:  # noqa: BLE001
            logger.error("NIS2 fallback PDF generation failed: %s", exc2)
            # Absolute last resort: a hand-written minimal valid PDF.
            return (
                b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
                b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]>>endobj\n"
                b"trailer<</Root 1 0 R>>\n%%EOF"
            )


def _finding_text(finding: dict) -> str:
    """Concatenate the relevant fields of a finding into one lowercase string."""
    parts = []
    for key in ("type", "title", "titel", "owasp", "owasp_category", "tool",
                "service", "description", "beschrijving", "name"):
        val = finding.get(key)
        if val:
            parts.append(str(val))
    return " ".join(parts).lower()


def _analyse(report_data: dict) -> dict:
    """Derive severity counts and category flags from report_data."""
    findings = report_data.get("findings") or report_data.get("bevindingen") or []

    critical = high = medium = low = 0
    for f in findings:
        sev = str(f.get("severity") or f.get("ernst") or f.get("risk_level") or "").upper()
        if sev == "CRITICAL":
            critical += 1
        elif sev == "HIGH":
            high += 1
        elif sev == "MEDIUM":
            medium += 1
        elif sev == "LOW":
            low += 1

    auth_kw = ("credential", "hydra", "login", "admin", "auth")
    secret_kw = ("secret", "gitleaks", ".env", "theharvester", "osint")
    ssl_kw = ("ssl", "tls", "testssl", "https", "certificate")

    auth_issue = False
    secret_issue = False
    ssl_issue = False
    auth_findings = []
    secret_findings = []
    ssl_findings = []

    for f in findings:
        text = _finding_text(f)
        title = f.get("title") or f.get("titel") or f.get("type") or "Bevinding"
        if any(k in text for k in auth_kw):
            auth_issue = True
            auth_findings.append(title)
        if any(k in text for k in secret_kw):
            secret_issue = True
            secret_findings.append(title)
        if any(k in text for k in ssl_kw):
            ssl_issue = True
            ssl_findings.append(title)

    return {
        "findings": findings,
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
        "auth_issue": auth_issue,
        "secret_issue": secret_issue,
        "ssl_issue": ssl_issue,
        "auth_findings": auth_findings,
        "secret_findings": secret_findings,
        "ssl_findings": ssl_findings,
    }


def _build_articles(a: dict) -> list:
    """Build the list of NIS2 article dicts with status, triggers and advice."""
    # Art. 21(2)(a)
    if a["critical"] > 0 or a["high"] > 0:
        status_a = "NON-COMPLIANT"
    elif a["medium"] > 0:
        status_a = "AANDACHT"
    else:
        status_a = "COMPLIANT"
    triggers_a = []
    for f in a["findings"]:
        sev = str(f.get("severity") or f.get("ernst") or f.get("risk_level") or "").upper()
        if sev in ("CRITICAL", "HIGH", "MEDIUM"):
            triggers_a.append(f.get("title") or f.get("titel") or f.get("type") or "Bevinding")

    # Art. 21(2)(b)
    status_b = "NON-COMPLIANT" if a["auth_issue"] else "COMPLIANT"

    # Art. 21(2)(e)
    status_e = "NON-COMPLIANT" if a["secret_issue"] else "COMPLIANT"

    # Art. 21(2)(h)
    status_h = "NON-COMPLIANT" if a["ssl_issue"] else "COMPLIANT"

    return [
        {
            "number": "Art. 21(2)(a)",
            "title": "Risicoanalyse en beveiligingsbeleid",
            "status": status_a,
            "triggers": triggers_a,
            "advice": (
                "Stel een formeel beleid op voor risicoanalyse en informatiebeveiliging. "
                "Pak kritieke en hoge bevindingen prioritair aan en evalueer het beleid "
                "periodiek." if status_a != "COMPLIANT" else
                "Het risicobeleid lijkt op orde. Blijf de risicoanalyse periodiek herhalen "
                "en actueel houden."
            ),
        },
        {
            "number": "Art. 21(2)(b)",
            "title": "Incidentafhandeling",
            "status": status_b,
            "triggers": a["auth_findings"],
            "advice": (
                "Versterk de toegangsbeveiliging en authenticatie en implementeer een "
                "procedure voor incidentdetectie en -afhandeling, inclusief logging en "
                "meldingsplicht." if status_b != "COMPLIANT" else
                "Er zijn geen authenticatie- of toegangsproblemen aangetroffen. Onderhoud "
                "het incidentafhandelingsproces."
            ),
        },
        {
            "number": "Art. 21(2)(e)",
            "title": "Beveiliging van de toeleveringsketen",
            "status": status_e,
            "triggers": a["secret_findings"],
            "advice": (
                "Verwijder blootgestelde geheimen en inloggegevens en beheer secrets in een "
                "veilige kluis. Beoordeel de beveiliging van leveranciers en externe "
                "componenten." if status_e != "COMPLIANT" else
                "Er zijn geen blootgestelde geheimen aangetroffen. Blijf secrets en "
                "leveranciersbeveiliging monitoren."
            ),
        },
        {
            "number": "Art. 21(2)(h)",
            "title": "Cryptografie en encryptie",
            "status": status_h,
            "triggers": a["ssl_findings"],
            "advice": (
                "Configureer geldige TLS-certificaten, schakel verouderde protocollen uit en "
                "forceer versleutelde verbindingen (HTTPS)." if status_h != "COMPLIANT" else
                "Er zijn geen problemen met cryptografie of encryptie aangetroffen. Houd "
                "certificaten en protocollen up-to-date."
            ),
        },
    ]


def _build_nis2_pdf(report_data: dict, target: str, scan_date: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    a = _analyse(report_data)
    articles = _build_articles(a)

    overall = "COMPLIANT"
    for art in articles:
        if _STATUS_RANK[art["status"]] > _STATUS_RANK[overall]:
            overall = art["status"]
    overall_label = _OVERALL_LABEL[overall]

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title="CyberPulse NIS2 Compliancerapport",
        author="CyberPulse",
    )

    styles = {
        "title": ParagraphStyle("title", fontSize=28, leading=34, textColor=colors.HexColor("#1e3a5f"), spaceAfter=6, alignment=TA_CENTER, fontName="Helvetica-Bold"),
        "subtitle": ParagraphStyle("subtitle", fontSize=15, leading=19, textColor=colors.HexColor("#6b7280"), spaceAfter=20, alignment=TA_CENTER, fontName="Helvetica-Bold"),
        "h1": ParagraphStyle("h1", fontSize=15, leading=19, textColor=colors.HexColor("#1e3a5f"), spaceAfter=8, spaceBefore=14, fontName="Helvetica-Bold"),
        "h2": ParagraphStyle("h2", fontSize=12, leading=16, textColor=colors.HexColor("#2563eb"), spaceAfter=6, spaceBefore=8, fontName="Helvetica-Bold"),
        "body": ParagraphStyle("body", fontSize=9, leading=13, textColor=colors.HexColor("#1f2937"), spaceAfter=6),
        "small": ParagraphStyle("small", fontSize=8, leading=11, textColor=colors.HexColor("#6b7280"), spaceAfter=4),
        "center": ParagraphStyle("center", fontSize=10, leading=14, textColor=colors.HexColor("#374151"), alignment=TA_CENTER, spaceAfter=4),
    }

    def _badge(status: str):
        """Return a small one-cell Table acting as a colored status badge."""
        label = status
        tbl = Table([[label]], colWidths=[5 * cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(_STATUS_COLOR.get(status, "#6b7280"))),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return tbl

    story = []

    # ── Cover page ──────────────────────────────────────────────────────────────
    story.append(Spacer(1, 4 * cm))
    story.append(Paragraph("CyberPulse", styles["title"]))
    story.append(Paragraph("NIS2 Compliancerapport", styles["subtitle"]))
    story.append(HRFlowable(width="80%", thickness=1, color=colors.HexColor("#1e3a5f"), hAlign="CENTER"))
    story.append(Spacer(1, 1 * cm))

    meta = [
        ["Organisatie:", target or "—"],
        ["Datum:", scan_date or "—"],
        ["Classificatie:", "VERTROUWELIJK"],
    ]
    meta_tbl = Table(meta, colWidths=[4 * cm, 12 * cm])
    meta_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#374151")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 1.2 * cm))

    story.append(Paragraph("Algehele NIS2-status", styles["center"]))
    story.append(Spacer(1, 0.2 * cm))
    overall_badge = Table([[overall_label]], colWidths=[8 * cm], hAlign="CENTER")
    overall_badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(_STATUS_COLOR.get(overall, "#6b7280"))),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 18),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(overall_badge)

    story.append(PageBreak())

    # ── Per-article sections ────────────────────────────────────────────────────
    story.append(Paragraph("Beoordeling per NIS2-artikel", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1e3a5f")))
    story.append(Spacer(1, 0.3 * cm))

    for art in articles:
        story.append(Paragraph(f"{art['number']} — {art['title']}", styles["h2"]))
        story.append(_badge(art["status"]))
        story.append(Spacer(1, 0.2 * cm))

        triggers = art.get("triggers") or []
        if triggers:
            story.append(Paragraph("Bevindingen die deze status veroorzaken:", styles["body"]))
            for t in triggers[:15]:
                story.append(Paragraph(f"• {str(t)[:200]}", styles["body"]))
        else:
            story.append(Paragraph("Geen relevante bevindingen aangetroffen.", styles["body"]))

        story.append(Paragraph(f"<b>Aanbeveling:</b> {art['advice']}", styles["body"]))
        story.append(Spacer(1, 0.3 * cm))

    # ── Final page: summary table + disclaimer ──────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Samenvatting", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1e3a5f")))
    story.append(Spacer(1, 0.3 * cm))

    table_data = [["Artikel", "Status"]]
    for art in articles:
        table_data.append([f"{art['number']} — {art['title']}", art["status"]])
    summary_tbl = Table(table_data, colWidths=[12 * cm, 5 * cm])
    summary_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for idx, art in enumerate(articles, start=1):
        summary_style.append(
            ("TEXTCOLOR", (1, idx), (1, idx), colors.HexColor(_STATUS_COLOR.get(art["status"], "#6b7280")))
        )
    summary_tbl.setStyle(TableStyle(summary_style))
    story.append(summary_tbl)
    story.append(Spacer(1, 1 * cm))

    story.append(Paragraph(
        "Dit rapport is gegenereerd door CyberPulse en dient als indicatief overzicht. "
        "Voor officiële NIS2-certificering is een gecertificeerde audit vereist.",
        styles["small"],
    ))

    doc.build(story)
    return buf.getvalue()


def _build_fallback_pdf(target: str, scan_date: str) -> bytes:
    """Minimal valid PDF built with reportlab when the full build fails."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("CyberPulse — NIS2 Compliancerapport", styles["Title"]),
        Spacer(1, 1 * cm),
        Paragraph(f"Organisatie: {target or '—'}", styles["Normal"]),
        Paragraph(f"Datum: {scan_date or '—'}", styles["Normal"]),
        Spacer(1, 1 * cm),
        Paragraph(
            "Het volledige rapport kon niet worden gegenereerd. Neem contact op met de beheerder.",
            styles["Normal"],
        ),
    ]
    doc.build(story)
    return buf.getvalue()
