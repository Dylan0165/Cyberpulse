#!/usr/bin/env python3
"""
Scanner container entrypoint.
Reads scan configuration from environment, enforces scope via iptables,
then executes the requested scan phases in sequence.
Results are pushed to Redis for the backend to consume.
"""

import json
import os
import subprocess
import sys
import ipaddress
import socket
import time
import redis

SCAN_CONFIG = json.loads(os.environ.get("SCAN_CONFIG", "{}"))
REDIS_URL = os.environ.get("REDIS_URL", "")
SCAN_ID = os.environ.get("SCAN_ID", "")
PHASE = os.environ.get("SCAN_PHASE", "")


def get_redis():
    return redis.from_url(REDIS_URL, decode_responses=True)


def publish(channel: str, data: dict):
    r = get_redis()
    r.publish(channel, json.dumps(data))


def push_output(phase: str, tool: str, output: str):
    r = get_redis()
    key = f"scan:{SCAN_ID}:output:{phase}:{tool}"
    r.setex(key, 3600, output)  # 1-hour TTL
    publish(f"scan:{SCAN_ID}:live", {
        "type": "tool_output",
        "phase": phase,
        "tool": tool,
        "output": output[:5000],  # Truncate for live feed
        "timestamp": time.time(),
    })


def enforce_scope():
    """Apply iptables rules to restrict outbound traffic to only in-scope targets."""
    targets = SCAN_CONFIG.get("targets", [])
    allowed_ips = set()

    for target in targets:
        t = target.get("value", "")
        t_type = target.get("type", "")
        if t_type == "ip":
            allowed_ips.add(t)
        elif t_type == "ip_range":
            try:
                network = ipaddress.ip_network(t, strict=False)
                for ip in network.hosts():
                    allowed_ips.add(str(ip))
                    if len(allowed_ips) > 65536:
                        break
            except ValueError:
                pass
        elif t_type == "domain":
            try:
                ip = socket.gethostbyname(t)
                allowed_ips.add(ip)
            except socket.gaierror:
                pass

    # Allow loopback and DNS
    subprocess.run(["iptables", "-A", "OUTPUT", "-o", "lo", "-j", "ACCEPT"], check=False)
    subprocess.run(["iptables", "-A", "OUTPUT", "-p", "udp", "--dport", "53", "-j", "ACCEPT"], check=False)
    subprocess.run(["iptables", "-A", "OUTPUT", "-p", "tcp", "--dport", "53", "-j", "ACCEPT"], check=False)

    # Allow Redis connection (internal network)
    redis_host = os.environ.get("REDIS_HOST", "redis")
    try:
        redis_ip = socket.gethostbyname(redis_host)
        subprocess.run(["iptables", "-A", "OUTPUT", "-d", redis_ip, "-j", "ACCEPT"], check=False)
    except socket.gaierror:
        pass

    # Allow only in-scope IPs
    for ip in allowed_ips:
        subprocess.run(["iptables", "-A", "OUTPUT", "-d", ip, "-j", "ACCEPT"], check=False)

    # Block metadata endpoints (169.254.169.254 etc.) — prevent SSRF to cloud metadata
    subprocess.run(["iptables", "-A", "OUTPUT", "-d", "169.254.169.254", "-j", "DROP"], check=False)

    # Drop everything else
    subprocess.run(["iptables", "-A", "OUTPUT", "-j", "DROP"], check=False)

    # Block RFC1918 ranges unless explicitly in scope
    private_ranges = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
    for pr in private_ranges:
        in_scope = any(
            t.get("value", "").startswith(pr.split("/")[0][:3])
            for t in targets
        )
        if not in_scope:
            subprocess.run(["iptables", "-I", "OUTPUT", "1", "-d", pr, "-j", "DROP"], check=False)


def run_tool(cmd: list, phase: str, tool_name: str, timeout: int = 600) -> str:
    """Execute a tool subprocess with timeout and capture output."""
    publish(f"scan:{SCAN_ID}:live", {
        "type": "tool_start",
        "phase": phase,
        "tool": tool_name,
        "timestamp": time.time(),
    })

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout + "\n" + result.stderr
    except subprocess.TimeoutExpired:
        output = f"[TIMEOUT] {tool_name} exceeded {timeout}s limit"
    except FileNotFoundError:
        output = f"[SKIP] {tool_name} not found in container"
    except Exception as e:
        output = f"[ERROR] {tool_name}: {str(e)}"

    push_output(phase, tool_name, output)

    publish(f"scan:{SCAN_ID}:live", {
        "type": "tool_complete",
        "phase": phase,
        "tool": tool_name,
        "timestamp": time.time(),
    })

    return output


def get_primary_target() -> str:
    targets = SCAN_CONFIG.get("targets", [])
    for t in targets:
        if t.get("type") == "domain":
            return t["value"]
    for t in targets:
        return t.get("value", "")
    return ""


