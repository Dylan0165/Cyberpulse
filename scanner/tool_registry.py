"""
Tool registry — metadata for all major Kali Linux security tools.

Each entry defines category, phase, description, estimated duration,
and RAM usage. The actual availability is determined at runtime by
checking if the binary exists on the system.
"""

from typing import TypedDict


class ToolMeta(TypedDict):
    category: str       # recon | vuln_scan | webapp | network | auth | ssl | osint | post_exploit | forensics | crypto
    phase: int          # 1-8, maps to scan phases
    description: str
    display_name: str
    estimated_ram_mb: int
    estimated_duration_s: int
    requires_gpu: bool
    cpu_intensive: bool


# ── Full tool registry ────────────────────────────────────────────────────────
TOOL_REGISTRY: dict[str, ToolMeta] = {

    # ── Phase 1: Reconnaissance ───────────────────────────────────────────────
    "nmap":          {"category":"recon","phase":1,"display_name":"Nmap","description":"Port scanner and service fingerprinter","estimated_ram_mb":64,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":True},
    "masscan":       {"category":"recon","phase":1,"display_name":"Masscan","description":"Fastest internet-scale port scanner","estimated_ram_mb":32,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":True},
    "netdiscover":   {"category":"recon","phase":1,"display_name":"Netdiscover","description":"Active/passive ARP host discovery","estimated_ram_mb":16,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "arp-scan":      {"category":"recon","phase":1,"display_name":"ARP-Scan","description":"ARP scanning tool for local networks","estimated_ram_mb":16,"estimated_duration_s":30,"requires_gpu":False,"cpu_intensive":False},
    "nbtscan":       {"category":"recon","phase":1,"display_name":"NBTScan","description":"NetBIOS name scanner","estimated_ram_mb":8,"estimated_duration_s":30,"requires_gpu":False,"cpu_intensive":False},
    "unicornscan":   {"category":"recon","phase":1,"display_name":"Unicornscan","description":"Asynchronous network stimulus delivery","estimated_ram_mb":32,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":True},
    "zmap":          {"category":"recon","phase":1,"display_name":"ZMap","description":"Internet-wide network scanner","estimated_ram_mb":64,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":True},
    "hping3":        {"category":"recon","phase":1,"display_name":"Hping3","description":"TCP/IP packet assembler and analyzer","estimated_ram_mb":16,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "dmitry":        {"category":"recon","phase":1,"display_name":"DMitry","description":"Deepmagic information gathering tool","estimated_ram_mb":16,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "amass":         {"category":"recon","phase":1,"display_name":"Amass","description":"In-depth attack surface mapping","estimated_ram_mb":128,"estimated_duration_s":300,"requires_gpu":False,"cpu_intensive":False},
    "subfinder":     {"category":"recon","phase":1,"display_name":"Subfinder","description":"Fast passive subdomain enumeration","estimated_ram_mb":64,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "assetfinder":   {"category":"recon","phase":1,"display_name":"Assetfinder","description":"Find domains and subdomains from various sources","estimated_ram_mb":32,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "findomain":     {"category":"recon","phase":1,"display_name":"Findomain","description":"Cross-platform subdomain enumerator","estimated_ram_mb":32,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "httpx":         {"category":"recon","phase":1,"display_name":"httpx","description":"Fast multi-purpose HTTP toolkit","estimated_ram_mb":64,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "httprobe":      {"category":"recon","phase":1,"display_name":"httprobe","description":"Probe for working HTTP/HTTPS servers","estimated_ram_mb":16,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "aquatone":      {"category":"recon","phase":1,"display_name":"Aquatone","description":"Tool for visual inspection of websites","estimated_ram_mb":256,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "gowitness":     {"category":"recon","phase":1,"display_name":"GoWitness","description":"Web screenshot utility using Chrome headless","estimated_ram_mb":512,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "eyewitness":    {"category":"recon","phase":1,"display_name":"EyeWitness","description":"Website screenshot and header grabber","estimated_ram_mb":256,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "whatweb":       {"category":"recon","phase":1,"display_name":"WhatWeb","description":"Next generation web scanner","estimated_ram_mb":64,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "wafw00f":       {"category":"recon","phase":1,"display_name":"WAF W00F","description":"Web Application Firewall fingerprinting","estimated_ram_mb":32,"estimated_duration_s":30,"requires_gpu":False,"cpu_intensive":False},
    "dnsx":          {"category":"recon","phase":1,"display_name":"DNSx","description":"Fast DNS toolkit","estimated_ram_mb":32,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "dnsrecon":      {"category":"recon","phase":1,"display_name":"DNSRecon","description":"DNS enumeration script","estimated_ram_mb":32,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "fierce":        {"category":"recon","phase":1,"display_name":"Fierce","description":"DNS reconnaissance tool","estimated_ram_mb":32,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},

    # ── Phase 2: Vulnerability Scanning ──────────────────────────────────────
    "nuclei":        {"category":"vuln_scan","phase":2,"display_name":"Nuclei","description":"Fast template-based vulnerability scanner","estimated_ram_mb":256,"estimated_duration_s":300,"requires_gpu":False,"cpu_intensive":True},
    "nikto":         {"category":"vuln_scan","phase":2,"display_name":"Nikto","description":"Web server vulnerability scanner","estimated_ram_mb":32,"estimated_duration_s":300,"requires_gpu":False,"cpu_intensive":False},
    "wpscan":        {"category":"vuln_scan","phase":2,"display_name":"WPScan","description":"WordPress vulnerability scanner","estimated_ram_mb":64,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "joomscan":      {"category":"vuln_scan","phase":2,"display_name":"JoomScan","description":"Joomla vulnerability scanner","estimated_ram_mb":32,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "droopescan":    {"category":"vuln_scan","phase":2,"display_name":"DroopeScan","description":"Drupal/Silverstripe vulnerability scanner","estimated_ram_mb":32,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "cmseek":        {"category":"vuln_scan","phase":2,"display_name":"CMSeek","description":"CMS detection and exploitation suite","estimated_ram_mb":32,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "skipfish":      {"category":"vuln_scan","phase":2,"display_name":"Skipfish","description":"Active web application security reconnaissance","estimated_ram_mb":64,"estimated_duration_s":300,"requires_gpu":False,"cpu_intensive":True},
    "w3af":          {"category":"vuln_scan","phase":2,"display_name":"W3AF","description":"Web Application Attack and Audit Framework","estimated_ram_mb":256,"estimated_duration_s":300,"requires_gpu":False,"cpu_intensive":True},
    "arachni":       {"category":"vuln_scan","phase":2,"display_name":"Arachni","description":"Web application security scanner","estimated_ram_mb":256,"estimated_duration_s":300,"requires_gpu":False,"cpu_intensive":True},
    "openvas":       {"category":"vuln_scan","phase":2,"display_name":"OpenVAS","description":"Full-featured vulnerability scanner","estimated_ram_mb":512,"estimated_duration_s":600,"requires_gpu":False,"cpu_intensive":True},
    "searchsploit":  {"category":"vuln_scan","phase":2,"display_name":"SearchSploit","description":"Offline exploit-db search tool","estimated_ram_mb":16,"estimated_duration_s":10,"requires_gpu":False,"cpu_intensive":False},
    "vulscan":       {"category":"vuln_scan","phase":2,"display_name":"Vulscan","description":"Nmap vulnerability scanning script","estimated_ram_mb":64,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},

    # ── Phase 3: Web Application Testing ─────────────────────────────────────
    "sqlmap":        {"category":"webapp","phase":3,"display_name":"SQLMap","description":"Automatic SQL injection and database takeover","estimated_ram_mb":64,"estimated_duration_s":300,"requires_gpu":False,"cpu_intensive":False},
    "ffuf":          {"category":"webapp","phase":3,"display_name":"ffuf","description":"Fast web fuzzer for directories and parameters","estimated_ram_mb":32,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "gobuster":      {"category":"webapp","phase":3,"display_name":"Gobuster","description":"Directory/file and DNS brute-forcer","estimated_ram_mb":32,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "feroxbuster":   {"category":"webapp","phase":3,"display_name":"Feroxbuster","description":"Fast, recursive content discovery tool","estimated_ram_mb":64,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "dirb":          {"category":"webapp","phase":3,"display_name":"DIRB","description":"Web content scanner based on word lists","estimated_ram_mb":16,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "dirsearch":     {"category":"webapp","phase":3,"display_name":"Dirsearch","description":"Web path scanner","estimated_ram_mb":32,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "wfuzz":         {"category":"webapp","phase":3,"display_name":"WFuzz","description":"Web application fuzzer","estimated_ram_mb":32,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "arjun":         {"category":"webapp","phase":3,"display_name":"Arjun","description":"HTTP parameter discovery suite","estimated_ram_mb":32,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "xsstrike":      {"category":"webapp","phase":3,"display_name":"XSStrike","description":"Advanced XSS detection suite","estimated_ram_mb":32,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "dalfox":        {"category":"webapp","phase":3,"display_name":"Dalfox","description":"Fast parameter analysis and XSS scanner","estimated_ram_mb":32,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "commix":        {"category":"webapp","phase":3,"display_name":"Commix","description":"Automated command injection exploiter","estimated_ram_mb":32,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "tplmap":        {"category":"webapp","phase":3,"display_name":"Tplmap","description":"Server-side template injection detection","estimated_ram_mb":32,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "jwt_tool":      {"category":"webapp","phase":3,"display_name":"JWT Tool","description":"JWT security testing toolkit","estimated_ram_mb":16,"estimated_duration_s":30,"requires_gpu":False,"cpu_intensive":False},
    "nosqlmap":      {"category":"webapp","phase":3,"display_name":"NoSQLMap","description":"Automated NoSQL database exploitation","estimated_ram_mb":32,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "ghauri":        {"category":"webapp","phase":3,"display_name":"Ghauri","description":"Advanced SQL injection detection tool","estimated_ram_mb":32,"estimated_duration_s":180,"requires_gpu":False,"cpu_intensive":False},
    "corsy":         {"category":"webapp","phase":3,"display_name":"Corsy","description":"CORS misconfiguration scanner","estimated_ram_mb":16,"estimated_duration_s":30,"requires_gpu":False,"cpu_intensive":False},

    # ── Phase 4: Network Services ─────────────────────────────────────────────
    "enum4linux":    {"category":"network","phase":4,"display_name":"Enum4linux","description":"SMB/Samba enumeration tool","estimated_ram_mb":16,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "enum4linux-ng": {"category":"network","phase":4,"display_name":"Enum4linux-ng","description":"Next-gen SMB enumeration tool","estimated_ram_mb":16,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "smbclient":     {"category":"network","phase":4,"display_name":"SMBClient","description":"SMB/CIFS file sharing client","estimated_ram_mb":16,"estimated_duration_s":30,"requires_gpu":False,"cpu_intensive":False},
    "smbmap":        {"category":"network","phase":4,"display_name":"SMBMap","description":"SMB share enumeration tool","estimated_ram_mb":16,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "rpcclient":     {"category":"network","phase":4,"display_name":"RPCClient","description":"MS-RPC endpoint enumeration","estimated_ram_mb":16,"estimated_duration_s":30,"requires_gpu":False,"cpu_intensive":False},
    "onesixtyone":   {"category":"network","phase":4,"display_name":"Onesixtyone","description":"Fast SNMP scanner","estimated_ram_mb":8,"estimated_duration_s":30,"requires_gpu":False,"cpu_intensive":False},
    "snmpwalk":      {"category":"network","phase":4,"display_name":"SNMPWalk","description":"SNMP MIB walker","estimated_ram_mb":8,"estimated_duration_s":30,"requires_gpu":False,"cpu_intensive":False},
    "snmpcheck":     {"category":"network","phase":4,"display_name":"SNMPCheck","description":"SNMP enumeration tool","estimated_ram_mb":16,"estimated_duration_s":30,"requires_gpu":False,"cpu_intensive":False},
    "ike-scan":      {"category":"network","phase":4,"display_name":"IKE-Scan","description":"IKE/IPSec VPN scanner","estimated_ram_mb":8,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "sslyze":        {"category":"network","phase":4,"display_name":"SSLyze","description":"Fast and comprehensive TLS/SSL analyser","estimated_ram_mb":32,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "sslscan":       {"category":"network","phase":4,"display_name":"SSLScan","description":"SSL/TLS cipher suite scanner","estimated_ram_mb":16,"estimated_duration_s":30,"requires_gpu":False,"cpu_intensive":False},
    "ncat":          {"category":"network","phase":4,"display_name":"Ncat","description":"Netcat with SSL support","estimated_ram_mb":8,"estimated_duration_s":30,"requires_gpu":False,"cpu_intensive":False},

    # ── Phase 5: Authentication Testing ──────────────────────────────────────
    "hydra":         {"category":"auth","phase":5,"display_name":"Hydra","description":"Network login password cracker","estimated_ram_mb":32,"estimated_duration_s":300,"requires_gpu":False,"cpu_intensive":True},
    "medusa":        {"category":"auth","phase":5,"display_name":"Medusa","description":"Modular parallel brute-forcer","estimated_ram_mb":32,"estimated_duration_s":300,"requires_gpu":False,"cpu_intensive":True},
    "ncrack":        {"category":"auth","phase":5,"display_name":"Ncrack","description":"High-speed authentication cracker","estimated_ram_mb":32,"estimated_duration_s":300,"requires_gpu":False,"cpu_intensive":True},
    "patator":       {"category":"auth","phase":5,"display_name":"Patator","description":"Multi-purpose brute-forcer","estimated_ram_mb":32,"estimated_duration_s":300,"requires_gpu":False,"cpu_intensive":True},
    "kerbrute":      {"category":"auth","phase":5,"display_name":"Kerbrute","description":"Kerberos pre-auth bruteforcing","estimated_ram_mb":32,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "evil-winrm":    {"category":"auth","phase":5,"display_name":"Evil-WinRM","description":"Windows Remote Management exploitation","estimated_ram_mb":64,"estimated_duration_s":30,"requires_gpu":False,"cpu_intensive":False},
    "crackmapexec":  {"category":"auth","phase":5,"display_name":"CrackMapExec","description":"Post-exploitation tool for AD networks","estimated_ram_mb":64,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "netexec":       {"category":"auth","phase":5,"display_name":"NetExec","description":"Network execution/enum tool (CrackMapExec successor)","estimated_ram_mb":64,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "responder":     {"category":"auth","phase":5,"display_name":"Responder","description":"LLMNR/NBT-NS poisoner and credential capture","estimated_ram_mb":32,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "hashcat":       {"category":"auth","phase":5,"display_name":"Hashcat","description":"Advanced CPU/GPU-based password recovery","estimated_ram_mb":512,"estimated_duration_s":600,"requires_gpu":True,"cpu_intensive":True},
    "john":          {"category":"auth","phase":5,"display_name":"John the Ripper","description":"Password security auditing tool","estimated_ram_mb":64,"estimated_duration_s":300,"requires_gpu":False,"cpu_intensive":True},
    "spray":         {"category":"auth","phase":5,"display_name":"Spray","description":"Password spraying tool","estimated_ram_mb":16,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "crowbar":       {"category":"auth","phase":5,"display_name":"Crowbar","description":"Brute-forcing tool for RDP/VNC/OpenVPN","estimated_ram_mb":32,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},

    # ── Phase 6: SSL/TLS Analysis ─────────────────────────────────────────────
    "testssl.sh":    {"category":"ssl","phase":6,"display_name":"testssl.sh","description":"Testing TLS/SSL encryption anywhere","estimated_ram_mb":32,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "tlssled":       {"category":"ssl","phase":6,"display_name":"TLSSLed","description":"TLS/SSL security testing script","estimated_ram_mb":16,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},

    # ── Phase 7: Post-Exploitation ────────────────────────────────────────────
    "msfconsole":    {"category":"post_exploit","phase":7,"display_name":"Metasploit","description":"Exploitation framework","estimated_ram_mb":512,"estimated_duration_s":300,"requires_gpu":False,"cpu_intensive":True},
    "msfvenom":      {"category":"post_exploit","phase":7,"display_name":"MSFVenom","description":"Metasploit payload generator","estimated_ram_mb":256,"estimated_duration_s":30,"requires_gpu":False,"cpu_intensive":False},
    "impacket-scripts":{"category":"post_exploit","phase":7,"display_name":"Impacket","description":"Python classes for network protocols","estimated_ram_mb":64,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "certipy":       {"category":"post_exploit","phase":7,"display_name":"Certipy","description":"Active Directory certificate abuse","estimated_ram_mb":32,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},

    # ── Phase 8: OSINT & Secrets ──────────────────────────────────────────────
    "theharvester":  {"category":"osint","phase":8,"display_name":"theHarvester","description":"Email/domain/IP OSINT tool","estimated_ram_mb":64,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "recon-ng":      {"category":"osint","phase":8,"display_name":"Recon-ng","description":"Full-featured web reconnaissance framework","estimated_ram_mb":64,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "spiderfoot":    {"category":"osint","phase":8,"display_name":"SpiderFoot","description":"Automated OSINT collection","estimated_ram_mb":128,"estimated_duration_s":300,"requires_gpu":False,"cpu_intensive":False},
    "maltego":       {"category":"osint","phase":8,"display_name":"Maltego","description":"Link analysis and data mining","estimated_ram_mb":512,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "shodan":        {"category":"osint","phase":8,"display_name":"Shodan CLI","description":"Shodan internet intelligence search","estimated_ram_mb":16,"estimated_duration_s":30,"requires_gpu":False,"cpu_intensive":False},
    "metagoofil":    {"category":"osint","phase":8,"display_name":"Metagoofil","description":"Metadata extraction from public documents","estimated_ram_mb":32,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "exiftool":      {"category":"osint","phase":8,"display_name":"ExifTool","description":"Read/write metadata from files","estimated_ram_mb":16,"estimated_duration_s":10,"requires_gpu":False,"cpu_intensive":False},
    "gitleaks":      {"category":"osint","phase":8,"display_name":"Gitleaks","description":"Detect hardcoded secrets in git repos","estimated_ram_mb":64,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "trufflehog":    {"category":"osint","phase":8,"display_name":"TruffleHog","description":"Find credentials in git history","estimated_ram_mb":128,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "gitrob":        {"category":"osint","phase":8,"display_name":"Gitrob","description":"GitHub reconnaissance tool","estimated_ram_mb":64,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":False},
    "osrframework":  {"category":"osint","phase":8,"display_name":"OSRFramework","description":"Username/email OSINT searches","estimated_ram_mb":32,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},

    # ── Forensics ─────────────────────────────────────────────────────────────
    "volatility3":   {"category":"forensics","phase":8,"display_name":"Volatility3","description":"Memory forensics framework","estimated_ram_mb":512,"estimated_duration_s":300,"requires_gpu":False,"cpu_intensive":True},
    "binwalk":       {"category":"forensics","phase":8,"display_name":"Binwalk","description":"Firmware analysis tool","estimated_ram_mb":64,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
    "foremost":      {"category":"forensics","phase":8,"display_name":"Foremost","description":"File recovery tool","estimated_ram_mb":64,"estimated_duration_s":120,"requires_gpu":False,"cpu_intensive":True},
    "steghide":      {"category":"forensics","phase":8,"display_name":"Steghide","description":"Steganography detection/extraction","estimated_ram_mb":16,"estimated_duration_s":30,"requires_gpu":False,"cpu_intensive":False},
    "stegseek":      {"category":"forensics","phase":8,"display_name":"Stegseek","description":"Ultrafast steganography cracker","estimated_ram_mb":32,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":True},
    "radare2":       {"category":"forensics","phase":8,"display_name":"Radare2","description":"Advanced binary analysis framework","estimated_ram_mb":128,"estimated_duration_s":60,"requires_gpu":False,"cpu_intensive":False},
}


def get_tool_meta(tool_name: str) -> ToolMeta:
    """Return metadata for a tool, or a sensible default if unknown."""
    if tool_name in TOOL_REGISTRY:
        return TOOL_REGISTRY[tool_name]
    return {
        "category": "recon",
        "phase": 1,
        "display_name": tool_name.replace("-", " ").replace("_", " ").title(),
        "description": f"{tool_name} security tool",
        "estimated_ram_mb": 64,
        "estimated_duration_s": 120,
        "requires_gpu": False,
        "cpu_intensive": False,
    }
