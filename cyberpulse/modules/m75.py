"""M75 — Database Connectivity Test (Gray Box)
Tests provided database credentials and checks if the DB is accessible
from external networks (security misconfiguration).
"""
import socket


class Scanner:
    def __init__(self, target, output_dir, config=None):
        self.target = target
        self.output_dir = output_dir
        self.config = config or {}
        self.creds = self.config.get("credentials", {})

    def _tcp_connect(self, host, port, timeout=5):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            r = s.connect_ex((host, port))
            s.close()
            return r == 0
        except Exception:
            return False

    def _try_mysql(self, host, port, user, pwd, db):
        try:
            import mysql.connector
            conn = mysql.connector.connect(host=host, port=port,
                user=user, password=pwd, database=db, connect_timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            conn.close()
            return True, str(version)
        except ImportError:
            return None, "mysql-connector-python niet geinstalleerd"
        except Exception as e:
            return False, str(e)

    def _try_postgres(self, host, port, user, pwd, db):
        try:
            import psycopg2
            conn = psycopg2.connect(host=host, port=port,
                user=user, password=pwd, dbname=db, connect_timeout=5)
            cur = conn.cursor()
            cur.execute("SELECT version()")
            version = cur.fetchone()
            conn.close()
            return True, str(version)
        except ImportError:
            return None, "psycopg2 niet geinstalleerd"
        except Exception as e:
            return False, str(e)

    def run(self):
        findings = []
        output = []

        db_host = self.creds.get("db_host", "") or self.target
        db_port = int(self.creds.get("db_port") or 3306)
        db_user = self.creds.get("db_username", "")
        db_pass = self.creds.get("db_password", "")
        db_name = self.creds.get("db_name", "")

        output.append(f"[M75] Database verbindingstest: {db_host}:{db_port}")

        # Common DB ports
        db_ports = {3306: "MySQL", 5432: "PostgreSQL", 27017: "MongoDB",
                    1433: "MSSQL", 5984: "CouchDB", 6379: "Redis",
                    9200: "Elasticsearch", 5000: "DB2"}

        for port, name in db_ports.items():
            if self._tcp_connect(db_host, port):
                output.append(f"  [OPEN] {name} op poort {port}")
                if port not in (db_port,):
                    findings.append({
                        "title": f"Database Poort Extern Bereikbaar: {name} ({port})",
                        "severity": "high",
                        "description": f"{name} (poort {port}) is extern bereikbaar op {db_host}. Databases horen niet direct toegankelijk te zijn via het internet.",
                        "recommendation": f"Blokkeer poort {port} via firewall. Databases mogen alleen bereikbaar zijn via applicatieservers op hetzelfde netwerk."
                    })
            else:
                output.append(f"  [CLOSED] {name} ({port})")

        # Test actual DB credentials
        if db_user:
            if db_port == 3306:
                ok, msg = self._try_mysql(db_host, db_port, db_user, db_pass, db_name)
            elif db_port == 5432:
                ok, msg = self._try_postgres(db_host, db_port, db_user, db_pass, db_name)
            else:
                ok, msg = None, "Onbekende DB type"

            if ok is True:
                output.append(f"  [AUTH] Login succesvol: {msg}")
                findings.append({
                    "title": "Database Login Geslaagd met Opgegeven Credentials",
                    "severity": "info",
                    "description": f"Succesvol ingelogd op {db_host}:{db_port} als '{db_user}'. DB versie: {msg}",
                    "recommendation": "Verifieer dat deze gebruiker minimale rechten heeft (least privilege). Gebruik een aparte read-only user voor applicaties waar mogelijk."
                })
            elif ok is False:
                output.append(f"  [FAIL] Login gefaald: {msg}")
            else:
                output.append(f"  [INFO] {msg}")

        # Check for common default/weak credentials
        weak_creds = [("root", ""), ("root", "root"), ("admin", "admin"),
                      ("mysql", "mysql"), ("postgres", "postgres")]
        if not db_user:
            for u, p in weak_creds:
                ok, msg = self._try_mysql(db_host, 3306, u, p, "")
                if ok is True:
                    findings.append({
                        "title": f"Database Toegankelijk met Standaard Credentials ({u}/{p or 'leeg'})",
                        "severity": "critical",
                        "description": f"MySQL op {db_host}:3306 accepteert standaard credentials {u}/{p or 'leeg wachtwoord'}.",
                        "recommendation": "Verander direct het database root-wachtwoord. Verwijder anonieme accounts (DROP USER ''@'%'). Beperk root tot localhost."
                    })
                    break

        if not findings:
            output.append("  [OK] Database correct afgeschermd")
        return {"findings": findings, "raw_output": "\n".join(output)}