def get_all_targets_str() -> str:
    return " ".join(t["value"] for t in SCAN_CONFIG.get("targets", []))


def phase_recon():
    target = get_primary_target()
    if not target:
        return

    # Nmap TCP SYN scan + version detection + OS fingerprinting
    run_tool(
        ["nmap", "-sS", "-sV", "-O", "--top-ports", "1000", "-oN", "/tmp/nmap_tcp.txt", target],
        "recon", "nmap_tcp", timeout=900
    )
    # Nmap UDP top 1000
    run_tool(
        ["nmap", "-sU", "--top-ports", "1000", "-oN", "/tmp/nmap_udp.txt", target],
        "recon", "nmap_udp", timeout=900
    )
    # theHarvester
    run_tool(
        ["theHarvester", "-d", target, "-b", "all", "-f", "/tmp/harvester.json"],
        "recon", "theharvester", timeout=300
    )
    # Amass passive enum
    run_tool(
        ["amass", "enum", "-passive", "-d", target, "-o", "/tmp/amass.txt"],
        "recon", "amass", timeout=600
    )
    # DNSRecon
    run_tool(
        ["dnsrecon", "-d", target, "-t", "std,brt", "-j", "/tmp/dnsrecon.json"],
        "recon", "dnsrecon", timeout=300
    )
    # DNSEnum
    run_tool(
        ["dnsenum", target],
        "recon", "dnsenum", timeout=300
    )
    # Sublist3r
    run_tool(
        ["sublist3r", "-d", target, "-o", "/tmp/sublist3r.txt"],
        "recon", "sublist3r", timeout=300
    )
    # WHOIS
    run_tool(
        ["whois", target],
        "recon", "whois", timeout=60
    )
    # Shodan (if API key available)
    shodan_key = os.environ.get("SHODAN_API_KEY", "")
    if shodan_key:
        run_tool(
            ["shodan", "host", target],
            "recon", "shodan", timeout=60
        )


def phase_vulnerability():
    target = get_primary_target()
    if not target:
        return

    # Nuclei
    run_tool(
        ["nuclei", "-u", f"https://{target}", "-severity", "critical,high,medium,low",
         "-o", "/tmp/nuclei.txt", "-silent"],
        "vulnerability", "nuclei", timeout=1200
    )
    # Nikto
    run_tool(
        ["nikto", "-h", target, "-output", "/tmp/nikto.txt", "-Format", "txt"],
        "vulnerability", "nikto", timeout=600
    )
    # SearchSploit
    run_tool(
        ["searchsploit", "--nmap", "/tmp/nmap_tcp.txt"],
        "vulnerability", "searchsploit", timeout=120
    )


def phase_webapp():
    target = get_primary_target()
    if not target:
        return

    url = f"https://{target}"

    # WhatWeb
    run_tool(
        ["whatweb", "-v", url],
        "webapp", "whatweb", timeout=120
    )
    # WAF detection
    run_tool(
        ["wafw00f", url],
        "webapp", "wafw00f", timeout=60
    )
    # Directory brute force with ffuf
    run_tool(
        ["ffuf", "-u", f"{url}/FUZZ", "-w", "/usr/share/seclists/Discovery/Web-Content/common.txt",
         "-mc", "200,301,302,403", "-o", "/tmp/ffuf.json", "-of", "json", "-t", "20"],
        "webapp", "ffuf", timeout=600
    )
    # SQLMap (safe level only)
    run_tool(
        ["sqlmap", "-u", url, "--batch", "--level=1", "--risk=1",
         "--output-dir=/tmp/sqlmap", "--forms", "--crawl=2"],
        "webapp", "sqlmap", timeout=600
    )
    # Dalfox XSS scan
    run_tool(
        ["dalfox", "url", url, "--silence", "-o", "/tmp/dalfox.txt"],
        "webapp", "dalfox", timeout=600
    )
    # Commix command injection
    run_tool(
        ["commix", "--url", url, "--batch", "--output-dir=/tmp/commix"],
        "webapp", "commix", timeout=300
    )
    # GoBuster
    run_tool(
        ["gobuster", "dir", "-u", url, "-w", "/usr/share/seclists/Discovery/Web-Content/directory-list-2.3-small.txt",
         "-o", "/tmp/gobuster.txt", "-t", "20", "-q"],
        "webapp", "gobuster", timeout=600
    )


def phase_network():
    target = get_primary_target()
    if not target:
        return

    # NSE scripts
    run_tool(
        ["nmap", "--script", "smb-vuln*,smb-enum*", "-p", "445", target],
        "network", "nmap_smb", timeout=300
    )
    run_tool(
        ["nmap", "--script", "snmp-brute,snmp-info", "-p", "161", "-sU", target],
        "network", "nmap_snmp", timeout=300
    )
    # enum4linux-ng
    run_tool(
        ["enum4linux-ng", "-A", target],
        "network", "enum4linux", timeout=300
    )
    # NetExec SMB
    run_tool(
        ["netexec", "smb", target],
        "network", "netexec_smb", timeout=120
    )
    # Banner grabbing
    run_tool(
        ["nmap", "-sV", "--script=banner", "-p", "1-1000", target],
        "network", "banner_grab", timeout=300
    )


