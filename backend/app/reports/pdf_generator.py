"""PDF report generation using WeasyPrint + Jinja2 templates."""

import io
import json
import logging
from datetime import datetime, timezone

from jinja2 import Environment, BaseLoader

try:
    from weasyprint import HTML as _HTML
except ImportError:
    _HTML = None  # type: ignore

logger = logging.getLogger(__name__)

REPORT_CSS = """
@page {
    size: A4;
    margin: 2cm;
    @top-center { content: "AutoPentest AI — Security Assessment Report"; font-size: 9px; color: #6b7280; }
    @bottom-center { content: "Page " counter(page) " of " counter(pages); font-size: 9px; color: #6b7280; }
    @bottom-right { content: "CONFIDENTIAL"; font-size: 9px; color: #ef4444; font-weight: bold; }
}

body {
    font-family: 'Helvetica Neue', Arial, sans-serif;
    color: #1f2937;
    line-height: 1.6;
    font-size: 11px;
}

.cover-page {
    text-align: center;
    padding-top: 200px;
    page-break-after: always;
}

.cover-page h1 {
    font-size: 36px;
    color: #1e3a5f;
    margin-bottom: 10px;
}

.cover-page .subtitle {
    font-size: 18px;
    color: #6b7280;
    margin-bottom: 40px;
}

.cover-page .meta {
    font-size: 14px;
    color: #374151;
}

h1 { font-size: 24px; color: #1e3a5f; border-bottom: 2px solid #1e3a5f; padding-bottom: 5px; margin-top: 30px; }
h2 { font-size: 18px; color: #2563eb; margin-top: 20px; }
h3 { font-size: 14px; color: #374151; margin-top: 15px; }

.score-box {
    display: inline-block;
    padding: 20px 40px;
    border-radius: 10px;
    text-align: center;
    margin: 20px 0;
}

.score-critical { background: #fef2f2; border: 2px solid #ef4444; }
.score-high { background: #fff7ed; border: 2px solid #f97316; }
.score-medium { background: #fffbeb; border: 2px solid #eab308; }
.score-good { background: #f0fdf4; border: 2px solid #22c55e; }

.score-number {
    font-size: 48px;
    font-weight: bold;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
    font-size: 10px;
}

th {
    background: #1e3a5f;
    color: white;
    padding: 8px 10px;
    text-align: left;
}

td {
    padding: 6px 10px;
    border-bottom: 1px solid #e5e7eb;
}

tr:nth-child(even) { background: #f9fafb; }

.severity-critical { color: #dc2626; font-weight: bold; }
.severity-high { color: #ea580c; font-weight: bold; }
.severity-medium { color: #ca8a04; font-weight: bold; }
.severity-low { color: #2563eb; }
.severity-info { color: #6b7280; }

.finding-box {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 15px;
    margin: 10px 0;
    page-break-inside: avoid;
}

.finding-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}

.remediation {
    background: #f0f9ff;
    border-left: 4px solid #2563eb;
    padding: 10px 15px;
    margin: 10px 0;
}

.section-break { page-break-before: always; }
"""

REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><style>{{ css }}</style></head>
<body>

<!-- Cover Page -->
<div class="cover-page">
    {% if white_label %}
    <h1>{{ company_name }}</h1>
    {% else %}
    <h1>AutoPentest AI</h1>
    {% endif %}
    <div class="subtitle">Security Assessment Report</div>
    <div class="meta">
        <p><strong>Target:</strong> {{ target }}</p>
        <p><strong>Scan Type:</strong> {{ scan_type | title }}</p>
        <p><strong>Date:</strong> {{ report_date }}</p>
        <p style="color: #ef4444; font-weight: bold; margin-top: 40px;">CONFIDENTIAL</p>
    </div>
</div>

<!-- Executive Summary -->
<h1>Executive Summary</h1>

<div class="score-box score-{{ score_class }}">
    <div class="score-number">{{ overall_score }}/100</div>
    <div>Overall Security Score</div>
</div>

<table>
<tr>
    <th>Severity</th><th>Count</th>
</tr>
<tr><td class="severity-critical">CRITICAL</td><td>{{ critical_count }}</td></tr>
<tr><td class="severity-high">HIGH</td><td>{{ high_count }}</td></tr>
<tr><td class="severity-medium">MEDIUM</td><td>{{ medium_count }}</td></tr>
<tr><td class="severity-low">LOW</td><td>{{ low_count }}</td></tr>
<tr><td class="severity-info">INFO</td><td>{{ info_count }}</td></tr>
</table>

<p>{{ executive_summary }}</p>

<!-- Technical Summary -->
<div class="section-break"></div>
<h1>Technical Summary</h1>
<p>{{ technical_summary }}</p>

<!-- Category Scores -->
<h2>Score Breakdown</h2>
<table>
<tr><th>Category</th><th>Score</th><th>Max</th><th>Findings</th></tr>
{% for cat in category_scores %}
<tr>
    <td>{{ cat.category }}</td>
    <td>{{ cat.score }}</td>
    <td>{{ cat.max_score }}</td>
    <td>{{ cat.findings_count }}</td>
