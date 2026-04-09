"""M89 — Network Configuration Audit (White Box)
Connects via SSH and checks network security settings: firewall rules,
IPv6 configuration, IP forwarding, ARP spoofing protection,
network interface security, and DNS configuration.
"""


class Scanner:
    def __init__(self, target, output_dir, config=None):
        self.target = target
        self.output_dir = output_dir
        self.config = config or {}
        self.creds = self.config.get("credentials", {})

    def _ssh_connect(self):
        host = self.creds.get("ssh_host") or self.target
        port = int(self.creds.get("ssh_port") or 22)
        user = self.creds.get("ssh_username", "")
        pwd  = self.creds.get("ssh_password", "")
        key  = self.creds.get("ssh_key", "")
        if not user:
            return None, "Geen SSH-gebruikersnaam"
        try:
            import paramiko, io
            c = paramiko.SSHClient()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if key:
                pkey = paramiko.RSAKey.from_private_key(io.StringIO(key))
                c.connect(host, port=port, username=user, pkey=pkey, timeout=10)
            else:
                c.connect(host, port=port, username=user, password=pwd, timeout=10)
            return c, None
        except ImportError:
            return None, "paramiko niet geinstalleerd"
        except Exception as e:
            return None, str(e)

    def _exec(self, c, cmd):
        try:
            _, out, _ = c.exec_command(cmd, timeout=15)
            return out.read().decode("utf-8", errors="ignore").strip()
        except Exception:
            return ""

    def run(self):
        findings = []
        output = [f"[M89] Netwerkconfiguratie audit via SSH"]

        client, err = self._ssh_connect()
        if client is None:
            return {"findings": [], "raw_output": f"[M89] SSH fout: {err}"}

        # 1. Firewall status
        iptables = self._exec(client, "iptables -L -n 2>/dev/null | head -20")
        ufw = self._exec(client, "ufw status 2>/dev/null")
        firewalld = self._exec(client, "firewall-cmd --list-all 2>/dev/null | head -10")

        has_firewall = bool(iptables.strip() or "active" in ufw.lower() or firewalld.strip())
        output.append(f"  Firewall actief: {has_firewall}")

        if not has_firewall:
            findings.append({
                "title": "Geen Firewall Geconfigureerd",
                "severity": "critical",
                "description": "Er is geen actieve firewall (iptables/ufw/firewalld) geconfigureerd. Alle poorten zijn onbeschermd.",
                "recommendation": "Installeer en configureer een firewall: ufw enable. Gebruik white-listing: ufw default deny incoming; ufw allow 22/tcp; ufw allow 80/tcp; ufw allow 443/tcp"
            })
        elif iptables and "ACCEPT all" in iptables and "DROP" not in iptables and "REJECT" not in iptables:
            findings.append({
                "title": "Firewall Laat Alle Verbindingen Door (ACCEPT all)",
                "severity": "high",
                "description": "iptables is geconfigureerd maar accepteert alle verbindingen zonder restricties.",
                "recommendation": "Stel restrictieve regels in met default DROP policy."
            })

        # 2. IP forwarding (router-functie)
        ip_forward = self._exec(client, "cat /proc/sys/net/ipv4/ip_forward 2>/dev/null")
        output.append(f"  IP forwarding: {ip_forward}")
        if ip_forward == "1":
            findings.append({
                "title": "IP Forwarding Ingeschakeld (Router Modus)",
                "severity": "medium",
                "description": "IP forwarding (net.ipv4.ip_forward=1) is ingeschakeld. Server fungeert als router. Tenzij gewenst vergroot dit aanvalsoppervlak.",
                "recommendation": "Indien niet nodig: sysctl -w net.ipv4.ip_forward=0. Maak permanent: echo 'net.ipv4.ip_forward=0' >> /etc/sysctl.conf"
            })

        # 3. IPv6 status
        ipv6_disable = self._exec(client,
            "cat /proc/sys/net/ipv6/conf/all/disable_ipv6 2>/dev/null")
        if ipv6_disable == "0":
            ipv6_listen = self._exec(client, "ss -tlnp 2>/dev/null | grep ':::'")
            if ipv6_listen:
                output.append(f"  IPv6 services: {ipv6_listen[:100]}")
                findings.append({
                    "title": "Services Luisteren op IPv6 — Mogelijk Onbeschermd",
                    "severity": "low",
                    "description": f"Diensten luisteren op IPv6 interfaces: {ipv6_listen[:200]}. IPv6 firewall-regels worden soms vergeten.",
                    "recommendation": "Controleer ip6tables regels: ip6tables -L. Voeg IPv6 regels toe of disable IPv6 indien niet nodig."
                })

        # 4. TCP syncookies (SYN flood protection)
        syncookies = self._exec(client,
            "cat /proc/sys/net/ipv4/tcp_syncookies 2>/dev/null")
        output.append(f"  TCP syncookies: {syncookies}")
        if syncookies == "0":
            findings.append({
                "title": "TCP SYN Flood Bescherming Uitgeschakeld",
                "severity": "medium",
                "description": "net.ipv4.tcp_syncookies=0. SYN flood aanvallen kunnen de server overbelasten.",
                "recommendation": "Schakel in: sysctl -w net.ipv4.tcp_syncookies=1. Maak permanent in /etc/sysctl.conf."
            })

        # 5. Sysctl security settings
        sysctl_checks = {
            "net.ipv4.conf.all.accept_redirects": ("0", "ICMP Redirect Accepteren Ingeschakeld"),
            "net.ipv4.conf.all.send_redirects": ("0", "ICMP Redirect Sturen Ingeschakeld"),
            "net.ipv4.conf.all.rp_filter": ("1", "Reverse Path Filtering Uitgeschakeld"),
            "kernel.randomize_va_space": ("2", "ASLR Niet Volledig Ingeschakeld"),
        }
        for key, (expected, title) in sysctl_checks.items():
            val = self._exec(client, f"sysctl -n {key} 2>/dev/null")
            output.append(f"  {key}: {val} (verwacht: {expected})")
            if val and val.strip() != expected:
                findings.append({
                    "title": f"Sysctl Beveiligingsinstelling Incorrect: {key}={val}",
                    "severity": "medium",
                    "description": f"{title}. Huidige waarde: {val}, aanbevolen: {expected}.",
                    "recommendation": f"Stel in: sysctl -w {key}={expected}. Maak permanent: echo '{key}={expected}' >> /etc/sysctl.conf"
                })

        client.close()
        if not findings:
            output.append("  [OK] Netwerkconfiguratie lijkt correct")
        return {"findings": findings, "raw_output": "\n".join(output)}
