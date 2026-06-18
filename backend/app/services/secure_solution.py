"""Secure Solution Report — per-finding, copy-paste fix instructions in Dutch.

A separate deliverable from the regular PDF: for every CRITICAL/HIGH/MEDIUM
finding the AI generates a plain-language explanation, exact Linux/Windows fix
commands, an effort estimate, a verification command and a residual-risk verdict.
Rendered to a reportlab PDF.
"""

import io
import json
import logging
import re

logger = logging.getLogger(__name__)

# Severities we generate fixes for (skip low/info — no actionable remediation).
_FIX_SEVERITIES = {"critical", "high", "medium"}
_MAX_FINDINGS = 20  # bound AI cost/time on huge scans (logged if truncated)

# Risk-score reduction estimate per fixed finding.
_RISK_REDUCTION = {"critical": 30, "high": 15, "medium": 5}

_SYSTEM_PROMPT = (
    "You are a security engineer helping a non-technical business owner fix a "
    "security vulnerability. Always answer in Dutch, simple language, no jargon. "
    "Return ONLY valid JSON (no markdown fences, no extra text)."
)


def _finding_field(f: dict, *keys: str, default: str = "") -> str:
    for k in keys:
        v = f.get(k)
        if v:
            return str(v)
    return default


# Markers that identify M14 Scan Comparator output / non-actionable history.
# The Secure Solution Report must only contain CURRENT active problems to fix.
_COMPARATOR_MARKERS = (
    "opgelost", "ongewijzigd", "nieuw", "vergelijking met scan van",
    "scan comparator", "m14",
)

_SEV_RANK = {"critical": 0, "high": 1, "medium": 2}


def _is_comparator_finding(f: dict) -> bool:
    blob = (
        _finding_field(f, "title", "titel") + " " + _finding_field(f, "description", "beschrijving")
    ).lower()
    return any(m in blob for m in _COMPARATOR_MARKERS)


def fixable_findings(report_data: dict) -> list:
    """Active findings that need fixing: severity critical/high/medium and NOT
    from the M14 comparator (resolved/unchanged/new history). Sorted most-severe
    first so the report reads in fix order."""
    findings = report_data.get("findings") or report_data.get("bevindingen") or []
    relevant = [
        f for f in findings
        if _finding_field(f, "severity", "ernst", default="info").lower() in _FIX_SEVERITIES
        and not _is_comparator_finding(f)
    ]
    relevant.sort(key=lambda f: _SEV_RANK.get(_finding_field(f, "severity", "ernst", default="medium").lower(), 9))
    return relevant


def _services_summary(tool_outputs: dict | None) -> str:
    """Short summary of services from the recon nmap output (for AI context)."""
    if not tool_outputs:
        return ""
    text = ""
    for phase, tools in (tool_outputs or {}).items():
        if not isinstance(tools, dict):
            continue
        for tname, out in tools.items():
            if "nmap" in str(tname).lower() and out:
                text += str(out) + "\n"
    lines = [ln.strip() for ln in text.splitlines() if "/tcp" in ln and "open" in ln]
    return "; ".join(lines[:15])


def _parse_json(raw: str) -> dict | None:
    cleaned = (raw or "").strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("\n")
        cleaned = "\n".join(parts[1:])
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3]
    # Best-effort: grab the outermost {...} if there is surrounding noise.
    m = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if m:
        cleaned = m.group(0)
    try:
        return json.loads(cleaned)
    except Exception:
        return None