</tr>
{% endfor %}
</table>

<!-- Detailed Findings -->
<div class="section-break"></div>
<h1>Detailed Findings</h1>

{% for finding in findings %}
<div class="finding-box">
    <div class="finding-header">
        <h3>{{ finding.id }}: {{ finding.title }}</h3>
        <span class="severity-{{ finding.risk_level | lower }}">{{ finding.risk_level }}
        {% if finding.cvss_score %} (CVSS {{ finding.cvss_score }}){% endif %}
        </span>
    </div>

    <p><strong>Affected Asset:</strong> {{ finding.affected_asset }}</p>
    <p><strong>Phase:</strong> {{ finding.phase }} | <strong>Tool:</strong> {{ finding.tool }}</p>
    {% if finding.cve_ids %}<p><strong>CVEs:</strong> {{ finding.cve_ids | join(', ') }}</p>{% endif %}
    {% if finding.owasp_category %}<p><strong>OWASP:</strong> {{ finding.owasp_category }}</p>{% endif %}

    <p><strong>Description:</strong> {{ finding.description }}</p>
    <p><strong>Evidence:</strong> {{ finding.evidence }}</p>
    <p><strong>Business Impact:</strong> {{ finding.business_impact }}</p>

    <div class="remediation">
        <strong>Remediation (Est. {{ finding.estimated_fix_time }}):</strong>
        <ul>
        {% for step in finding.remediation_steps %}
            <li>{{ step }}</li>
        {% endfor %}
        </ul>
    </div>
</div>
{% endfor %}

<!-- Remediation Roadmap -->
<div class="section-break"></div>
<h1>Remediation Roadmap</h1>

<h2>Quick Wins (< 1 day)</h2>
{% for item in remediation_quick_wins %}
<div class="remediation">
    <strong>{{ item.title }}</strong> — {{ item.estimated_effort }}
    <ul>{% for s in item.steps %}<li>{{ s }}</li>{% endfor %}</ul>
</div>
{% endfor %}

<h2>Short Term (< 1 week)</h2>
{% for item in remediation_short_term %}
<div class="remediation">
    <strong>{{ item.title }}</strong> — {{ item.estimated_effort }}
    <ul>{% for s in item.steps %}<li>{{ s }}</li>{% endfor %}</ul>
</div>
{% endfor %}

<h2>Long Term (< 1 month)</h2>
{% for item in remediation_long_term %}
<div class="remediation">
    <strong>{{ item.title }}</strong> — {{ item.estimated_effort }}
    <ul>{% for s in item.steps %}<li>{{ s }}</li>{% endfor %}</ul>
</div>
{% endfor %}

<!-- Compliance Mapping -->
{% if compliance %}
<div class="section-break"></div>
<h1>Compliance Mapping</h1>
{% for framework, controls in compliance.items() %}
<h2>{{ framework | upper }}</h2>
<ul>{% for c in controls %}<li>{{ c }}</li>{% endfor %}</ul>
{% endfor %}
{% endif %}

</body>
</html>
"""


def generate_pdf_report(
    report_data: dict,
    target: str,
    scan_type: str,
    white_label: bool = False,
    company_name: str = "",
) -> bytes:
    """Generate a PDF report from structured report data."""
    env = Environment(loader=BaseLoader())
    template = env.from_string(REPORT_TEMPLATE)

    score = report_data.get("overall_score", 0)
    if score >= 80:
        score_class = "good"
    elif score >= 60:
        score_class = "medium"
    elif score >= 40:
        score_class = "high"
    else:
        score_class = "critical"

    roadmap = report_data.get("remediation_roadmap", {})

    html_content = template.render(
        css=REPORT_CSS,
        target=target,
        scan_type=scan_type,
        report_date=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        white_label=white_label,
        company_name=company_name,
        overall_score=score,
        score_class=score_class,
        critical_count=report_data.get("critical_count", 0),
        high_count=report_data.get("high_count", 0),
        medium_count=report_data.get("medium_count", 0),
        low_count=report_data.get("low_count", 0),
        info_count=report_data.get("info_count", 0),
        executive_summary=report_data.get("executive_summary", ""),
        technical_summary=report_data.get("technical_summary", ""),
        category_scores=report_data.get("category_scores", []),
        findings=report_data.get("findings", []),
        remediation_quick_wins=roadmap.get("quick_wins", []),
        remediation_short_term=roadmap.get("short_term", []),
        remediation_long_term=roadmap.get("long_term", []),
        compliance=report_data.get("compliance", {}),
    )

    if _HTML is None:
        raise RuntimeError("weasyprint is not installed. PDF generation is unavailable in local dev mode.")
    pdf_bytes = _HTML(string=html_content).write_pdf()
    return pdf_bytes
