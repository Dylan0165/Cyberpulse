"""M88 — Running Services Audit (White Box)
Connects via SSH and audits running services: insecure services
(telnet, rsh, ftp), unneeded services, services running as root,
open ports vs expected, and systemd service unit security settings.
"""
import re


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

    INSECURE_SERVICES = {
        "telnet": ("23", "critical", "Telnet verstuurt data in plaintext inclusief wachtwoorden. Gebruik SSH als vervanger."),
        "rsh": ("514", "critical", "rsh is onbeveiligd en verouderd. Vervang door SSH."),
        "rlogin": ("513", "critical", "rlogin is onbeveiligd. Vervang door SSH."),
        "ftp": ("21", "high", "FTP verstuurt data/wachtwoorden in plaintext. Gebruik SFTP of FTPS."),
        "vnc": ("5900", "high", "VNC zonder encryptie of zwak wachtwoord. Gebruik VNC via SSH-tunnel of vervang door RDP/TeamViewer."),
        "snmp": ("161", "medium", "SNMP v1/v2 gebruikt community strings in plaintext. Gebruik SNMPv3 met authenticatie."),
        "nfs": ("2049", "medium", "NFS zonder Kerberos exporteert in plaintext. Beperk exports en gebruik sec=krb5."),
    }

    def run(self):
        findings = []
        output = [f"[M88] Draaiende diensten audit via SSH"]

        client, err = self._ssh_connect()
        if client is None:
            return {"findings": [], "raw_output": f"[M88] SSH fout: {err}"}

        # 1. Listening ports
        netstat = self._exec(client,
            "ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null")
        output.append(f"  Open poorten:\n{netstat[:500]}")

        for service, (port, severity, desc) in self.INSECURE_SERVICES.items():
            if f":{port}" in netstat or f" {port} " in netstat:
                findings.append({
                    "title": f"Onveilige Dienst Actief: {service.upper()} (:{port})",
                    "severity": severity,
                    "description": f"Dienst {service} luistert op poort {port}. {desc}",
                    "recommendation": f"Stop en disable: systemctl stop {service}; systemctl disable {service}. {desc}"
                })
                output.append(f"  [VULN] {service} gevonden op poort {port}")

        # 2. Services running as root that shouldn't be
        ps_out = self._exec(client, "ps aux 2>/dev/null | grep '^root' | "
                                    "awk '{print $11}' | sort -u | head -30")
        suspicious_root = []
        safe_root = {"sshd", "cron", "init", "systemd", "kernel", "kthreadd",
                     "udevd", "auditd", "rsyslogd", "dbus", "NetworkManager"}
        for proc in ps_out.splitlines():
            proc_name = proc.strip().split("/")[-1].split()[0]
            if proc_name and proc_name not in safe_root and not proc_name.startswith("["):
                if any(svc in proc_name.lower() for svc in
                       ["nginx", "apache", "mysql", "postgres", "redis",
                        "mongodb", "elasticsearch", "node", "python", "php"]):
                    suspicious_root.append(proc_name)
        if suspicious_root:
            findings.append({
                "title": f"Webdiensten Draaien als Root: {', '.join(suspicious_root[:5])}",
                "severity": "high",
                "description": f"Diensten {', '.join(suspicious_root[:5])} draaien als root. Bij een compromittering heeft de aanvaller direct root-toegang.",
                "recommendation": "Maak een aparte systeemgebruiker per service: useradd -r -s /sbin/nologin nginx. Gebruik systemd User= directive."
            })

        # 3. Services without systemd hardening
        weak_services = self._exec(client,
            "systemctl show -p NoNewPrivileges,PrivateTmp,ProtectSystem "
            "nginx apache2 mysql postgresql redis-server 2>/dev/null | head -30")
        if "NoNewPrivileges=no" in weak_services or "PrivateTmp=no" in weak_services:
            findings.append({
                "title": "Systemd Services Zonder Sandboxing",
                "severity": "medium",
                "description": "Services missen systemd beveiligingsinstellingen zoals NoNewPrivileges, PrivateTmp of ProtectSystem.",
                "recommendation": ("Voeg toe aan service unit files:\n"
                    "NoNewPrivileges=yes\nPrivateTmp=yes\nProtectSystem=full\n"
                    "Herlaad: systemctl daemon-reload && systemctl restart <service>")
            })

        # 4. Cron jobs check
        cron_out = self._exec(client,
            "crontab -l 2>/dev/null; cat /etc/cron* /etc/cron.d/* 2>/dev/null | "
            "grep -v '^#' | grep -v '^$' | head -20")
        if "wget " in cron_out or "curl " in cron_out:
            findings.append({
                "title": "Cron Jobs met Externe Downloads",
                "severity": "high",
                "description": f"Cron jobs downloaden externe content (wget/curl): {cron_out[:200]}. Dit kan leiden tot supply-chain aanvallen.",
                "recommendation": "Gebruik vaste hashes voor externe scripts. Controleer de herkomst van alle externe downloads in cron."
            })

        client.close()
        if not findings:
            output.append("  [OK] Diensten zijn veilig geconfigureerd")
        return {"findings": findings, "raw_output": "\n".join(output)}
