"""M62 — Threat Intelligence Enrichment."""
import requests

class Scanner:
    name = "Threat Intelligence"
    phase = "reconnaissance"
    description = "Enrich target with threat intelligence data from public sources."

    def __init__(self, target, output_dir, config):
        self.target = target.split(":")[0]
        self.output_dir = output_dir
        self.config = config

    def run(self):
        findings, raw = [], []
        timeout = self.config.get("timeout", 15)
        abuseipdb_key = self.config.get("ABUSEIPDB_API_KEY", "")
        vt_key = self.config.get("VIRUSTOTAL_API_KEY", "")
        shodan_key = self.config.get("SHODAN_API_KEY", "")

        # Resolve target to IP
        import socket
        try:
            ip = socket.gethostbyname(self.target)
            raw.append(f"Resolved {self.target} -> {ip}")
        except Exception as e:
            ip = None
            raw.append(f"DNS resolution failed: {e}")

        # AbuseIPDB lookup
        if abuseipdb_key and ip:
            try:
                r = requests.get(
                    "https://api.abuseipdb.com/api/v2/check",
                    headers={"Key": abuseipdb_key, "Accept": "application/json"},
                    params={"ipAddress": ip, "maxAgeInDays": 90},
                    timeout=timeout,
                )
                if r.status_code == 200:
                    data = r.json().get("data", {})
                    score = data.get("abuseConfidenceScore", 0)
                    reports = data.get("totalReports", 0)
                    raw.append(f"AbuseIPDB: score={score}, reports={reports}")
                    if score > 0:
                        findings.append({
                            "type": "threat_intel",
                            "detail": f"IP {ip} reported on AbuseIPDB with confidence score {score}% ({reports} reports)",
                            "severity": "critical" if score > 75 else ("high" if score > 25 else "medium"),
                            "source": "AbuseIPDB",
                            "ip": ip,
                            "abuse_score": score,
                        })
            except Exception as e:
                raw.append(f"AbuseIPDB error: {e}")

        # VirusTotal domain lookup
        if vt_key:
            try:
                r = requests.get(
                    f"https://www.virustotal.com/api/v3/domains/{self.target}",
                    headers={"x-apikey": vt_key},
                    timeout=timeout,
                )
                if r.status_code == 200:
                    stats = r.json().get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
                    malicious = stats.get("malicious", 0)
                    suspicious = stats.get("suspicious", 0)
                    raw.append(f"VirusTotal: malicious={malicious}, suspicious={suspicious}")
                    if malicious > 0 or suspicious > 0:
                        findings.append({
                            "type": "threat_intel",
                            "detail": f"Domain flagged by VirusTotal: {malicious} malicious, {suspicious} suspicious engines",
                            "severity": "critical" if malicious > 3 else "high",
                            "source": "VirusTotal",
                            "malicious_engines": malicious,
                            "suspicious_engines": suspicious,
                        })
            except Exception as e:
                raw.append(f"VirusTotal error: {e}")

        # Shodan host lookup
        if shodan_key and ip:
            try:
                r = requests.get(
                    f"https://api.shodan.io/shodan/host/{ip}?key={shodan_key}",
                    timeout=timeout,
                )
                if r.status_code == 200:
                    data = r.json()
                    ports = data.get("ports", [])
                    vulns = data.get("vulns", [])
                    raw.append(f"Shodan: ports={ports[:10]}, vulns={list(vulns)[:5]}")
                    if ports:
                        findings.append({
                            "type": "threat_intel",
                            "detail": f"Shodan: {len(ports)} open ports visible — {', '.join(str(p) for p in ports[:10])}",
                            "severity": "info",
                            "source": "Shodan",
                            "open_ports": ports,
                        })
                    for vuln in list(vulns)[:10]:
                        findings.append({
                            "type": "threat_intel",
                            "detail": f"Shodan vulnerability: {vuln}",
                            "severity": "high",
                            "source": "Shodan",
                            "cve": vuln,
                        })
            except Exception as e:
                raw.append(f"Shodan error: {e}")

        # Check threat feeds (no API key needed)
        try:
            # Check Spamhaus DBL (domain)
            import dns.resolver
            dbl_query = f"{self.target}.dbl.spamhaus.org"
            dns.resolver.resolve(dbl_query, "A")
            findings.append({
                "type": "threat_intel",
                "detail": f"Domain {self.target} listed in Spamhaus DBL domain blocklist",
                "severity": "high",
                "source": "Spamhaus DBL",
            })
        except Exception:
            raw.append("Spamhaus DBL: not listed or DNS error")

        if not any(f["type"] == "threat_intel" for f in findings):
            findings.append({"type": "info", "detail": "No threat intelligence alerts found for this target", "severity": "info"})

        return {"findings": findings, "raw_output": "\n".join(raw)}
