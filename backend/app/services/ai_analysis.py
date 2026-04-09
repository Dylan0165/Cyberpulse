"""Claude AI analysis pipeline — processes raw scan output into structured reports."""

import json
import logging
from typing import AsyncIterator

import anthropic

from app.core.config import get_settings
from app.schemas.report import ReportSchema

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """You are an expert penetration tester with OSCP, CISSP, and CEH certifications.
Analyze the provided scan output and produce a structured security report.

For each finding, provide:
- CVE IDs where applicable
- CVSS v3.1 score (calculate if not present)
- Risk level: CRITICAL / HIGH / MEDIUM / LOW / INFO
- Business impact (plain English, no jargon)
- Proof of concept description (no actual exploit code)
- Remediation steps (specific, actionable, with code examples where helpful)
- OWASP category if applicable
- Estimated fix time

At the end, provide:
- Executive summary (for non-technical CEO/CFO audience, max 3 paragraphs)
- Technical summary (for IT team)
- Prioritized remediation roadmap:
  - Quick wins (< 1 day)
  - Short term (< 1 week)
  - Long term (< 1 month)
- Overall security score 0-100 with breakdown per category

Format output as structured JSON matching this schema:
{
  "executive_summary": "string",
  "technical_summary": "string",
  "findings": [
    {
      "id": "string",
      "title": "string",
      "description": "string",
      "cve_ids": ["string"],
      "cvss_score": number_or_null,
      "risk_level": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
      "owasp_category": "string_or_null",
      "affected_asset": "string",
      "evidence": "string",
      "business_impact": "string",
      "poc_description": "string",
      "remediation_steps": ["string"],
      "estimated_fix_time": "string",
      "phase": "string",
      "tool": "string"
    }
  ],
  "overall_score": number,
  "category_scores": [
    {"category": "string", "score": number, "max_score": number, "findings_count": number}
  ],
  "remediation_roadmap": {
    "quick_wins": [{"finding_id": "string", "title": "string", "priority": "quick_win", "estimated_effort": "string", "steps": ["string"]}],
    "short_term": [...],
    "long_term": [...]
  },
  "scan_id": "string",
  "target": "string",
  "scan_type": "string",
  "phases_completed": ["string"],
  "total_findings": number,
  "critical_count": number,
  "high_count": number,
  "medium_count": number,
  "low_count": number,
  "info_count": number,
  "compliance": {
    "iso27001": ["string"],
    "nis2": ["string"],
    "soc2": ["string"],
    "gdpr": ["string"]
  }
}

IMPORTANT RULES:
- Never include actual working exploit code. Focus on education and remediation.
- Be precise with CVSS scores — calculate them properly using CVSS v3.1 vectors.
- Provide actionable remediation with specific configuration changes or code snippets.
- Map findings to compliance frameworks where applicable.
- If scan output shows no vulnerabilities for a tool, note it under INFO findings.
- Return ONLY valid JSON, no markdown code fences or extra text."""


async def analyze_phase_output(
    scan_id: str,
    target: str,
    scan_type: str,
    phase: str,
    tool_outputs: dict[str, str],
) -> AsyncIterator[str]:
    """Stream Claude's analysis of scan phase output."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Build the user message with all tool outputs for this phase
    tool_sections = []
    for tool_name, output in tool_outputs.items():
        # Truncate very large outputs to stay within context limits
        truncated = output[:50000] if len(output) > 50000 else output
        tool_sections.append(f"=== {tool_name} ===\n{truncated}")

    user_message = f"""Analyze the following penetration test results.

Target: {target}
Scan Type: {scan_type}
Phase: {phase}
Scan ID: {scan_id}
Phases completed: ["{phase}"]

--- SCAN OUTPUT ---
{"\\n\\n".join(tool_sections)}
--- END SCAN OUTPUT ---

Produce the structured JSON security report."""

    async with client.messages.stream(
        model=settings.claude_model,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def analyze_full_scan(
    scan_id: str,
    target: str,
    scan_type: str,
    phases_completed: list[str],
    all_outputs: dict[str, dict[str, str]],
) -> AsyncIterator[str]:
    """Stream Claude's analysis of a complete multi-phase scan."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Build comprehensive output
    sections = []
    for phase, tools in all_outputs.items():
        sections.append(f"\n{'='*60}\nPHASE: {phase.upper()}\n{'='*60}")
        for tool_name, output in tools.items():
            truncated = output[:30000] if len(output) > 30000 else output
            sections.append(f"\n--- {tool_name} ---\n{truncated}")

    user_message = f"""Analyze the following complete penetration test results.

Target: {target}
Scan Type: {scan_type}
Scan ID: {scan_id}
Phases completed: {json.dumps(phases_completed)}

--- FULL SCAN OUTPUT ---
{"\\n".join(sections)}
--- END SCAN OUTPUT ---

Produce the comprehensive structured JSON security report covering all phases."""

    async with client.messages.stream(
        model=settings.claude_model,
        max_tokens=32000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        async for text in stream.text_stream:
            yield text


def parse_report_json(raw_json: str) -> ReportSchema | None:
    """Parse Claude's JSON output into our report schema."""
    try:
        # Strip markdown code fences if present
        cleaned = raw_json.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:])
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
        data = json.loads(cleaned)
        return ReportSchema(**data)
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Failed to parse report JSON: {e}")
        return None
