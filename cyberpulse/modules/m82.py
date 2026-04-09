"""M82 — Source Code SAST Scan (White Box)
Connects via SSH, navigates to source_path, and performs static analysis:
hardcoded secrets, SQL injection patterns, dangerous function calls,
insecure deserialization, and secrets in config files.
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
            _, out, _ = c.exec_command(cmd, timeout=20)
            return out.read().decode("utf-8", errors="ignore").strip()
        except Exception:
            return ""

    def run(self):
        findings = []
        output = []
        src = self.creds.get("source_path", "")

        output.append(f"[M82] SAST broncode analyse via SSH")

        client, err = self._ssh_connect()
        if client is None:
            return {"findings": [], "raw_output": f"[M82] SSH fout: {err}"}

        if not src:
            # Try to auto-detect
            src = self._exec(client, "find /var/www /opt /home -maxdepth 3 "
                                     "-name '*.py' -o -name '*.php' -o -name '*.js' "
                                     "2>/dev/null | head -1")
            src = "/".join(src.split("/")[:-1]) if src else "/var/www/html"
        output.append(f"  Bronpad: {src}")

        SAST_RULES = [
            # (grep pattern, title, severity, description, recommendation)
            (r"password\s*=\s*['\"][^'\"]{4,}['\"]",
             "Hardcoded Wachtwoord in Broncode", "critical",
             "Hardcoded wachtwoord gevonden in broncode. Elke developer met codebase toegang heeft dit wachtwoord.",
             "Gebruik omgevingsvariabelen (os.environ) of een secrets manager (Vault, AWS Secrets Manager)."),
            (r"(api_key|apikey|api_secret|access_token)\s*=\s*['\"][A-Za-z0-9+/]{16,}['\"]",
             "Hardcoded API Sleutel", "critical",
             "API-sleutel direct in de broncode gevonden.",
             "Gebruik .env bestanden of secrets managers. Voeg .env toe aan .gitignore."),
            (r"execute\(.*%.*%|execute\(.*\+|cursor\.execute\([^,)]+format",
             "SQL Injectie Patroon (String Concatenatie)", "critical",
             "SQL query wordt samengesteld via string formatting of concatenatie. Dit is kwetsbaar voor SQL injectie.",
             "Gebruik altijd prepared statements / parameterized queries. Nooit gebruikersinput in SQL string samenvoegen."),
            (r"eval\(.*request\.|eval\(.*_GET|eval\(.*_POST|eval\(.*input",
             "Gevaarlijk eval() met Gebruikersinput", "critical",
             "eval() wordt aangeroepen met (potentiële) gebruikersinput. Dit kan leiden tot Remote Code Execution.",
             "Verwijder alle eval() aanroepen met externe data. Gebruik JSON.parse() of ast.literal_eval() als alternatief."),
            (r"subprocess\.(call|run|Popen)\(.*shell=True",
             "Shell=True in subprocess — Command Injection Risico", "high",
             "subprocess wordt aangeroepen met shell=True. Indien gebruikersinput in het commando verwerkt wordt, leidt dit tot command injection.",
             "Gebruik shell=False en geef argumenten als lijst. Valideer en escaped alle externe input."),
            (r"pickle\.loads?\(",
             "Onveilige Deserialisatie (pickle)", "high",
             "pickle.load(s) deserialiseert data. Deserialisatie van onbetrouwbare data kan tot RCE leiden.",
             "Gebruik nooit pickle voor data van externe bronnen. Gebruik JSON of XML als alternatief."),
            (r"md5|sha1\(",
             "Zwakke Hashing Algoritmen (MD5/SHA1)", "medium",
             "MD5 en SHA1 zijn cryptografisch gebroken en niet geschikt voor wachtwoord-hashing of integriteitschecks.",
             "Gebruik SHA-256 of hoger voor hashes. Gebruik bcrypt/argon2 voor wachtwoorden."),
            (r"verify\s*=\s*False",
             "SSL Verificatie Uitgeschakeld", "high",
             "SSL certificaat verificatie is uitgeschakeld (verify=False). Man-in-the-middle aanvallen worden hierdoor mogelijk.",
             "Verwijder verify=False. Voeg het juiste CA-certificaat toe als self-signed certs nodig zijn."),
            (r"debug\s*=\s*True|DEBUG\s*=\s*True",
             "Debug Modus Ingeschakeld in Productie", "medium",
             "Applicatie is ingesteld op debug-modus. Dit kan stack traces en interne informatie onthullen.",
             "Zet DEBUG=False in productie. Gebruik omgevingsvariabelen voor debug-instellingen."),
        ]

        for pattern, title, severity, desc, rec in SAST_RULES:
            grep_cmd = (f"grep -rn --include='*.py' --include='*.php' "
                        f"--include='*.js' --include='*.ts' --include='*.rb' "
                        f"-E '{pattern}' {src} 2>/dev/null | head -10")
            result = self._exec(client, grep_cmd)
            lines = [l for l in result.splitlines() if l.strip()]
            output.append(f"  [{severity.upper()}] {title}: {len(lines)} treffer(s)")
            if lines:
                sample = "\n".join(lines[:3])
                findings.append({
                    "title": title,
                    "severity": severity,
                    "description": f"{desc}\n\nVoorbeelden:\n{sample}",
                    "recommendation": rec
                })

        # Count total source files
        file_count = self._exec(client,
            f"find {src} -type f \\( -name '*.py' -o -name '*.php' -o -name '*.js' \\) "
            "2>/dev/null | wc -l")
        output.append(f"  Bronbestanden geanalyseerd: {file_count.strip()}")

        client.close()
        return {"findings": findings, "raw_output": "\n".join(output)}
