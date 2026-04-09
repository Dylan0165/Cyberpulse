"""M76 — Internal Network Port Scan (Gray Box)
Scans the provided internal network range for open ports and
services that should not be accessible from corporate networks.
"""
import socket
import concurrent.futures
import ipaddress


class Scanner:
    def __init__(self, target, output_dir, config=None):
        self.target = target
        self.output_dir = output_dir
        self.config = config or {}
        self.creds = self.config.get("credentials", {})

    def _probe(self, host, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            r = s.connect_ex((str(host), port))
            s.close()
            return r == 0
        except Exception:
            return False

    def _banner(self, host, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((str(host), port))
            s.send(b"HEAD / HTTP/1.0\r\n\r\n")
            data = s.recv(256).decode("utf-8", errors="ignore").strip()
            s.close()
            return data[:80]
        except Exception:
            return ""

    SENSITIVE_PORTS = {
        21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
        80: "HTTP", 110: "POP3", 143: "IMAP", 389: "LDAP", 443: "HTTPS",
        445: "SMB", 1433: "MSSQL", 1521: "Oracle DB", 3306: "MySQL",
        3389: "RDP", 5432: "PostgreSQL", 5900: "VNC", 6379: "Redis",
        8080: "HTTP-ALT", 8443: "HTTPS-ALT", 9200: "Elasticsearch",
        27017: "MongoDB", 2375: "Docker API", 2376: "Docker TLS",
        6443: "Kubernetes API", 10250: "Kubelet"
    }

    CRITICAL_PORTS = {23, 5900, 2375, 9200, 27017, 6379, 6443, 10250}

    def run(self):
        findings = []
        output = []
        network_range = self.creds.get("network_range", "")

        if not network_range:
            output.append("[M76] Geen netwerk-range opgegeven — overgeslagen")
            return {"findings": [], "raw_output": "\n".join(output)}

        output.append(f"[M76] Intern netwerk portscan: {network_range}")

        try:
            net = ipaddress.ip_network(network_range, strict=False)
        except ValueError as e:
            return {"findings": [], "raw_output": f"[M76] Ongeldig netwerk: {e}"}

        # Limit scan to /24 or smaller
        hosts = list(net.hosts())[:254]
        open_services = {}

        def scan_host(host):
            host_open = {}
            for port in self.SENSITIVE_PORTS:
                if self._probe(host, port):
                    host_open[port] = self.SENSITIVE_PORTS[port]
            return str(host), host_open

        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
            futures = {ex.submit(scan_host, h): h for h in hosts}
            for f in concurrent.futures.as_completed(futures, timeout=60):
                ip, ports = f.result()
                if ports:
                    open_services[ip] = ports

        for ip, ports in open_services.items():
            port_list = ", ".join(f"{p}/{n}" for p, n in ports.items())
            output.append(f"  {ip}: {port_list}")

            critical = {p: n for p, n in ports.items() if p in self.CRITICAL_PORTS}
            if critical:
                crit_list = ", ".join(f"{n} (:{p})" for p, n in critical.items())
                findings.append({
                    "title": f"Kritieke Diensten Intern Bereikbaar: {ip}",
                    "severity": "critical",
                    "description": f"Host {ip} heeft kritieke diensten open: {crit_list}. Diensten zoals Docker API, Kubernetes, Redis en MongoDB mogen nooit intern onbeveiligd bereikbaar zijn.",
                    "recommendation": "Segmenteer netwerk met VLANs. Voeg authenticatie toe aan alle genoemde diensten. Blokkeer ongeautoriseerde toegang via host-based firewall (iptables/ufw)."
                })
            elif len(ports) >= 5:
                findings.append({
                    "title": f"Host met Veel Open Poorten Intern: {ip}",
                    "severity": "medium",
                    "description": f"Host {ip} heeft {len(ports)} open poorten: {port_list}. Dit vergroot het aanvalsoppervlak.",
                    "recommendation": "Sluit onnodige poorten. Implementeer least-privilege network policy."
                })

        if not open_services:
            output.append("  [OK] Geen gevoelige diensten gevonden op intern netwerk")
        output.append(f"  Totaal: {len(open_services)} hosts met open poorten")
        return {"findings": findings, "raw_output": "\n".join(output)}
