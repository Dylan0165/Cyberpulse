"""M81 — SSH System Audit / Lynis (White Box)
Connects via SSH and runs a comprehensive system security audit:
sshd_config, sudo rules, SUID binaries, world-writable files,
kernel version, open ports, and optionally Lynis if installed.
"""
import re


class Scanner:
    def __init__(self, target, output_dir, config=None):
        self.target = target
        self.output_dir = output_dir
        self.config = config or {}
        self.creds = self.config.get("credentials", {})

    def _ssh_connect(self):
        ssh_host = self.creds.get("ssh_host") or self.target
        ssh_port = int(self.creds.get("ssh_port") or 22)
        ssh_user = self.creds.get("ssh_username", "")
        ssh_pass = self.creds.get("ssh_password", "")
        ssh_key  = self.creds.get("ssh_key", "")
        if not ssh_user:
            return None, "Geen SSH-gebruikersnaam opgegeven"
        try:
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if ssh_key:
                import io
                pkey = paramiko.RSAKey.from_private_key(io.StringIO(ssh_key))
                client.connect(ssh_host, port=ssh_port, username=ssh_user,
                               pkey=pkey, timeout=10)
            else:
                client.connect(ssh_host, port=ssh_port, username=ssh_user,
                               password=ssh_pass, timeout=10)
            return client, None
        except ImportError:
            return None, "paramiko niet geinstalleerd (pip install paramiko)"
        except Exception as e:
            return None, str(e)

    def _exec(self, client, cmd):
        try:
            _, stdout, stderr = client.exec_command(cmd, timeout=15)
            out = stdout.read().decode("utf-8", errors="ignore")
            err = stderr.read().decode("utf-8", errors="ignore")
            return out.strip()
        except Exception:
            return ""

    def run(self):
        findings = []
        output = []
        output.append(f"[M81] SSH systeemaudit: {self.creds.get('ssh_host', self.target)}")

        client, err = self._ssh_connect()
        if client is None:
            return {"findings": [], "raw_output": f"[M81] SSH verbinding mislukt: {err}"}

        output.append("  SSH verbinding geslaagd")

        # 1. sshd_config audit
        sshd = self._exec(client, "cat /etc/ssh/sshd_config 2>/dev/null")
        if sshd:
            if re.search(r"PermitRootLogin\s+yes", sshd, re.I):
                findings.append({
                    "title": "SSH: Root Login Toegestaan",
                    "severity": "high",
                    "description": "PermitRootLogin is ingesteld op 'yes' in sshd_config. Root SSH-toegang vergroot het risico bij brute-force aanvallen.",
                    "recommendation": "Stel in: PermitRootLogin no. Gebruik sudo voor verhoogde rechten."
                })
            if re.search(r"PasswordAuthentication\s+yes", sshd, re.I):
                findings.append({
                    "title": "SSH: Wachtwoordauthenticatie Ingeschakeld",
                    "severity": "medium",
                    "description": "SSH staat wachtwoord-authenticatie toe. Dit maakt brute-force aanvallen mogelijk.",
                    "recommendation": "Schakel over op SSH-sleutels. Stel in: PasswordAuthentication no. Gebruik fail2ban voor brute-force bescherming."
                })
            if not re.search(r"Protocol\s+2", sshd):
                findings.append({
                    "title": "SSH: Protocol Versie Niet Expliciet Beperkt tot v2",
                    "severity": "low",
                    "description": "SSHv1 is verouderd en heeft bekende kwetsbaarheden.",
                    "recommendation": "Voeg toe aan sshd_config: Protocol 2"
                })
        output.append(f"  sshd_config: {len(sshd.splitlines())} regels")

        # 2. Kernel version
        kernel = self._exec(client, "uname -r")
        output.append(f"  Kernel: {kernel}")
        if kernel:
            major = re.search(r"^(\d+)\.(\d+)", kernel)
            if major:
                maj, minor = int(major.group(1)), int(major.group(2))
                if maj < 5 or (maj == 5 and minor < 10):
                    findings.append({
                        "title": f"Verouderde Linux Kernel: {kernel}",
                        "severity": "medium",
                        "description": f"Kernel versie {kernel} is ouder dan 5.10 LTS. Verouderde kernels missen beveiligingspatches.",
                        "recommendation": "Update de kernel: apt upgrade linux-image-generic (Debian/Ubuntu) of yum update kernel (RHEL/CentOS)."
                    })

        # 3. SUID binaries
        suid_out = self._exec(client, "find / -perm -4000 -type f 2>/dev/null | head -30")
        suid_bins = [l.strip() for l in suid_out.splitlines() if l.strip()]
        dangerous_suid = [b for b in suid_bins if any(
            n in b for n in ["nmap", "vim", "nano", "python", "perl", "ruby",
                              "bash", "sh", "find", "awk", "env", "tee", "cp"])]
        output.append(f"  SUID bestanden: {len(suid_bins)} gevonden, {len(dangerous_suid)} gevaarlijk")
        if dangerous_suid:
            findings.append({
                "title": f"Gevaarlijke SUID Binaries: {', '.join(dangerous_suid[:5])}",
                "severity": "critical",
                "description": f"SUID-binaries zoals {', '.join(dangerous_suid[:3])} kunnen via GTFOBins worden gebruikt voor privilege escalation naar root.",
                "recommendation": "Verwijder SUID van niet-essentiële binaries: chmod u-s /pad/naar/binary. Controleer ook via GTFOBins.github.io."
            })

        # 4. World-writable directories
        ww_dirs = self._exec(client, "find / -xdev -type d -perm -0002 2>/dev/null | grep -v /proc | head -20")
        ww_list = [l.strip() for l in ww_dirs.splitlines() if l.strip()
                   and not any(x in l for x in ["/tmp", "/var/tmp", "/dev/shm"])]
        output.append(f"  World-writable dirs: {len(ww_list)} buiten /tmp")
        if ww_list:
            findings.append({
                "title": f"World-Writable Directories: {len(ww_list)} gevonden",
                "severity": "medium",
                "description": f"Directories buiten /tmp met world-write permissies: {', '.join(ww_list[:3])}. Kunnen worden misbruikt voor privilege escalation.",
                "recommendation": "Haal world-write weg: chmod o-w /pad/naar/dir. Gebruik /tmp voor tijdelijke bestanden met sticky bit (chmod +t)."
            })

        # 5. Sudoers check
        sudo_out = self._exec(client, "sudo -l 2>/dev/null")
        if "NOPASSWD" in sudo_out:
            findings.append({
                "title": "Sudo Regels met NOPASSWD Gevonden",
                "severity": "high",
                "description": f"sudo -l toont NOPASSWD regels: {sudo_out[:200]}. Commando's kunnen zonder wachtwoord als root worden uitgevoerd.",
                "recommendation": "Verwijder NOPASSWD uit /etc/sudoers. Gebruik specifieke commandobeperkingen i.p.v. ALL. Audit regelmatig sudo configuratie."
            })

        # 6. Lynis (optional)
        lynis_check = self._exec(client, "which lynis 2>/dev/null")
        if lynis_check:
            output.append("  Lynis aanwezig — snel audit uitvoeren...")
            lynis_out = self._exec(client, "lynis audit system --quick --quiet 2>/dev/null | tail -30")
            warn_count = lynis_out.count("Warning")
            sugg_count = lynis_out.count("Suggestion")
            if warn_count > 0:
                findings.append({
                    "title": f"Lynis Audit: {warn_count} Waarschuwingen, {sugg_count} Suggesties",
                    "severity": "medium",
                    "description": f"Lynis systeemaudit vond {warn_count} waarschuwingen. Uitvoer (laatste regels): {lynis_out[-300:]}",
                    "recommendation": "Voer uit: lynis audit system en corrigeer alle meldingen. Automatiseer maandelijks via cron."
                })
        else:
            output.append("  Lynis niet aanwezig — handmatige checks uitgevoerd")

        client.close()
        output.append(f"  Audit compleet. {len(findings)} bevindingen.")
        return {"findings": findings, "raw_output": "\n".join(output)}
