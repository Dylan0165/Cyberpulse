"""Backend API endpoints for Kali tool management.

Proxies tool info from the CyberPulse scanner to the SaaS frontend.
"""

import shutil
from fastapi import APIRouter

router = APIRouter(prefix="/tools", tags=["tools"])

# Category → tool list (mirrors what's in cyberpulse/tools)
_ALL_TOOLS = {
    "password": [
        {"name": "john", "display_name": "John the Ripper"},
        {"name": "hashcat", "display_name": "Hashcat"},
        {"name": "hydra", "display_name": "Hydra"},
        {"name": "crackmapexec", "display_name": "CrackMapExec"},
        {"name": "medusa", "display_name": "Medusa"},
        {"name": "fcrackzip", "display_name": "Fcrackzip"},
        {"name": "ophcrack", "display_name": "Ophcrack"},
        {"name": "pdfcrack", "display_name": "PDFCrack"},
    ],
    "network_scanning": [
        {"name": "masscan", "display_name": "Masscan"},
        {"name": "zmap", "display_name": "ZMap"},
        {"name": "netdiscover", "display_name": "Netdiscover"},
        {"name": "arpscan", "display_name": "ARP-scan"},
        {"name": "hping3", "display_name": "Hping3"},
        {"name": "unicornscan", "display_name": "Unicornscan"},
    ],
    "web": [
        {"name": "sqlmap", "display_name": "SQLmap"},
        {"name": "nikto", "display_name": "Nikto"},
        {"name": "wpscan", "display_name": "WPScan"},
        {"name": "gobuster", "display_name": "Gobuster"},
        {"name": "nuclei", "display_name": "Nuclei"},
        {"name": "wfuzz", "display_name": "Wfuzz"},
        {"name": "xsstrike", "display_name": "XSStrike"},
        {"name": "commix", "display_name": "Commix"},
        {"name": "arjun", "display_name": "Arjun"},
        {"name": "skipfish", "display_name": "Skipfish"},
    ],
    "wireless": [
        {"name": "aireplay-ng", "display_name": "Aireplay-ng"},
        {"name": "reaver", "display_name": "Reaver"},
        {"name": "wash", "display_name": "Wash"},
        {"name": "kismet", "display_name": "Kismet"},
    ],
    "sniffing": [
        {"name": "tshark", "display_name": "Tshark"},
        {"name": "tcpdump", "display_name": "Tcpdump"},
        {"name": "bettercap", "display_name": "Bettercap"},
        {"name": "responder", "display_name": "Responder"},
        {"name": "arpspoof", "display_name": "Arpspoof"},
        {"name": "ettercap", "display_name": "Ettercap"},
        {"name": "macchanger", "display_name": "Macchanger"},
    ],
    "osint": [
        {"name": "theharvester", "display_name": "theHarvester"},
        {"name": "amass", "display_name": "Amass"},
        {"name": "dnsrecon", "display_name": "DNSrecon"},
        {"name": "fierce", "display_name": "Fierce"},
        {"name": "spiderfoot", "display_name": "SpiderFoot"},
        {"name": "shodan", "display_name": "Shodan"},
        {"name": "recon-ng", "display_name": "Recon-ng"},
        {"name": "maltego", "display_name": "Maltego"},
    ],
    "exploitation": [
        {"name": "searchsploit", "display_name": "SearchSploit"},
        {"name": "impacket", "display_name": "Impacket"},
        {"name": "evil-winrm", "display_name": "Evil-WinRM"},
        {"name": "certipy", "display_name": "Certipy"},
    ],
    "post_exploit": [
        {"name": "bloodhound-reader", "display_name": "BloodHound Reader"},
        {"name": "linpeas-parser", "display_name": "LinPEAS Parser"},
        {"name": "mimikatz", "display_name": "Mimikatz"},
        {"name": "winpeas-parser", "display_name": "WinPEAS Parser"},
    ],
    "forensics": [
        {"name": "volatility3", "display_name": "Volatility 3"},
        {"name": "binwalk", "display_name": "Binwalk"},
        {"name": "exiftool", "display_name": "ExifTool"},
        {"name": "strings", "display_name": "Strings"},
        {"name": "foremost", "display_name": "Foremost"},
        {"name": "steghide", "display_name": "Steghide"},
    ],
    "reversing": [
        {"name": "radare2", "display_name": "Radare2"},
        {"name": "objdump", "display_name": "Objdump"},
        {"name": "strace", "display_name": "Strace"},
        {"name": "ghidra", "display_name": "Ghidra"},
        {"name": "pwntools", "display_name": "Pwntools"},
        {"name": "ropper", "display_name": "Ropper"},
    ],
    "vuln_analysis": [
        {"name": "lynis", "display_name": "Lynis"},
        {"name": "trivy", "display_name": "Trivy"},
        {"name": "grype", "display_name": "Grype"},
        {"name": "chkrootkit", "display_name": "Chkrootkit"},
        {"name": "openvas", "display_name": "OpenVAS"},
    ],
    "crypto": [
        {"name": "hashid", "display_name": "hashID"},
        {"name": "hash_identifier", "display_name": "Hash Identifier"},
        {"name": "cyberchef", "display_name": "CyberChef"},
        {"name": "stegseek", "display_name": "Stegseek"},
        {"name": "featherduster", "display_name": "FeatherDuster"},
    ],
}


@router.get("/available")
async def list_tools():
    """Return all Kali tools with local availability check."""
    results = {}
    for category, tools in _ALL_TOOLS.items():
        for tool in tools:
            available = shutil.which(tool["name"]) is not None
            results[tool["name"]] = {
                **tool,
                "category": category,
                "available": available,
            }
    return results


@router.get("/check")
async def check_tools():
    """Quick availability check for common pentest tools."""
    tool_names = ["nmap", "nikto", "sqlmap", "gobuster", "nuclei", "masscan",
                  "hydra", "john", "hashcat", "wpscan", "amass", "tshark"]
    return {name: shutil.which(name) is not None for name in tool_names}
