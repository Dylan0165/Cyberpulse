"""Tool-specific AI analyser — builds DeepSeek prompts per tool type.

Each tool gets contextual prompts so DeepSeek understands exactly what
the output means and how to assess findings.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from config import Config
from tools.base import ToolCategory, ToolFinding, ToolResult

logger = logging.getLogger("cyberpulse.tools.ai_analyser")


# ── Tool-Specific Prompt Guidelines ───────────────────────────────

TOOL_PROMPTS: dict[str, str] = {
    "john": (
        "Dit is output van John the Ripper, een password cracking tool. "
        "Beoordeel de sterkte van gekraakte wachtwoorden op basis van NIST 800-63B richtlijnen. "
        "Geef password policy aanbevelingen. Classificeer: eenvoudige wachtwoorden als high, "
        "default credentials als critical."
    ),
    "hashcat": (
        "Dit is output van Hashcat (GPU/CPU password cracker). "
        "Beoordeel de sterkte van gekraakte wachtwoorden. Geef password policy aanbevelingen. "
        "Let op hash types en crack tijden — sneller gekraakt = zwakker wachtwoord."
    ),
    "hydra": (
        "Dit is output van Hydra, een brute-force login tool. "
        "Succesvolle logins zijn altijd critical of high. Let op default credentials. "
        "Geef aanbevelingen voor account lockout, MFA, en sterke wachtwoorden."
    ),
    "sqlmap": (
        "Dit is output van SQLmap, een SQL injection tool. "
        "Analyseer welk type injectie gevonden is (error-based, blind, time-based, UNION). "
        "Schat data exfiltratie risico in. SQL injection is altijd minimaal high, "
        "bij database access critical."
    ),
    "nikto": (
        "Dit is output van Nikto, een web vulnerability scanner. "
        "Filter false positives — veel Nikto findings zijn informatief. "
        "Prioritiseer op basis van CVSS. Outdated servers en bekende CVEs zijn high/critical."
    ),
    "wpscan": (
        "Dit is output van WPScan, een WordPress security scanner. "
        "Beoordeel plugin/theme kwetsbaarheden, outdated WordPress versies, "
        "en onveilige configuraties. Bekende CVEs zijn high/critical."
    ),
    "nuclei": (
        "Dit is output van Nuclei, een template-based vulnerability scanner. "
        "Nuclei findings bevatten al severity levels — valideer deze en voeg context toe. "
        "Geef concrete mitigatiestappen per finding."
    ),
    "gobuster": (
        "Dit is output van Gobuster, een directory/file brute-force tool. "
        "Beoordeel gevonden paden op risico: admin panels, backup bestanden, "
        "configuratiebestanden, API endpoints. Prioritiseer op gevoeligheid."
    ),
    "masscan": (
        "Dit is output van Masscan, een snelle port scanner. "
        "Beoordeel open poorten op risico. Onverwachte open poorten zijn medium, "
        "bekende kwetsbare services (SMB, RDP, telnet) zijn high."
    ),
    "theharvester": (
        "Dit is output van theHarvester, een OSINT tool voor email/subdomain discovery. "
        "Beoordeel het aanvalsoppervlak. Veel blootgestelde emails verhogen phishing risico. "
        "Subdomains met gevoelige namen (admin, staging) zijn medium/high."
    ),
    "amass": (
        "Dit is output van Amass, een subdomain enumeration tool. "
        "Beoordeel de scope van het aanvalsoppervlak. Veel subdomains verhogen de kans "
        "op kwetsbaarheden. Let op wildcard DNS en verouderde subdomains."
    ),
    "tshark": (
        "Dit is output van TShark (Wireshark CLI), een packet capture tool. "
        "Analyseer netwerk verkeer op onversleutelde protocols, credential leaks, "
        "suspicious DNS queries, en ongebruikelijke verbindingen."
    ),
    "searchsploit": (
        "Dit is output van SearchSploit (ExploitDB lookup). "
        "Match gevonden exploits met gedetecteerde services en versies. "
        "Exploits met publieke PoC code zijn critical als de service bereikbaar is."
    ),
    "responder": (
        "Dit is output van Responder, een LLMNR/NBT-NS/mDNS poisoner. "
        "Gecapturde hashes zijn high — beoordeel NTLM relay risico. "
        "Aanbevelingen: disable LLMNR, NBT-NS, WPAD in het netwerk."
    ),
    "crackmapexec": (
        "Dit is output van CrackMapExec, een post-exploitation tool voor Windows/AD. "
        "Succesvolle authenticaties zijn critical. Beoordeel laterale beweging risico."
    ),
    "dnsrecon": (
        "Dit is output van DNSrecon, een DNS reconnaissance tool. "
        "Beoordeel zone transfers (critical als succesvol), DNS records op misconfigs, "
        "en subdomain discovery resultaten."
    ),
    "xsstrike": (
        "Dit is output van XSStrike, een XSS detection tool. "
        "Bevestigde XSS kwetsbaarheden zijn high. Reflected XSS is high, "
        "stored XSS is critical. Beoordeel de context van de injection."
    ),
    "commix": (
        "Dit is output van Commix, een command injection tool. "
        "Bevestigde command injection is altijd critical — het geeft shell access. "
        "Beoordeel het type (classic, eval-based, time-based)."
    ),
    "volatility3": (
        "Dit is output van Volatility 3, een memory forensics tool. "
        "Analyseer verdachte processen, vergelijk met bekende malware indicators. "
        "Hidden processes en code injection zijn critical."
    ),
    "aircrack": (
        "Dit is output van Aircrack-ng, een wireless security tool. "
        "Beoordeel WPA2 handshake kwaliteit. Zwakke WiFi wachtwoorden zijn high. "
        "Adviseer over enterprise WiFi beveiliging (WPA2-Enterprise, 802.1X)."
    ),
    "hashid": (
        "Dit is output van Hashid, een hash identification tool. "
        "Identificeer de hash types en beoordeel de sterkte van het hash algoritme. "
        "MD5/SHA1 = weak (medium), bcrypt/argon2 = sterk (info)."
    ),
    "lynis": (
        "Dit is output van Lynis, een Linux system audit tool. "
        "Beoordeel hardening score en individuele checks. "
        "Kritieke findings zijn misconfiguraties die direct exploitbaar zijn."
    ),
    "trivy": (
        "Dit is output van Trivy, een container vulnerability scanner. "
        "Beoordeel CVEs per severity. Focus op fixable vulnerabilities."
    ),
    "impacket": (
        "Dit is output van Impacket, een Python library voor AD/SMB/Kerberos attacks. "
        "Succesvolle credential dumps zijn critical. Kerberoasting en AS-REP roasting "
        "resultaten beoordelen op basis van hash crack-baarheid."
    ),
}

# Default prompt for tools without specific guidance
DEFAULT_TOOL_PROMPT = (
    "Analyseer de output van deze security tool. "
    "Beoordeel elke finding op ernst (critical/high/medium/low/info). "
    "Geef concrete aanbevelingen voor mitigatie."
)


# ── AI Analyser ────────────────────────────────────────────────────

TOOL_ANALYSIS_SYSTEM_PROMPT = """Je bent CyberPulse AI, een expert cybersecurity-analist.
Je analyseert de output van individuele security tools en geeft een gestructureerde beoordeling in het Nederlands.