def _fix_for_finding(provider, finding: dict, target: str, services: str) -> dict:
    title = _finding_field(finding, "title", "titel", "type", default="Bevinding")
    severity = _finding_field(finding, "severity", "ernst", default="medium").lower()
    description = _finding_field(finding, "description", "beschrijving", "detail")

    user_prompt = (
        f"Finding: {title}\n"
        f"Severity: {severity}\n"
        f"Description: {description}\n"
        f"System: {target}\n"
        f"Services found: {services or 'onbekend'}\n\n"
        "Genereer een Secure Solution in het Nederlands en geef het terug als JSON met exact deze sleutels:\n"
        "{\n"
        '  "uitleg": "uitleg in gewone taal, max 3 zinnen, geen jargon",\n'
        '  "fix_linux": "exacte bash-commandos voor Linux/Ubuntu, of null",\n'
        '  "fix_windows": "exacte PowerShell-commandos voor Windows Server, of null",\n'
        '  "tijdsduur": "geschatte tijd, bijv. 5 minuten",\n'
        '  "verificatie": "commando om te controleren of de fix werkt",\n'
        '  "risico_na_fix": "OPGELOST of VERMINDERD of HANDMATIGE ACTIE VEREIST",\n'
        '  "handmatige_actie": "uitleg als ontwikkelaarsactie nodig is, anders null"\n'
        "}\n"
        "Als de fix wijziging van applicatie-broncode vereist (SQL-injectie, XSS in code), "
        'zet dan risico_na_fix op "HANDMATIGE ACTIE VEREIST" en leg in handmatige_actie uit '
        "wat de ontwikkelaar moet doen."
    )
    try:
        raw = provider.analyze(_SYSTEM_PROMPT, user_prompt, max_tokens=900)
        data = _parse_json(raw) or {}
    except Exception as exc:
        logger.warning("Secure-solution AI failed for '%s': %s", title, exc)
        data = {}

    return {
        "titel": title,
        "ernst": severity,
        "uitleg": data.get("uitleg") or description or "Geen aanvullende uitleg beschikbaar.",
        "fix_linux": data.get("fix_linux") or None,
        "fix_windows": data.get("fix_windows") or None,
        "tijdsduur": data.get("tijdsduur") or "Onbekend",
        "verificatie": data.get("verificatie") or None,
        "risico_na_fix": (data.get("risico_na_fix") or "VERMINDERD").upper().strip(),
        "handmatige_actie": data.get("handmatige_actie") or None,
    }


def _minutes_from(text: str) -> int:
    """Rough minutes from strings like '5 minuten' / '1 uur' / '2 uren'."""
    if not text:
        return 0
    t = text.lower()
    nums = re.findall(r"\d+", t)
    n = int(nums[0]) if nums else 0
    if "uur" in t or "uren" in t or "hour" in t:
        return n * 60
    return n


def build_secure_solution(scan, target: str, report_data: dict, user) -> dict:
    """Run the AI per finding and return a structured report object (no PDF yet)."""
    from app.services.ai_provider import AIProvider

    relevant = fixable_findings(report_data)
    if len(relevant) > _MAX_FINDINGS:
        logger.info("Secure solution: capping %d findings to %d", len(relevant), _MAX_FINDINGS)
        relevant = relevant[:_MAX_FINDINGS]

    provider = AIProvider(user)
    services = _services_summary(getattr(scan, "tool_outputs", None))

    fixes = [_fix_for_finding(provider, f, target, services) for f in relevant]

    total_minutes = sum(_minutes_from(fx["tijdsduur"]) for fx in fixes)
    risk_before = int(report_data.get("risk_score", 0) or 0)
    reduction = sum(_RISK_REDUCTION.get(fx["ernst"], 0) for fx in fixes)
    risk_after = max(0, risk_before - reduction)

    return {
        "target": target,
        "fixes": fixes,
        "total_minutes": total_minutes,
        "risk_before": risk_before,
        "risk_after": risk_after,
    }


# ── PDF ───────────────────────────────────────────────────────────────────────

_SEV_HEX = {"critical": "#dc2626", "high": "#ea580c", "medium": "#ca8a04",
            "low": "#2563eb", "info": "#6b7280"}
_STATUS_HEX = {"OPGELOST": "#16a34a", "VERMINDERD": "#ea580c",
               "HANDMATIGE ACTIE VEREIST": "#dc2626"}


def _fmt_minutes(total: int) -> str:
    if total <= 0:
        return "onbekend"
    if total < 60:
        return f"{total} minuten"
    h, m = divmod(total, 60)
    return f"{h} uur" + (f" {m} min" if m else "")


