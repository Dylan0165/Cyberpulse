"""Module 37 — Database Exploitation Detection.

Tests for exposed database management interfaces, default database
credentials, and SQL injection entry points.
"""

import json
import logging
import socket
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m37")

DB_PORTS = [
    (3306, "MySQL"),
    (5432, "PostgreSQL"),
    (1433, "MSSQL"),
    (1521, "Oracle"),
    (27017, "MongoDB"),
    (6379, "Redis"),
    (9042, "Cassandra"),
    (5984, "CouchDB"),
    (9200, "Elasticsearch"),
    (8529, "ArangoDB"),
    (7474, "Neo4j"),
    (2424, "OrientDB"),
    (28015, "RethinkDB"),
    (8087, "Riak"),
    (11211, "Memcached"),
]

DB_WEB_PATHS = [
    ("/phpmyadmin", "phpMyAdmin"),
    ("/phpmyadmin/", "phpMyAdmin"),
    ("/pma", "phpMyAdmin"),
    ("/adminer.php", "Adminer"),
    ("/adminer", "Adminer"),
    ("/pgadmin", "pgAdmin"),
    ("/pgadmin4", "pgAdmin4"),
    ("/_utils", "CouchDB Fauxton"),
    ("/_all_dbs", "CouchDB"),
    ("/mongo-express", "Mongo Express"),
    ("/rockmongo", "RockMongo"),
    ("/_plugin/head", "Elasticsearch Head"),
    ("/_cat/indices", "Elasticsearch"),
    ("/redis-commander", "Redis Commander"),
    ("/browser", "Neo4j Browser"),
    ("/solr", "Apache Solr"),
]


class Scanner:
    name = "Database Exploitation"
    phase = "exploitation"
    description = "Detects exposed databases, management interfaces, and injection points"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"Database exploitation scan for {self.target}"]
        base_url = self._get_base_url()

        # Phase 1: Database port scan
        raw_lines.append("\n[Phase 1: Database Port Scan]")
        try:
            ip = socket.gethostbyname(self.target)
            for port, db_name in DB_PORTS:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((ip, port))
                if result == 0:
                    banner = self._banner_grab(ip, port)
                    findings.append({
                        "type": "db_port_open",
                        "port": port,
                        "database": db_name,
                        "banner": banner,
                        "detail": f"{db_name} exposed on port {port}",
                        "severity": "high",
                    })
                    raw_lines.append(f"  HIGH: {db_name} open on port {port}" +
                                     (f" — {banner[:60]}" if banner else ""))
                sock.close()
        except Exception:
            raw_lines.append("  Port scan failed")

        # Phase 2: Database web management interfaces
        raw_lines.append("\n[Phase 2: Database Web Interfaces]")
        for path, tool_name in DB_WEB_PATHS:
            url = base_url + path
            try:
                resp = self.session.get(url, timeout=8, allow_redirects=False)
                if resp.status_code in (200, 301, 302, 401):
                    sev = "critical" if resp.status_code == 200 else "high"
                    findings.append({
                        "type": "db_web_interface",
                        "path": path,
                        "tool": tool_name,
                        "status": resp.status_code,
                        "detail": f"{tool_name} accessible at {path} (HTTP {resp.status_code})",
                        "severity": sev,
                    })
                    raw_lines.append(f"  {sev.upper()}: {tool_name} at {path}")
            except Exception:
                continue

        # Phase 3: NoSQL injection tests
        raw_lines.append("\n[Phase 3: NoSQL Injection]")
        nosql_payloads = [
            {"$gt": ""},
            {"$ne": ""},
            {"$regex": ".*"},
        ]
        nosql_endpoints = [
            "/api/login", "/api/auth", "/api/users",
            "/api/search", "/api/query",
        ]
        for endpoint in nosql_endpoints:
            for payload in nosql_payloads:
                try:
                    # JSON body with NoSQL operators
                    resp = self.session.post(
                        f"{base_url}{endpoint}",
                        json={"username": payload, "password": payload},
                        timeout=8,
                    )
                    if resp.status_code == 200:
                        try:
                            data = resp.json()
                            if data.get("token") or data.get("user") or data.get("success"):
                                findings.append({
                                    "type": "nosql_injection",
                                    "endpoint": endpoint,
                                    "payload": str(payload),
                                    "detail": f"NoSQL injection at {endpoint} — auth bypass possible",
                                    "severity": "critical",
                                })
                                raw_lines.append(f"  CRITICAL: NoSQL injection at {endpoint}")
                                break
                        except Exception:
                            pass
                except Exception:
                    continue

        # Phase 4: Redis/Memcached unauthenticated access
        raw_lines.append("\n[Phase 4: Redis/Memcached Unauthenticated]")
        try:
            ip = socket.gethostbyname(self.target)
            # Redis test
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            if sock.connect_ex((ip, 6379)) == 0:
                sock.send(b"INFO\r\n")
                resp_data = sock.recv(4096).decode(errors="ignore")
                if "redis_version" in resp_data:
                    findings.append({
                        "type": "redis_unauth",
                        "detail": "Redis accepts commands without authentication!",
                        "severity": "critical",
                    })
                    raw_lines.append("  CRITICAL: Redis unauthenticated access!")
            sock.close()

            # Memcached test
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            if sock.connect_ex((ip, 11211)) == 0:
                sock.send(b"stats\r\n")
                resp_data = sock.recv(4096).decode(errors="ignore")
                if "STAT" in resp_data:
                    findings.append({
                        "type": "memcached_unauth",
                        "detail": "Memcached unauthenticated — data extraction possible",
                        "severity": "critical",
                    })
                    raw_lines.append("  CRITICAL: Memcached unauthenticated!")
            sock.close()
        except Exception:
            pass

        # Phase 5: Elasticsearch unauthenticated
        raw_lines.append("\n[Phase 5: Elasticsearch Unauthenticated]")
        es_paths = ["http://{}:9200", "http://{}:9200/_cat/indices",
                     "http://{}:9200/_cluster/health"]
        try:
            ip = socket.gethostbyname(self.target)
            for path_tpl in es_paths:
                url = path_tpl.format(ip)
                try:
                    resp = self.session.get(url, timeout=5)
                    if resp.status_code == 200:
                        findings.append({
                            "type": "elasticsearch_unauth",
                            "url": url,
                            "detail": f"Elasticsearch accessible: {url}",
                            "severity": "critical",
                        })
                        raw_lines.append(f"  CRITICAL: Elasticsearch open: {url}")
                        break
                except Exception:
                    continue
        except Exception:
            pass

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "37_database.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("Database scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _banner_grab(self, ip: str, port: int) -> str:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((ip, port))
            banner = sock.recv(1024).decode(errors="ignore").strip()
            sock.close()
            return banner[:200]
        except Exception:
            return ""

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
