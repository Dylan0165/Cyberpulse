"""DeepSeek AI analysis pipeline — processes raw scan output into structured reports.

Replaces the previous Anthropic/Claude implementation.
Uses the OpenAI-compatible SDK pointed at DeepSeek's base URL.
"""

import json
import logging

from openai import OpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """You are a certified penetration tester (OSCP, CEH, CISSP).
Analyze the provided security scan output and produce a structured JSON report.

For EACH finding include:
- id: unique string
- title: short descriptive title
- severity: CRITICAL | HIGH | MEDIUM | LOW | INFO
- cvss: CVSS v3.1 score (0.0-10.0, calculate if not given)
- cve: CVE-ID if known, else null
- description: technical explanation
- impact: business impact in plain language
- recommendation: specific, actionable remediation steps
- owasp: OWASP Top 10 category if applicable
- phase: which scan phase found this
- tool: which tool found this

Top-level JSON structure:
{
  "risk_score": <0-100>,
  "risk_level": "CRITICAL|HIGH|MEDIUM|LOW",
  "management_summary": "<2-3 paragraph executive summary for non-technical audience>",
  "technical_summary": "<technical summary for IT team>",
  "findings": [ <finding objects> ],
  "finding_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
  "remediation_roadmap": {
    "quick_wins": [ {"title":"...", "effort":"<1 day", "steps":["..."]} ],
    "short_term": [ {"title":"...", "effort":"<1 week", "steps":["..."]} ],
    "long_term":  [ {"title":"...", "effort":"<1 month", "steps":["..."]} ]
  },
  "compliance_mapping": {
    "owasp_top10": ["A01:2021 - ..."],
    "iso27001": ["A.12.6.1 - ..."],
    "nis2": ["Article 21 - ..."]
  },
  "scan_id": "<scan_id>",
  "target": "<target>",
  "scan_type": "<scan_type>"
}

RULES:
- Return ONLY valid JSON, no markdown fences, no extra text.
- Never include working exploit code.
- If a phase produced no output or only errors, note it as INFO finding.
- Be precise with CVSS scores.
"""


def _get_client() -> OpenAI:
    return OpenAI(
        api_key=settings.deepseek_api_key or "no-key",
        base_url=settings.deepseek_base_url,
    )


def analyze_scan_sync(
    scan_id: str,
    target: str,
    scan_type: str,
    phases_completed: list[str],
    all_outputs: dict[str, dict[str, str]],
) -> dict:
    """
    Synchronous DeepSeek analysis — used by Celery workers.

    Args:
        scan_id:          UUID string of the scan
        target:           target value (IP or hostname)
        scan_type:        "quick" | "full" | …
        phases_completed: list of phase names that ran
        all_outputs:      {phase_name: {tool_name: stdout_string}}

    Returns:
        Parsed JSON dict from DeepSeek (or an error dict on failure).
    """
    client = _get_client()

    sections = []
    for phase, tools in all_outputs.items():
        sections.append(f"\n{'='*60}\nPHASE: {phase.upper()}\n{'='*60}")
        for tool_name, output in tools.items():
            truncated = output[:25000] if len(output) > 25000 else output
            sections.append(f"\n--- {tool_name} ---\n{truncated}")

    user_message = (
        f"Analyze the following penetration test results.\n\n"
        f"Target: {target}\n"
        f"Scan Type: {scan_type}\n"
        f"Scan ID: {scan_id}\n"
        f"Phases completed: {json.dumps(phases_completed)}\n\n"
        f"--- FULL SCAN OUTPUT ---\n"
        f"{''.join(sections)}\n"
        f"--- END SCAN OUTPUT ---\n\n"
        f"Produce the comprehensive structured JSON security report."
    )

    try:
        response = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            max_tokens=16000,
            temperature=0.1,
        )
        raw = response.choices[0].message.content or ""
        return _parse_json(raw, scan_id, target, scan_type)
    except Exception as exc:
        logger.error("DeepSeek analysis failed for scan %s: %s", scan_id, exc)
        return _error_report(scan_id, target, scan_type, str(exc))


def analyze_scan_sync_streaming(
    scan_id: str,
    target: str,
    scan_type: str,
    phases_completed: list[str],
    all_outputs: dict[str, dict[str, str]],
    redis_client=None,
) -> dict:
    """
    Like analyze_scan_sync but streams tokens to Redis channel
    `scan:{scan_id}:analysis` for live WebSocket updates.
    """
    client = _get_client()

    sections = []
    for phase, tools in all_outputs.items():
        sections.append(f"\n{'='*60}\nPHASE: {phase.upper()}\n{'='*60}")
        for tool_name, output in tools.items():
            truncated = output[:25000] if len(output) > 25000 else output
            sections.append(f"\n--- {tool_name} ---\n{truncated}")

    user_message = (
        f"Target: {target}\nScan Type: {scan_type}\nScan ID: {scan_id}\n"
        f"Phases: {json.dumps(phases_completed)}\n\n"
        f"--- SCAN OUTPUT ---\n{''.join(sections)}\n--- END ---\n\n"
        f"Produce the structured JSON security report."
    )

    accumulated = ""
    try:
        stream = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            max_tokens=16000,
            temperature=0.1,
            stream=True,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content or ""
            accumulated += delta
            if redis_client and delta:
                try:
                    redis_client.publish(
                        f"scan:{scan_id}:analysis",
                        json.dumps({"type": "token", "token": delta}),
                    )
                except Exception:
                    pass

        result = _parse_json(accumulated, scan_id, target, scan_type)
        if redis_client:
            try:
                redis_client.publish(
                    f"scan:{scan_id}:analysis",
                    json.dumps({"type": "analysis_complete", "risk_score": result.get("risk_score", 0)}),
                )
            except Exception:
                pass
        return result

    except Exception as exc:
        logger.error("DeepSeek streaming failed for scan %s: %s", scan_id, exc)
        # Fall back to non-streaming on error
        logger.info("Falling back to non-streaming DeepSeek call for scan %s", scan_id)
        return analyze_scan_sync(scan_id, target, scan_type, phases_completed, all_outputs)


def _parse_json(raw: str, scan_id: str, target: str, scan_type: str) -> dict:
    cleaned = raw.strip()
    # Strip markdown code fences if present
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:])
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3]
    try:
        data = json.loads(cleaned)
        # Ensure required top-level keys are present
        data.setdefault("scan_id",   scan_id)
        data.setdefault("target",    target)
        data.setdefault("scan_type", scan_type)
        data.setdefault("risk_score", 0)
        data.setdefault("risk_level", "LOW")
        data.setdefault("findings", [])
        return data
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse DeepSeek JSON: %s | raw=%s", exc, cleaned[:200])
        return _error_report(scan_id, target, scan_type, f"JSON parse error: {exc}")


def _error_report(scan_id: str, target: str, scan_type: str, error: str) -> dict:
    return {
        "scan_id":            scan_id,
        "target":             target,
        "scan_type":          scan_type,
        "risk_score":         0,
        "risk_level":         "INFO",
        "management_summary": f"AI analysis could not complete: {error}",
        "technical_summary":  f"DeepSeek API error: {error}",
        "findings":           [],
        "finding_counts":     {"critical":0,"high":0,"medium":0,"low":0,"info":0},
        "remediation_roadmap": {"quick_wins":[],"short_term":[],"long_term":[]},
        "compliance_mapping":  {"owasp_top10":[],"iso27001":[],"nis2":[]},
    }
