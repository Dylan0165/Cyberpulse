"""M86 — File Permissions Audit (White Box)
Connects via SSH and audits dangerous file permissions:
world-readable sensitive files, incorrect SSH key permissions,
config files accessible by non-root, and backup files in webroot.
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
        output = [f"[M86] Bestandspermissies audit via SSH"]

        client, err = self._ssh_connect()
        if client is None:
            return {"findings": [], "raw_output": f"[M86] SSH fout: {err}"}

        src = self.creds.get("source_path", "/var/www")

        # 1. World-readable sensitive config files
        sensitive_patterns = [
            "/etc/shadow", "/etc/gshadow",
            "*/wp-config.php", "*/.env", "*/config.php",
            "*/database.yml", "*/settings.py", "*/.htpasswd"
        ]
        for pattern in sensitive_patterns:
            result = self._exec(client,
                f"find {pattern} /var/www /home /opt -name '{pattern.split('/')[-1]}' "
                f"-perm -o+r 2>/dev/null | head -5")
            for f in result.splitlines():
                if f.strip():
                    output.append(f"  World-readable: {f.strip()}")
                    findings.append({
                        "title": f"Gevoelig Bestand World-Readable: {f.strip()}",
                        "severity": "critical",
                        "description": f"Bestand {f.strip()} is leesbaar voor alle systeemgebruikers. Dit kan credentials of configuratie onthullen.",
                        "recommendation": f"Voer uit: chmod 640 {f.strip()} of chmod 600 {f.strip()}. Controleer de eigenaar: chown root:www-data {f.strip()}"
                    })

        # 2. SSH private keys with wrong permissions
        ssh_keys = self._exec(client,
            "find /root /home ~/.ssh -name '*.pem' -o -name 'id_rsa' "
            "-o -name 'id_ed25519' 2>/dev/null | head -10")
        for key_file in ssh_keys.splitlines():
            key_file = key_file.strip()
            if not key_file:
                continue
            perms = self._exec(client, f"stat -c '%a' '{key_file}' 2>/dev/null")
            output.append(f"  SSH key {key_file}: permissies {perms}")
            if perms and perms not in ("600", "400"):
                findings.append({
                    "title": f"SSH Privésleutel met Incorrecte Permissies: {key_file} ({perms})",
                    "severity": "high",
                    "description": f"SSH privésleutel {key_file} heeft permissies {perms}. Andere gebruikers kunnen de sleutel lezen.",
                    "recommendation": f"Voer uit: chmod 600 {key_file}"
                })

        # 3. Backup files in webroot
        backup_files = self._exec(client,
            f"find {src} /var/www -type f \\( "
            "-name '*.bak' -o -name '*.backup' -o -name '*.old' "
            "-o -name '*.orig' -o -name '*.sql' -o -name '*.tar.gz' "
            "-o -name '*.zip' \\) 2>/dev/null | head -15")
        for bf in backup_files.splitlines():
            bf = bf.strip()
            if bf:
                output.append(f"  Backup in webroot: {bf}")
                findings.append({
                    "title": f"Backup/Archief Bestand in Webroot: {bf}",
                    "severity": "high",
                    "description": f"Bestand {bf} in de webroot is mogelijk publiek downloadbaar. Backup-bestanden bevatten vaak broncode, database dumps, of configuratie.",
                    "recommendation": f"Verplaats of verwijder: mv {bf} /tmp/ of rm {bf}. Bewaar backups buiten de webroot."
                })

        # 4. Writable config files by web server user
        web_writable = self._exec(client,
            "find /var/www /etc/nginx /etc/apache2 -user www-data -perm -o+w "
            "-type f 2>/dev/null | head -10")
        for wf in web_writable.splitlines():
            wf = wf.strip()
            if wf:
                findings.append({
                    "title": f"Configuratiebestand Schrijfbaar door Web Server: {wf}",
                    "severity": "medium",
                    "description": f"Bestand {wf} is schrijfbaar door de webserver-user (www-data). Bij een RCE kan de aanvaller configuraties aanpassen.",
                    "recommendation": f"Voer uit: chmod 644 {wf}; chown root:www-data {wf}"
                })

        client.close()
        output.append(f"  Audit compleet: {len(findings)} bevindingen")
        if not findings:
            output.append("  [OK] Bestandspermissies lijken correct geconfigureerd")
        return {"findings": findings, "raw_output": "\n".join(output)}
