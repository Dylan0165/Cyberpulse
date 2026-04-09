"""M85 — Hardcoded Secrets Detection (White Box)
Connects via SSH and scans source code and config files for
hardcoded API keys, tokens, passwords, and private keys using
regex patterns for common secret formats.
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

    # (pattern, name, severity)
    SECRET_PATTERNS = [
        (r"-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----", "RSA/EC Privésleutel", "critical"),
        (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID", "critical"),
        (r'(?i)aws.{0,20}secret.{0,20}[A-Za-z0-9/+=]{40}', "AWS Secret Access Key", "critical"),
        (r"ghp_[A-Za-z0-9]{36}", "GitHub Personal Access Token", "critical"),
        (r"github_pat_[A-Za-z0-9_]{82}", "GitHub PAT (Fine-grained)", "critical"),
        (r"glpat-[A-Za-z0-9\-_]{20}", "GitLab Personal Access Token", "critical"),
        (r"sk-[A-Za-z0-9]{48}", "OpenAI API Key", "critical"),
        (r"AIza[0-9A-Za-z\-_]{35}", "Google API Key", "critical"),
        (r"[0-9]+-[0-9A-Za-z_]{32}\.apps\.googleusercontent\.com", "Google OAuth Client", "high"),
        (r"xox[baprs]-[0-9A-Za-z\-]{10,48}", "Slack Token", "critical"),
        (r"EAACEdEose0cBA[0-9A-Za-z]+", "Facebook Access Token", "critical"),
        (r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"][^'\"\s]{6,}", "Hardcoded Wachtwoord", "critical"),
        (r"(?i)(secret_key|secret|jwt_secret)\s*[=:]\s*['\"][^'\"\s]{8,}", "Hardcoded Secret Key", "critical"),
        (r"(?i)(database_url|db_url)\s*[=:]\s*['\"][^'\"\s]+:[^'\"\s]+@", "Database URL met Credentials", "critical"),
        (r"mongodb://[^:]+:[^@]+@", "MongoDB Connection String met Credentials", "critical"),
        (r"mysql://[^:]+:[^@]+@|postgres://[^:]+:[^@]+@", "SQL DB Connection String", "critical"),
        (r"(?i)(smtp_password|mail_password)\s*[=:]\s*['\"][^'\"\s]{4,}", "SMTP Wachtwoord", "high"),
        (r"(?i)(stripe_secret|stripe_key)\s*[=:]\s*['\"]sk_live_[A-Za-z0-9]+", "Stripe Live Secret Key", "critical"),
        (r"(?i)private.?key\s*[=:]\s*['\"][A-Za-z0-9+/=]{32,}", "Hardcoded Private Key", "high"),
    ]

    def run(self):
        findings = []
        output = [f"[M85] Hardcoded secrets detectie via SSH"]

        client, err = self._ssh_connect()
        if client is None:
            return {"findings": [], "raw_output": f"[M85] SSH fout: {err}"}

        src = self.creds.get("source_path", "/var/www")
        output.append(f"  Scanpad: {src}")

        # File types to search
        file_types = ("*.py", "*.php", "*.js", "*.ts", "*.env", "*.json",
                      "*.yml", "*.yaml", "*.rb", "*.java", "*.conf", "*.ini",
                      "*.properties", "*.xml", "*.sh", "*.bash")
        include_args = " ".join(f"--include='{t}'" for t in file_types)

        for pattern, name, severity in self.SECRET_PATTERNS:
            # Escape single quotes for shell
            safe_pattern = pattern.replace("'", r"'\''")
            grep_cmd = (f"grep -rn {include_args} "
                        f"-E '{safe_pattern}' {src} 2>/dev/null | "
                        "grep -v '.pyc' | grep -v 'test_' | head -5")
            result = self._exec(client, grep_cmd)
            hits = [l for l in result.splitlines() if l.strip()]
            output.append(f"  {name}: {len(hits)} treffer(s)")

            if hits:
                # Redact actual secret values before reporting
                redacted = []
                for h in hits[:3]:
                    # Replace anything that looks like a secret value after = or :
                    clean = re.sub(r'([=:"\']\s*)([A-Za-z0-9+/=\-_]{8,})', r'\1[REDACTED]', h)
                    redacted.append(clean)
                findings.append({
                    "title": f"Hardcoded Secret Gevonden: {name}",
                    "severity": severity,
                    "description": f"{name} gedetecteerd in broncode:\n" + "\n".join(redacted),
                    "recommendation": (
                        f"Verwijder de hardcoded {name} uit de broncode. "
                        "Gebruik omgevingsvariabelen (.env + python-dotenv) of een secrets manager "
                        "(HashiCorp Vault, AWS Secrets Manager, Azure Key Vault). "
                        "Roteer direct alle blootgestelde credentials."
                    )
                })

        # Also check git history for secrets
        git_check = self._exec(client,
            f"cd {src} 2>/dev/null && git log --all --oneline 2>/dev/null | wc -l")
        if git_check and git_check.strip() != "0":
            output.append(f"  Git repository gevonden ({git_check.strip()} commits) — "
                          "gebruik git-secrets of truffleHog voor volledige history scan")

        client.close()
        output.append(f"  Scan compleet: {len(findings)} secrets gevonden")
        return {"findings": findings, "raw_output": "\n".join(output)}
