"""CyberPulse — Application configuration loaded from environment."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_ROOT = Path(__file__).resolve().parent
load_dotenv(_ROOT / ".env")


class Config:
    """Central configuration — all values sourced from .env or defaults."""

    # ── Paths ──────────────────────────────────────────────
    ROOT_DIR: Path = _ROOT
    DATA_DIR: Path = _ROOT / os.getenv("DATA_DIR", "data")
    SCANS_DIR: Path = _ROOT / os.getenv("SCANS_DIR", "data/scans")
    LOG_FILE: Path = _ROOT / os.getenv("LOG_FILE", "data/cyberpulse.log")

    # ── DeepSeek AI ────────────────────────────────────────
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    DEEPSEEK_TEMPERATURE: float = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.3"))
    DEEPSEEK_MAX_TOKENS: int = int(os.getenv("DEEPSEEK_MAX_TOKENS", "8192"))

    # ── Flask / API ─────────────────────────────────────────
    FLASK_HOST: str = os.getenv("FLASK_HOST", "127.0.0.1")
    FLASK_PORT: int = int(os.getenv("FLASK_PORT", "7823"))
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    FLASK_SECRET_KEY: str = os.getenv("FLASK_SECRET_KEY", "cyberpulse-dev-secret-change-in-production")
    API_KEY: str = os.getenv("API_KEY", "")  # Set in .env to enable auth

    # ── Data Files ─────────────────────────────────────────
    SCHEDULES_FILE: Path = _ROOT / os.getenv("SCHEDULES_FILE", "data/schedules.json")

    # ── Logging ────────────────────────────────────────────
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # ── Scanner ────────────────────────────────────────────
    SCAN_TIMEOUT: int = int(os.getenv("SCAN_TIMEOUT", "28800"))
    NMAP_TIMING: str = os.getenv("NMAP_TIMING", "T4")
    MAX_THREADS: int = int(os.getenv("MAX_THREADS", "50"))
    RATE_LIMIT: int = int(os.getenv("RATE_LIMIT", "10000"))

    # ── Wordlists ──────────────────────────────────────────
    SECLISTS_PATH: str = os.getenv("SECLISTS_PATH", "/usr/share/seclists")
    WORDLIST_DIR: str = os.getenv("WORDLIST_DIR", "/usr/share/wordlists")

    # ── Optional API Keys ──────────────────────────────────
    HIBP_API_KEY: str = os.getenv("HIBP_API_KEY", "")
    ABUSEIPDB_API_KEY: str = os.getenv("ABUSEIPDB_API_KEY", "")
    VIRUSTOTAL_API_KEY: str = os.getenv("VIRUSTOTAL_API_KEY", "")
    SHODAN_API_KEY: str = os.getenv("SHODAN_API_KEY", "")

    # ── Scraper ────────────────────────────────────────────
    SCRAPER_ENABLED: bool = os.getenv("SCRAPER_ENABLED", "true").lower() == "true"
    SCRAPER_HOUR: int = int(os.getenv("SCRAPER_HOUR", "3"))
    SCRAPER_MINUTE: int = int(os.getenv("SCRAPER_MINUTE", "0"))

    # ── Laptop Mode & Tool Settings ───────────────────────
    LAPTOP_MODE: bool = os.getenv("LAPTOP_MODE", "true").lower() == "true"
    TOOL_MAX_PARALLEL: int = int(os.getenv("TOOL_MAX_PARALLEL", "3"))
    TOOL_DEFAULT_TIMEOUT: int = int(os.getenv("TOOL_DEFAULT_TIMEOUT", "300"))
    TOOL_RATE_LIMIT: int = int(os.getenv("TOOL_RATE_LIMIT", "1000"))  # pps for network tools

    # ── Tool Scan Profiles ─────────────────────────────────
    TOOL_SCAN_PROFILES: dict = {
        "web_full": ["sqlmap", "nikto", "gobuster", "nuclei", "wpscan", "xsstrike", "commix", "arjun"],
        "web_quick": ["nikto", "gobuster", "nuclei"],
        "network_full": ["masscan", "netdiscover", "arpscan", "hping3", "tshark"],
        "network_quick": ["masscan", "tshark"],
        "recon_full": ["theharvester", "amass", "dnsrecon", "fierce", "spiderfoot"],
        "recon_quick": ["theharvester", "dnsrecon"],
        "password_audit": ["john", "hashcat", "hydra", "hashid"],
        "vuln_scan": ["nuclei", "lynis", "trivy", "grype"],
        "exploitation": ["searchsploit"],
        "forensics": ["volatility3", "binwalk", "exiftool", "strings_tool"],
        "crypto_audit": ["hashid", "hash_identifier", "stegseek"],
    }

    # ── Module Registry ────────────────────────────────────
    QUICK_MODULES: list = ["01", "02", "03", "07", "08", "11", "09", "17"]
    ALL_MODULES: list = [f"{i:02d}" for i in range(1, 71)] + [str(i) for i in range(91, 102)]

    # Gray-box modules (require web/API credentials)
    GRAYBOX_MODULES: list = ["71", "72", "73", "74", "75", "76", "77", "78", "79", "80"]

    # White-box modules (require SSH/source code access)
    WHITEBOX_MODULES: list = ["81", "82", "83", "84", "85", "86", "87", "88", "89", "90"]

    # Mobile modules
    MOBILE_ANDROID_MODULES: list = ["98b"]
    MOBILE_IOS_MODULES: list = ["98c"]

    # Desktop modules
    DESKTOP_MODULES: list = ["101"]

    MODULE_INFO: dict = {
        # ── Modules 01-20: Core Recon & Scanning ──
        "01": {"name": "Port Scanning", "phase": "reconnaissance", "cost": "€0.10"},
        "02": {"name": "Service Enumeration", "phase": "reconnaissance", "cost": "€0.20"},
        "03": {"name": "Web Discovery", "phase": "reconnaissance", "cost": "€0.15"},
        "04": {"name": "Web Vulnerabilities", "phase": "scanning", "cost": "€0.50"},
        "05": {"name": "Injection Testing", "phase": "scanning", "cost": "€1.00"},
        "06": {"name": "Authentication", "phase": "scanning", "cost": "€0.75"},
        "07": {"name": "SSL/TLS Audit", "phase": "scanning", "cost": "€0.10"},
        "08": {"name": "DNS Reconnaissance", "phase": "reconnaissance", "cost": "€0.05"},
        "09": {"name": "Subdomain Enumeration", "phase": "reconnaissance", "cost": "€0.30"},
        "10": {"name": "OSINT", "phase": "reconnaissance", "cost": "€0.40"},
        "11": {"name": "Headers & Cookies", "phase": "scanning", "cost": "€0.05"},
        "12": {"name": "Vulnerability Scan", "phase": "scanning", "cost": "€2.00"},
        "13": {"name": "Network Services", "phase": "scanning", "cost": "€0.80"},
        "14": {"name": "SMB & LDAP", "phase": "scanning", "cost": "€0.60"},
        "15": {"name": "Email Security", "phase": "scanning", "cost": "€0.25"},
        "16": {"name": "Cloud Exposure", "phase": "reconnaissance", "cost": "€0.90"},
        "17": {"name": "API Testing", "phase": "scanning", "cost": "€1.50"},
        "18": {"name": "Fuzzing", "phase": "exploitation", "cost": "€3.00"},
        "19": {"name": "CMS Scanning", "phase": "scanning", "cost": "€0.50"},
        "20": {"name": "Breach Check", "phase": "post", "cost": "€0.15"},
        # ── Modules 21-30: Active Exploitation ──
        "21": {"name": "Firewall & WAF Detection", "phase": "reconnaissance", "cost": "€0.35"},
        "22": {"name": "CORS Misconfiguration", "phase": "scanning", "cost": "€0.20"},
        "23": {"name": "GraphQL Testing", "phase": "scanning", "cost": "€0.45"},
        "24": {"name": "WebSocket Security", "phase": "scanning", "cost": "€0.30"},
        "25": {"name": "Default Credentials", "phase": "exploitation", "cost": "€0.50"},
        "26": {"name": "File Upload Testing", "phase": "exploitation", "cost": "€0.60"},
        "27": {"name": "SSRF Testing", "phase": "exploitation", "cost": "€0.70"},
        "28": {"name": "XXE Testing", "phase": "exploitation", "cost": "€0.55"},
        "29": {"name": "JWT Token Analysis", "phase": "scanning", "cost": "€0.25"},
        "30": {"name": "OAuth & SAML Testing", "phase": "scanning", "cost": "€0.40"},
        # ── Modules 31-40: Post-Exploitation & Advanced ──
        "31": {"name": "Directory Traversal & LFI", "phase": "exploitation", "cost": "€0.65"},
        "32": {"name": "Remote Code Execution", "phase": "exploitation", "cost": "€0.90"},
        "33": {"name": "Privilege Escalation", "phase": "exploitation", "cost": "€0.80"},
        "34": {"name": "Lateral Movement", "phase": "exploitation", "cost": "€0.75"},
        "35": {"name": "Active Directory Recon", "phase": "exploitation", "cost": "€0.85"},
        "36": {"name": "Kerberos Attacks", "phase": "exploitation", "cost": "€0.70"},
        "37": {"name": "Database Exploitation", "phase": "exploitation", "cost": "€0.95"},
        "38": {"name": "Backup File Discovery", "phase": "reconnaissance", "cost": "€0.30"},
        "39": {"name": "Source Code Leaks", "phase": "reconnaissance", "cost": "€0.35"},
        "40": {"name": "Session Management", "phase": "scanning", "cost": "€0.40"},
        # ── Modules 41-50: Advanced & Specialized ──
        "41": {"name": "Rate Limiting & DoS", "phase": "scanning", "cost": "€0.45"},
        "42": {"name": "2FA/MFA Bypass", "phase": "exploitation", "cost": "€0.60"},
        "43": {"name": "Business Logic Flaws", "phase": "exploitation", "cost": "€0.85"},
        "44": {"name": "API Security Deep", "phase": "scanning", "cost": "€1.20"},
        "45": {"name": "Subdomain Takeover", "phase": "scanning", "cost": "€0.50"},
        "46": {"name": "DNS Zone Transfer", "phase": "reconnaissance", "cost": "€0.25"},
        "47": {"name": "Network Service Security", "phase": "scanning", "cost": "€0.70"},
        "48": {"name": "OWASP Top 10 Compliance", "phase": "scanning", "cost": "€1.50"},
        "49": {"name": "IPv6 Security", "phase": "scanning", "cost": "€0.35"},
        "50": {"name": "Evidence & Reporting", "phase": "reporting", "cost": "€0.10"},
        # ── Modules 51-65: Advanced Exploitation & Recon ──
        "51": {"name": "HTTP Request Smuggling",        "phase": "exploitation",   "cost": "€0.45"},
        "52": {"name": "Web Cache Poisoning",            "phase": "exploitation",   "cost": "€0.40"},
        "53": {"name": "Prototype Pollution",            "phase": "exploitation",   "cost": "€0.35"},
        "54": {"name": "Deserialization Testing",        "phase": "exploitation",   "cost": "€0.55"},
        "55": {"name": "SSTI Detection",                "phase": "exploitation",   "cost": "€0.50"},
        "56": {"name": "Clickjacking & UI Redressing",  "phase": "scanning",       "cost": "€0.20"},
        "57": {"name": "Open Redirect Testing",         "phase": "scanning",       "cost": "€0.25"},
        "58": {"name": "HTTP Parameter Pollution",      "phase": "scanning",       "cost": "€0.20"},
        "59": {"name": "CSP Deep Analysis",             "phase": "scanning",       "cost": "€0.30"},
        "60": {"name": "Password Policy Analysis",      "phase": "scanning",       "cost": "€0.40"},
        "61": {"name": "Certificate Transparency",      "phase": "reconnaissance", "cost": "€0.25"},
        "62": {"name": "Threat Intelligence",           "phase": "reconnaissance", "cost": "€0.60"},
        "63": {"name": "Docker & Container Exposure",   "phase": "reconnaissance", "cost": "€0.50"},
        "64": {"name": "Kubernetes Exposure",           "phase": "reconnaissance", "cost": "€0.70"},
        "65": {"name": "Serverless Functions Discovery","phase": "reconnaissance", "cost": "€0.45"},
        # ── Modules 66-70: Supply Chain & Synthesis ──
        "66": {"name": "Third-Party Script Analysis",   "phase": "scanning",       "cost": "€0.35"},
        "67": {"name": "Mobile API Detection",          "phase": "scanning",       "cost": "€0.40"},
        "68": {"name": "CI/CD Pipeline Exposure",       "phase": "reconnaissance", "cost": "€0.55"},
        "69": {"name": "Dependency Confusion",          "phase": "reconnaissance", "cost": "€0.45"},
        "70": {"name": "Attack Chain Simulation",       "phase": "reporting",      "cost": "€0.75"},
        # ── Gray-box Modules 71-80 (require credentials) ──
        "71": {"name": "Authenticated Web Scanning",     "phase": "scanning",       "cost": "€1.20", "mode": "graybox"},
        "72": {"name": "Authenticated API Testing",      "phase": "scanning",       "cost": "€1.50", "mode": "graybox"},
        "73": {"name": "Session & Cookie Audit",         "phase": "scanning",       "cost": "€0.80", "mode": "graybox"},
        "74": {"name": "Authenticated CMS Audit",        "phase": "scanning",       "cost": "€0.90", "mode": "graybox"},
        "75": {"name": "Database Connectivity Test",     "phase": "exploitation",   "cost": "€1.00", "mode": "graybox"},
        "76": {"name": "Internal Port Scan (Auth)",      "phase": "reconnaissance", "cost": "€0.70", "mode": "graybox"},
        "77": {"name": "Admin Panel Discovery",          "phase": "scanning",       "cost": "€0.60", "mode": "graybox"},
        "78": {"name": "Privilege Escalation (Auth)",   "phase": "exploitation",   "cost": "€1.20", "mode": "graybox"},
        "79": {"name": "IDOR / Broken Access Control",  "phase": "exploitation",   "cost": "€1.10", "mode": "graybox"},
        "80": {"name": "Authenticated File Inclusion",   "phase": "exploitation",   "cost": "€0.90", "mode": "graybox"},
        # ── White-box Modules 81-90 (require SSH/source access) ──
        "81": {"name": "SSH System Audit (Lynis)",       "phase": "scanning",       "cost": "€2.00", "mode": "whitebox"},
        "82": {"name": "Source Code SAST Scan",          "phase": "scanning",       "cost": "€2.50", "mode": "whitebox"},
        "83": {"name": "Config File Audit",              "phase": "scanning",       "cost": "€1.50", "mode": "whitebox"},
        "84": {"name": "Dependency Vulnerability Scan",  "phase": "scanning",       "cost": "€1.80", "mode": "whitebox"},
        "85": {"name": "Hardcoded Secrets Detection",    "phase": "scanning",       "cost": "€1.20", "mode": "whitebox"},
        "86": {"name": "File Permissions Audit",         "phase": "scanning",       "cost": "€0.80", "mode": "whitebox"},
        "87": {"name": "User & Group Account Audit",     "phase": "scanning",       "cost": "€0.70", "mode": "whitebox"},
        "88": {"name": "Running Services Audit",         "phase": "scanning",       "cost": "€0.90", "mode": "whitebox"},
        "89": {"name": "Network Configuration Audit",    "phase": "scanning",       "cost": "€1.00", "mode": "whitebox"},
        "90": {"name": "Docker / Container Audit",       "phase": "scanning",       "cost": "€1.30", "mode": "whitebox"},
        # ── V2 Modules 91-101: Advanced Tooling ──
        "91": {"name": "Nuclei Template Scanner",        "phase": "vulnerability_scan", "cost": "€0.80"},
        "92": {"name": "Gobuster Directory Fuzzing",     "phase": "discovery",          "cost": "€0.40"},
        "93": {"name": "SQLmap Injection Testing",       "phase": "exploitation",       "cost": "€1.50"},
        "94": {"name": "Testssl.sh TLS Audit",           "phase": "scanning",           "cost": "€0.20"},
        "95": {"name": "Feroxbuster Recursive Scan",     "phase": "discovery",          "cost": "€0.60"},
        "96": {"name": "Nmap NSE Scripts",               "phase": "vulnerability_scan", "cost": "€0.70"},
        "97": {"name": "WhatWeb Fingerprinting",         "phase": "reconnaissance",     "cost": "€0.15"},
        "98": {"name": "Gitleaks Secrets Scanner",       "phase": "discovery",          "cost": "€0.50"},
        "98b": {"name": "Android APK Analysis",          "phase": "analysis",           "cost": "€1.00", "mode": "mobile"},
        "98c": {"name": "iOS IPA Analysis",              "phase": "analysis",           "cost": "€1.00", "mode": "mobile"},
        "99": {"name": "Metasploit Auxiliary Scanner",   "phase": "vulnerability_scan", "cost": "€1.20"},
        "100": {"name": "Shodan API Intelligence",       "phase": "reconnaissance",     "cost": "€0.30"},
        "101": {"name": "Desktop Binary Analysis",       "phase": "analysis",           "cost": "€0.80", "mode": "desktop"},
    }

    @classmethod
    def ensure_dirs(cls):
        """Create required data directories if they don't exist."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.SCANS_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls):
        """Check that critical configuration is present."""
        issues = []
        if not cls.DEEPSEEK_API_KEY:
            issues.append("DEEPSEEK_API_KEY is not set — AI analysis will be unavailable")
        return issues