Voor elke tool finding, produceer een JSON object met:
{
    "findings": [
        {
            "severity": "critical|high|medium|low|info",
            "title": "max 80 chars — korte beschrijving",
            "description": "Technische uitleg in het Nederlands",
            "impact": "Wat kan een aanvaller hiermee doen",
            "recommendation": "Concrete mitigatiestap",
            "cve": "CVE nummer of leeg",
            "confidence": "high|medium|low",
            "false_positive_risk": "high|medium|low"
        }
    ],
    "samenvatting": "Korte samenvatting van alle tool findings"
}

Regels:
- Gebruik ALLEEN Nederlands
- Wees specifiek en concreet
- Filter false positives waar mogelijk
- Verwijs naar CVE-nummers en standaarden waar relevant
- Geef maximaal 20 findings (de belangrijkste)
"""


def build_tool_prompt(tool_result: ToolResult, target: str,
                      scan_context: dict | None = None) -> list[dict]:
    """Build a DeepSeek prompt for analysing a specific tool's output."""
    tool_name = tool_result.tool_name
    tool_guidance = TOOL_PROMPTS.get(tool_name, DEFAULT_TOOL_PROMPT)

    # Build context section
    context_lines = [
        f"Tool: {tool_result.display_name} ({tool_name})",
        f"Categorie: {tool_result.category.value if isinstance(tool_result.category, ToolCategory) else tool_result.category}",
        f"Target: {target}",
        f"Aantal ruwe findings: {len(tool_result.findings)}",
        "",
        f"=== TOOL-SPECIFIEKE RICHTLIJN ===",
        tool_guidance,
        "",
    ]

    # Add scan context if available
    if scan_context:
        context_lines.append("=== SCAN CONTEXT ===")
        if scan_context.get("open_ports"):
            context_lines.append(f"Open poorten: {scan_context['open_ports']}")
        if scan_context.get("services"):
            context_lines.append(f"Gedetecteerde services: {scan_context['services']}")
        if scan_context.get("os_info"):
            context_lines.append(f"OS informatie: {scan_context['os_info']}")
        context_lines.append("")

    # Add findings
    context_lines.append("=== TOOL FINDINGS ===")
    for finding in tool_result.findings[:20]:
        f_dict = finding.to_dict() if hasattr(finding, "to_dict") else finding
        context_lines.append(json.dumps(f_dict, ensure_ascii=False, indent=2))
        context_lines.append("")

    # Add raw output (truncated)
    if tool_result.raw_output:
        context_lines.append("=== RAW OUTPUT (truncated) ===")
        context_lines.append(tool_result.raw_output[:2000])
        context_lines.append("")

    context_lines.append("Geef nu je analyse in het gevraagde JSON-formaat.")

    return [
        {"role": "system", "content": TOOL_ANALYSIS_SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(context_lines)},
    ]


def analyse_tool_result(tool_result: ToolResult, target: str,
                        scan_context: dict | None = None) -> dict:
    """Send tool result to DeepSeek for AI analysis.

    Returns parsed JSON with enriched findings, or the original findings
    if AI is unavailable.
    """
    if not Config.DEEPSEEK_API_KEY:
        logger.info("DeepSeek niet beschikbaar — tool findings zonder AI analyse")
        return {
            "findings": [f.to_dict() for f in tool_result.findings],
            "samenvatting": f"{tool_result.display_name}: {len(tool_result.findings)} findings (zonder AI analyse)",
        }

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=Config.DEEPSEEK_API_KEY,
            base_url=Config.DEEPSEEK_BASE_URL,
        )

        messages = build_tool_prompt(tool_result, target, scan_context)

        response = client.chat.completions.create(
            model=Config.DEEPSEEK_MODEL,
            messages=messages,
            temperature=Config.DEEPSEEK_TEMPERATURE,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        return json.loads(content)

    except Exception as e:
        logger.error("AI analyse voor %s mislukt: %s", tool_result.tool_name, e)
        return {
            "findings": [f.to_dict() for f in tool_result.findings],
            "samenvatting": f"AI analyse mislukt: {e}",
            "error": str(e),
        }