def phase_auth():
    target = get_primary_target()
    if not target:
        return

    # Hydra SSH (top 10 passwords only - ethical)
    run_tool(
        ["hydra", "-l", "admin", "-P", "/usr/share/seclists/Passwords/Common-Credentials/top-20-common-SSH-passwords.txt",
         "-t", "4", "-f", target, "ssh"],
        "auth", "hydra_ssh", timeout=300
    )
    # Hydra FTP
    run_tool(
        ["hydra", "-l", "anonymous", "-p", "anonymous@", "-f", target, "ftp"],
        "auth", "hydra_ftp", timeout=120
    )
    # Default credentials nmap script
    run_tool(
        ["nmap", "--script", "http-default-accounts", "-p", "80,443,8080,8443", target],
        "auth", "nmap_default_creds", timeout=300
    )


def phase_ssl():
    target = get_primary_target()
    if not target:
        return

    # testssl.sh
    run_tool(
        ["testssl.sh", "--jsonfile", "/tmp/testssl.json", target],
        "ssl", "testssl", timeout=600
    )
    # SSLyze
    run_tool(
        ["sslyze", target, "--json_out", "/tmp/sslyze.json"],
        "ssl", "sslyze", timeout=300
    )
    # SSLScan
    run_tool(
        ["sslscan", "--xml=/tmp/sslscan.xml", target],
        "ssl", "sslscan", timeout=120
    )


def phase_cloud():
    target = get_primary_target()
    if not target:
        return

    # Trivy (if container registry URL provided)
    registry_url = SCAN_CONFIG.get("container_registry", "")
    if registry_url:
        run_tool(
            ["trivy", "image", "--severity", "CRITICAL,HIGH", "--format", "json",
             "--output", "/tmp/trivy.json", registry_url],
            "cloud", "trivy", timeout=600
        )

    # Check cloud metadata exposure
    run_tool(
        ["nmap", "--script", "http-headers", "-p", "80,443,8080", target],
        "cloud", "cloud_headers", timeout=120
    )

    # S3 bucket enum
    run_tool(
        ["gobuster", "s3", "-w", "/usr/share/seclists/Discovery/Cloud/s3-common.txt",
         "-o", "/tmp/s3_enum.txt", "-q"],
        "cloud", "s3_enum", timeout=300
    )


def phase_osint():
    target = get_primary_target()
    if not target:
        return

    # theHarvester (emails)
    run_tool(
        ["theHarvester", "-d", target, "-b", "all", "-f", "/tmp/osint_harvest.json"],
        "osint", "theharvester_osint", timeout=300
    )
    # GitLeaks (public repos)
    run_tool(
        ["gitleaks", "detect", "--source", f"https://github.com/{target}",
         "--report-path", "/tmp/gitleaks.json", "--report-format", "json"],
        "osint", "gitleaks", timeout=300
    )


PHASES = {
    "recon": phase_recon,
    "vulnerability": phase_vulnerability,
    "webapp": phase_webapp,
    "network": phase_network,
    "auth": phase_auth,
    "ssl": phase_ssl,
    "cloud": phase_cloud,
    "osint": phase_osint,
}


def main():
    if not SCAN_ID or not SCAN_CONFIG:
        print("Missing SCAN_ID or SCAN_CONFIG", file=sys.stderr)
        sys.exit(1)

    # Enforce network scope
    enforce_scope()

    publish(f"scan:{SCAN_ID}:live", {
        "type": "phase_start",
        "phase": PHASE,
        "timestamp": time.time(),
    })

    # Run requested phase
    if PHASE in PHASES:
        PHASES[PHASE]()
    elif PHASE == "all":
        for phase_name, phase_fn in PHASES.items():
            publish(f"scan:{SCAN_ID}:live", {
                "type": "phase_start",
                "phase": phase_name,
                "timestamp": time.time(),
            })
            phase_fn()
            publish(f"scan:{SCAN_ID}:live", {
                "type": "phase_complete",
                "phase": phase_name,
                "timestamp": time.time(),
            })
    else:
        print(f"Unknown phase: {PHASE}", file=sys.stderr)
        sys.exit(1)

    publish(f"scan:{SCAN_ID}:live", {
        "type": "phase_complete",
        "phase": PHASE,
        "timestamp": time.time(),
    })

    publish(f"scan:{SCAN_ID}:live", {
        "type": "scan_complete",
        "timestamp": time.time(),
    })


if __name__ == "__main__":
    main()
