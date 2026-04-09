"""M83 — Configuration File Audit (White Box)
Connects via SSH and audits application configuration files:
database connection strings, API keys, debug settings,
insecure server configuration, and exposed secrets.
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

    CONFIG_FILES = [
        "/etc/nginx/nginx.conf",
        "/etc/nginx/sites-enabled/*",
        "/etc/apache2/apache2.conf",
        "/etc/apache2/sites-enabled/*",
        "/etc/mysql/mysql.conf.d/mysqld.cnf",
        "/etc/postgresql/*/main/postgresql.conf",
        "/etc/redis/redis.conf",
        "/etc/ssh/sshd_config",
        "/etc/php/*/fpm/php.ini",
        "/etc/php/*/apache2/php.ini",
    ]

    APP_CONFIG_PATTERNS = [
        "**/.env", "**/config.php", "**/wp-config.php",
        "**/settings.py", "**/config.py", "**/database.yml",
        "**/config/database.php", "**/.htaccess",
        "**/application.properties", "**/appsettings.json",
    ]

    def run(self):
        findings = []
        output = [f"[M83] Configuratiebestand audit via SSH"]

        client, err = self._ssh_connect()
        if client is None:
            return {"findings": [], "raw_output": f"[M83] SSH fout: {err}"}

        src = self.creds.get("source_path", "/var/www")
        output.append(f"  Basispad: {src}")

        # 1. Find .env files
        env_files = self._exec(client, f"find {src} /home /opt -name '.env' -not -path '*/.git/*' 2>/dev/null | head -10")
        for ef in env_files.splitlines():
            ef = ef.strip()
            if not ef:
                continue
            content = self._exec(client, f"cat '{ef}' 2>/dev/null | head -30")
            output.append(f"  .env gevonden: {ef}")
            if any(kw in content.upper() for kw in
                   ["PASSWORD", "SECRET", "KEY", "TOKEN", "DATABASE_URL"]):
                findings.append({
                    "title": f".env Bestand met Gevoelige Data: {ef}",
                    "severity": "critical",
                    "description": f"Bestand {ef} bevat gevoelige configuratie:\n{content[:300]}",
                    "recommendation": "Zorg dat .env in .gitignore staat. Gebruik rechten 600. Overweeg een secrets manager. Roteer alle blootgestelde credentials."
                })

        # 2. Check web server configs for security headers
        nginx_conf = self._exec(client, "cat /etc/nginx/nginx.conf 2>/dev/null; "
                                        "cat /etc/nginx/sites-enabled/* 2>/dev/null")
        if nginx_conf:
            output.append("  Nginx config gevonden")
            missing_headers = []
            for header in ["X-Frame-Options", "X-Content-Type-Options",
                           "Strict-Transport-Security", "Content-Security-Policy"]:
                if header not in nginx_conf:
                    missing_headers.append(header)
            if missing_headers:
                findings.append({
                    "title": f"Ontbrekende Beveiligingsheaders in Nginx Config",
                    "severity": "medium",
                    "description": f"Nginx bevat geen headers: {', '.join(missing_headers)}.",
                    "recommendation": ("Voeg toe aan nginx server block:\n"
                        "add_header X-Frame-Options 'SAMEORIGIN';\n"
                        "add_header X-Content-Type-Options 'nosniff';\n"
                        "add_header Strict-Transport-Security 'max-age=31536000; includeSubDomains';\n"
                        "add_header Content-Security-Policy \"default-src 'self'\";")
                })
            # Check for server_tokens off
            if "server_tokens off" not in nginx_conf:
                findings.append({
                    "title": "Nginx: Server Versie Wordt Onthuld (server_tokens on)",
                    "severity": "low",
                    "description": "Nginx onthult de serverversie in HTTP-headers. Dit geeft aanvallers info over kwetsbare versies.",
                    "recommendation": "Voeg toe aan nginx.conf http-block: server_tokens off;"
                })

        # 3. PHP configuration
        php_ini = self._exec(client, "grep -h 'expose_php\\|display_errors\\|allow_url_include' "
                                      "/etc/php/*/*/php.ini 2>/dev/null")
        if "expose_php = On" in php_ini or "expose_php=On" in php_ini:
            findings.append({
                "title": "PHP: expose_php Ingeschakeld",
                "severity": "low",
                "description": "expose_php=On stuurt PHP versie-informatie in HTTP responses.",
                "recommendation": "Stel in php.ini: expose_php = Off"
            })
        if "display_errors = On" in php_ini or "display_errors=On" in php_ini:
            findings.append({
                "title": "PHP: display_errors Ingeschakeld",
                "severity": "medium",
                "description": "display_errors=On toont PHP fouten inclusief paden en code aan gebruikers. Nuttig voor aanvallers.",
                "recommendation": "Stel in php.ini: display_errors = Off. Log errors naar bestand: log_errors = On"
            })
        if "allow_url_include = On" in php_ini:
            findings.append({
                "title": "PHP: allow_url_include Ingeschakeld — Remote File Inclusion Mogelijk",
                "severity": "critical",
                "description": "allow_url_include=On maakt Remote File Inclusion (RFI) aanvallen mogelijk via include($remote_url).",
                "recommendation": "Stel in php.ini: allow_url_include = Off. Schakel ook allow_url_fopen uit indien niet nodig."
            })

        client.close()
        output.append(f"  Audit compleet: {len(findings)} bevindingen")
        return {"findings": findings, "raw_output": "\n".join(output)}
