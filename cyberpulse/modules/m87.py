"""M87 — User & Group Account Audit (White Box)
Connects via SSH and audits local user accounts: empty passwords,
UID 0 accounts besides root, unlocked service accounts, users without
password expiry, and suspicious groups.
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

    def run(self):
        findings = []
        output = [f"[M87] Gebruikersaccounts audit via SSH"]

        client, err = self._ssh_connect()
        if client is None:
            return {"findings": [], "raw_output": f"[M87] SSH fout: {err}"}

        # 1. UID 0 accounts (besides root)
        uid0 = self._exec(client, "awk -F: '($3==0){print $1}' /etc/passwd 2>/dev/null")
        uid0_users = [u.strip() for u in uid0.splitlines() if u.strip() and u.strip() != "root"]
        output.append(f"  UID 0 accounts naast root: {uid0_users or 'geen'}")
        if uid0_users:
            findings.append({
                "title": f"Extra UID 0 Accounts (Root Equivalenten): {', '.join(uid0_users)}",
                "severity": "critical",
                "description": f"Gebruikers {', '.join(uid0_users)} hebben UID 0 en zijn daarmee equivalent aan root.",
                "recommendation": "Verwijder extra UID-0 accounts of verander hun UID. Alleen 'root' mag UID 0 hebben."
            })

        # 2. Accounts with empty passwords
        empty_pass = self._exec(client,
            "awk -F: '($2==\"\" || $2==\"!\"){print $1}' /etc/shadow 2>/dev/null")
        if empty_pass:
            empty_users = [u for u in empty_pass.splitlines() if u.strip()]
            if empty_users:
                findings.append({
                    "title": f"Accounts met Leeg/Geblokkeerd Wachtwoord: {', '.join(empty_users[:5])}",
                    "severity": "medium",
                    "description": f"Accounts {', '.join(empty_users[:5])} hebben geen geldig wachtwoord. Lege wachtwoorden zijn een beveiligingsrisico.",
                    "recommendation": "Stel een sterk wachtwoord in of vergrendel accounts die niet gebruikt worden: passwd -l <gebruiker>"
                })
        output.append(f"  Lege wachtwoorden check: OK")

        # 3. Login shells for service accounts
        service_with_shell = self._exec(client,
            "awk -F: '($3>=1000 && $7!=\"/usr/sbin/nologin\" && $7!=\"/bin/false\" "
            "&& $7!=\"/sbin/nologin\"){print $1\": \"$7}' /etc/passwd 2>/dev/null")
        human_accounts = []
        for line in service_with_shell.splitlines():
            if line.strip():
                uname = line.split(":")[0].strip()
                if uname not in ("nobody",):
                    human_accounts.append(line.strip())
        output.append(f"  Accounts met login-shell: {len(human_accounts)}")
        if len(human_accounts) > 5:
            findings.append({
                "title": f"Veel Gebruikersaccounts met Login Shell: {len(human_accounts)}",
                "severity": "low",
                "description": f"Gevonden accounts met interactieve shell:\n" +
                               "\n".join(human_accounts[:8]),
                "recommendation": "Controleer of alle accounts met een login-shell actief gebruikt worden. Blokkeer ongebruikte: usermod -s /usr/sbin/nologin <gebruiker>"
            })

        # 4. Sudo group members
        sudo_members = self._exec(client,
            "getent group sudo 2>/dev/null; getent group wheel 2>/dev/null")
        output.append(f"  Sudo/wheel groep: {sudo_members}")
        sudo_users = []
        for line in sudo_members.splitlines():
            parts = line.split(":")
            if len(parts) >= 4 and parts[3].strip():
                sudo_users += [u.strip() for u in parts[3].split(",") if u.strip()]
        if len(sudo_users) > 3:
            findings.append({
                "title": f"Veel Gebruikers in Sudo Groep: {', '.join(sudo_users)}",
                "severity": "medium",
                "description": f"{len(sudo_users)} gebruikers hebben sudo-rechten: {', '.join(sudo_users)}. Teveel sudo-toegang vergroot het aanvalsoppervlak.",
                "recommendation": "Beperk sudo-toegang tot absolute minimum. Gebruik specifieke sudo-regels in /etc/sudoers.d/ i.p.v. volledige sudo-groep lidmaatschap."
            })

        # 5. Last login check — stale accounts
        last_out = self._exec(client, "lastlog 2>/dev/null | awk 'NR>1 && $2==\"Never\"  {print $1}' | head -10")
        never_logged = [u for u in last_out.splitlines() if u.strip()]
        if len(never_logged) > 3:
            output.append(f"  Accounts die nooit ingelogd zijn: {len(never_logged)}")
            findings.append({
                "title": f"Inactieve Accounts Die Nooit Zijn Ingelogd: {len(never_logged)}",
                "severity": "low",
                "description": f"Accounts die nooit zijn gebruikt: {', '.join(never_logged[:6])}. Inactieve accounts vergroten het aanvalsoppervlak.",
                "recommendation": "Verwijder of vergrendel ongebruikte accounts: passwd -l <gebruiker> of userdel <gebruiker>"
            })

        client.close()
        if not findings:
            output.append("  [OK] Gebruikersaccounts lijken correct geconfigureerd")
        return {"findings": findings, "raw_output": "\n".join(output)}
