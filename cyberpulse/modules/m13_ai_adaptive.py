"""Module 13-AI — AI Adaptive Scanner.

After all standard phases complete, DeepSeek analyses the accumulated findings
and suggests targeted follow-up scans. Those scans are then executed via subprocess.
"""

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger("cyberpulse.modules.m13_ai_adaptive")

_ALLOWED_TOOLS = {"nmap", "nuclei", "nikto", "gobuster", "feroxbuster", "sqlmap", "curl"}
_TOOL_TIMEOUT = 180  # seconds per follow-up scan


class Scanner:
    name = "AI Adaptive Scanner"
    phase = "custom"
    description = "DeepSeek analyses findings and directs targeted follow-up scans"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config or {}

    # ── data loading ──────────────────────────────────────────────────────────

    def _load_findings(self) -> list[dict]:
        """Return all findings from scan_data.json or individual module files."""
        findings: list[dict] = []
        scan_data_file = self.output_dir / "scan_data.json"
        if scan_data_file.exists():
            try:
                with open(scan_data_file, encoding="utf-8") as f:
                    data = json.load(f)
                for result in data.get("results", []):
                    findings.extend(result.get("findings", []))
                return findings
            except Exception:
                pass
        # Fallback: scan individual module JSON files
        for jf in sorted(self.output_dir.glob("*.json")):
            if jf.name in ("scan_data.json", "analysis.json"):
                continue
            try:
                with open(jf, encoding="utf-8") as f:
                    data = json.load(f)
                findings.extend(data.get("findings", []))
            except Exception:
                pass
        return findings

    # ── DeepSeek prompt ───────────────────────────────────────────────────────

    def _ask_deepseek(self, findings: list[dict]) -> list[dict]:
        """Ask DeepSeek for up to 5 follow-up scan commands. Returns list of {tool, args, reason}."""
        try:
            from openai import OpenAI  # type: ignore
        except ImportError:
            logger.warning("openai SDK not available — skipping AI adaptive scan")
            return []

        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

        if not api_key:
            logger.warning("DEEPSEEK_API_KEY not set — skipping AI adaptive scan")
            return []

        # Summarise findings to stay within token limit
        summary = []
        for f in findings[:50]:
            summary.append({
                "type": f.get("type", ""),
                "severity": f.get("severity", ""),
                "title": f.get("title", f.get("type", "")),
                "service": f.get("service", ""),
                "version": f.get("version", ""),
                "port": f.get("port", ""),
            })

        prompt = f"""You are a professional penetration tester.
Based on the scan findings below, suggest up to 5 targeted follow-up scans.

Target: {self.target}

Findings summary:
{json.dumps(summary, indent=2)[:3000]}

Respond ONLY with a valid JSON array. Each item must have exactly these keys:
  "tool": one of {sorted(_ALLOWED_TOOLS)},
  "args": command-line arguments string (no sudo, no pipes, no semicolons),
  "reason": one sentence explaining why this scan is relevant.

Example:
[
  {{"tool": "nmap", "args": "--script smb-vuln-ms17-010 -p 445 192.168.1.1", "reason": "SMB on port 445 detected — check for EternalBlue."}},
  {{"tool": "nuclei", "args": "-u http://example.com -t cves/2021/CVE-2021-41773.yaml", "reason": "Apache 2.4.49 version detected."}}
]

Output ONLY the JSON array, no prose."""

        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=800,
            )
            raw = response.choices[0].message.content.strip()
            # Extract JSON array from response
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start == -1 or end == 0:
                return []
            return json.loads(raw[start:end])
        except Exception as e:
            logger.warning("DeepSeek adaptive query failed: %s", e)
            return []

    # ── tool execution ────────────────────────────────────────────────────────

    def _run_tool(self, tool: str, args: str) -> str:
        """Execute a scan tool via subprocess with safety checks."""
        # Safety: only allow tools from the allowlist
        if tool not in _ALLOWED_TOOLS:
            return f"Tool '{tool}' not in allowlist"
        if not shutil.which(tool):
            return f"Tool '{tool}' not installed"
        # Safety: block shell metacharacters
        for bad in ("|", ";", "&", "`", "$(", ">", "<", "\n"):
            if bad in args:
                return f"Rejected: args contain disallowed character '{bad}'"

        cmd = [tool] + args.split()
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=_TOOL_TIMEOUT
            )
            return (result.stdout + result.stderr)[:1000]
        except subprocess.TimeoutExpired:
            return f"{tool} timed out after {_TOOL_TIMEOUT}s"
        except Exception as e:
            return f"Error running {tool}: {e}"

    # ── main ──────────────────────────────────────────────────────────────────

    def run(self) -> dict:
        findings: list[dict] = []
        raw_lines: list[str] = []

        raw_lines.append(f"[+] AI Adaptive Scanner — target: {self.target}")

        all_findings = self._load_findings()
        raw_lines.append(f"[*] Loaded {len(all_findings)} findings from previous modules")

        if not all_findings:
            raw_lines.append("[!] No previous findings available — skipping adaptive scan")
            return {"findings": [], "raw_output": "\n".join(raw_lines), "follow_up_scans": 0}

        raw_lines.append("[*] Querying DeepSeek for follow-up scan recommendations...")
        follow_ups = self._ask_deepseek(all_findings)
        raw_lines.append(f"[*] DeepSeek suggested {len(follow_ups)} follow-up scans")

        for scan in follow_ups[:5]:
            tool = scan.get("tool", "")
            args = scan.get("args", "")
            reason = scan.get("reason", "")

            if not tool or not args:
                continue

            raw_lines.append(f"[*] Executing: {tool} {args}")
            raw_lines.append(f"    Reason: {reason}")
            output = self._run_tool(tool, args)
            raw_lines.append(f"    Output ({len(output)} chars):\n{output[:300]}")

            if output and len(output) > 20:
                findings.append({
                    "type": "ai_directed_finding",
                    "severity": "HIGH",
                    "title": f"AI-directed scan: {tool} ({reason[:60]})",
                    "description": reason,
                    "impact": "Additional attack surface or vulnerability identified by AI-directed analysis.",
                    "recommendation": "Review output manually and investigate further.",
                    "evidence": f"Command: {tool} {args}\n\nOutput:\n{output[:500]}",
                    "tool": tool,
                    "command": f"{tool} {args}",
                })

        raw_lines.append(f"[+] Done — {len(findings)} AI-directed findings")
        return {
            "findings": findings,
            "raw_output": "\n".join(raw_lines),
            "follow_up_scans": len(follow_ups),
        }