def generate_secure_solution_pdf(report_obj: dict) -> bytes:
    from datetime import datetime, timezone
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak, Preformatted,
    )

    target = report_obj["target"]
    fixes = report_obj["fixes"]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title="Scanix Secure Solution Rapport", author="Scanix",
    )

    st = {
        "brand":  ParagraphStyle("brand", fontSize=26, leading=30, alignment=TA_CENTER, fontName="Helvetica-Bold", textColor=colors.HexColor("#0e2a3f")),
        "title":  ParagraphStyle("title", fontSize=20, leading=24, alignment=TA_CENTER, fontName="Helvetica-Bold", textColor=colors.HexColor("#00809e"), spaceBefore=6),
        "sub":    ParagraphStyle("sub", fontSize=13, leading=17, alignment=TA_CENTER, textColor=colors.HexColor("#6b7280"), spaceAfter=18),
        "h1":     ParagraphStyle("h1", fontSize=16, leading=20, fontName="Helvetica-Bold", textColor=colors.HexColor("#0e2a3f"), spaceBefore=14, spaceAfter=8),
        "fh":     ParagraphStyle("fh", fontSize=15, leading=19, fontName="Helvetica-Bold", spaceBefore=4, spaceAfter=4),
        "h2":     ParagraphStyle("h2", fontSize=11, leading=15, fontName="Helvetica-Bold", textColor=colors.HexColor("#0e6f8a"), spaceBefore=10, spaceAfter=4),
        "body":   ParagraphStyle("body", fontSize=9.5, leading=14, textColor=colors.HexColor("#1f2937"), spaceAfter=4),
        "small":  ParagraphStyle("small", fontSize=8, leading=11, textColor=colors.HexColor("#6b7280")),
        "code":   ParagraphStyle("code", fontSize=8.5, leading=12, fontName="Courier", textColor=colors.HexColor("#e5e7eb")),
        "warn":   ParagraphStyle("warn", fontSize=9.5, leading=14, textColor=colors.HexColor("#7f1d1d"), spaceAfter=2),
    }

    def code_block(text: str):
        tbl = Table([[Preformatted(text.strip(), st["code"])]], colWidths=[16.5 * cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0b1220")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#1f3550")),
        ]))
        return tbl

    def status_badge(status: str):
        hexc = _STATUS_HEX.get(status, "#6b7280")
        tbl = Table([[status]], colWidths=[8 * cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(hexc)),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return tbl

    story = []
    now = datetime.now(timezone.utc).strftime("%d-%m-%Y")

    # ── Page 1 — Cover ────────────────────────────────────────────────────────
    story.append(Spacer(1, 4 * cm))
    story.append(Paragraph("Scanix", st["brand"]))
    story.append(Paragraph("Secure Solution Rapport", st["title"]))
    story.append(Paragraph("Wat moet worden opgelost en hoe", st["sub"]))
    story.append(Paragraph(
        f"Actieve bevindingen die aandacht vereisen — {target}",
        ParagraphStyle("covsub", parent=st["sub"], fontSize=10,
                       textColor=colors.HexColor("#9ca3af"), spaceAfter=14),
    ))
    story.append(HRFlowable(width="70%", thickness=1, color=colors.HexColor("#00809e"), hAlign="CENTER"))
    story.append(Spacer(1, 1 * cm))
    cover = Table([
        ["Datum:", now],
        ["Aantal op te lossen bevindingen:", str(len(fixes))],
        ["Geschatte totale hersteltijd:", _fmt_minutes(report_obj["total_minutes"])],
    ], colWidths=[7 * cm, 9 * cm])
    cover.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#374151")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(cover)
    story.append(PageBreak())

    # ── Page 2 — Samenvatting ─────────────────────────────────────────────────
    story.append(Paragraph("Samenvatting", st["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0e2a3f")))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "Dit rapport bevat voor elke actieve bevinding exacte instructies om het "
        "probleem op te lossen. Voer de fixes uit in de aangegeven volgorde, begin "
        "met de meest ernstige bevindingen.",
        st["body"],
    ))
    story.append(Spacer(1, 0.4 * cm))

    rows = [["Bevinding", "Ernst", "Oplostijd", "Status"]]
    for fx in fixes:
        rows.append([
            fx["titel"][:60], fx["ernst"].upper(),
            fx["tijdsduur"], fx["risico_na_fix"],
        ])
    tbl = Table(rows, colWidths=[7.5 * cm, 2.2 * cm, 2.8 * cm, 4 * cm])
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0e2a3f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i, fx in enumerate(fixes, start=1):
        style.append(("TEXTCOLOR", (1, i), (1, i), colors.HexColor(_SEV_HEX.get(fx["ernst"], "#6b7280"))))
        style.append(("FONTNAME", (1, i), (1, i), "Helvetica-Bold"))
        style.append(("TEXTCOLOR", (3, i), (3, i), colors.HexColor(_STATUS_HEX.get(fx["risico_na_fix"], "#6b7280"))))
    tbl.setStyle(TableStyle(style))
    story.append(tbl)
    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(
        f"<b>Risicoverlaging:</b> na implementatie van alle fixes daalt uw risicoscore "
        f"van {report_obj['risk_before']} naar geschat {report_obj['risk_after']}.",
        st["body"],
    ))

    # ── Page 3+ — Per finding ─────────────────────────────────────────────────
    for fx in fixes:
        story.append(PageBreak())
        sev_hex = _SEV_HEX.get(fx["ernst"], "#6b7280")
        fh = ParagraphStyle("fhx", parent=st["fh"], textColor=colors.HexColor(sev_hex))
        story.append(Paragraph(fx["titel"], fh))
        badge = Table([[fx["ernst"].upper()]], colWidths=[3 * cm])
        badge.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(sev_hex)),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(badge)
        story.append(Spacer(1, 0.2 * cm))

        story.append(Paragraph("Wat is het probleem?", st["h2"]))
        story.append(Paragraph(fx["uitleg"], st["body"]))

        story.append(Paragraph("Hoe lost u dit op?", st["h2"]))
        if fx["fix_linux"]:
            story.append(Paragraph("Op Linux/Ubuntu:", st["body"]))
            story.append(code_block(fx["fix_linux"]))
            story.append(Spacer(1, 0.2 * cm))
        if fx["fix_windows"]:
            story.append(Paragraph("Op Windows Server:", st["body"]))
            story.append(code_block(fx["fix_windows"]))
            story.append(Spacer(1, 0.2 * cm))
        if fx["handmatige_actie"]:
            warn = Table([[Paragraph(
                "<b>Let op — dit vereist actie van uw ontwikkelaar:</b><br/>" + fx["handmatige_actie"],
                st["warn"])]], colWidths=[16.5 * cm])
            warn.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#fecaca")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(warn)
            story.append(Spacer(1, 0.2 * cm))
        if not fx["fix_linux"] and not fx["fix_windows"] and not fx["handmatige_actie"]:
            story.append(Paragraph("Zie de uitleg hierboven; specifieke commando's zijn niet van toepassing.", st["body"]))

        story.append(Paragraph("Hoe lang duurt het?", st["h2"]))
        story.append(Paragraph(fx["tijdsduur"], st["body"]))

        if fx["verificatie"]:
            story.append(Paragraph("Hoe weet u dat het werkt?", st["h2"]))
            story.append(code_block(fx["verificatie"]))
            story.append(Spacer(1, 0.2 * cm))

        story.append(Paragraph("Risico na implementatie", st["h2"]))
        story.append(status_badge(fx["risico_na_fix"]))
        story.append(Spacer(1, 0.3 * cm))
        story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#e5e7eb")))

    # ── Last page — Disclaimer ────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Disclaimer", st["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0e2a3f")))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "Dit rapport is automatisch gegenereerd door Scanix. De fix-instructies zijn "
        "algemeen van aard en gebaseerd op de gevonden configuratie. Test altijd eerst in "
        "een testomgeving. Scanix is niet aansprakelijk voor schade die ontstaat door het "
        "uitvoeren van de instructies. Voor complexe omgevingen adviseren wij ondersteuning "
        "van een gecertificeerde IT-professional.",
        st["body"],
    ))

    doc.build(story)
    return buf.getvalue()
