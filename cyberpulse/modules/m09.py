"""Module 09 — Directory and File Enumeration.

Discovers hidden directories, backup files, and sensitive paths using
common wordlists.
"""

import json
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

logger = logging.getLogger("cyberpulse.modules.m09")

# Built-in wordlist of common paths
COMMON_PATHS = [
    # Common directories
    "admin", "administrator", "login", "wp-admin", "wp-login.php",
    "phpmyadmin", "pma", "cpanel", "webmail", "panel",
    "dashboard", "api", "api/v1", "api/v2", "graphql",
    ".git", ".git/HEAD", ".git/config", ".svn", ".svn/entries",
    ".env", ".env.local", ".env.production", ".env.backup",
    ".htaccess", ".htpasswd", "web.config",
    "backup", "backups", "bak", "old", "temp", "tmp",
    "database", "db", "dump", "sql", "mysql",
    "config", "configuration", "conf", "settings",
    "logs", "log", "debug", "trace",
    "upload", "uploads", "files", "media", "images", "assets",
    "cgi-bin", "scripts", "bin",
    "test", "tests", "testing", "demo", "example",
    "doc", "docs", "documentation", "readme", "README.md",
    "sitemap.xml", "robots.txt", "crossdomain.xml", "clientaccesspolicy.xml",
    "server-status", "server-info",
    ".well-known", ".well-known/security.txt",
    "wp-content", "wp-includes", "wp-config.php.bak",
    "elmah.axd", "trace.axd",
    "swagger", "swagger-ui", "swagger.json", "api-docs",
    "graphiql", "playground",
    "actuator", "actuator/health", "actuator/env",
    "info.php", "phpinfo.php", "test.php", "info",
    ".DS_Store", "Thumbs.db", "desktop.ini",
    "composer.json", "package.json", "Gemfile", "Makefile",
    "docker-compose.yml", "Dockerfile",
    "id_rsa", ".ssh", "authorized_keys",
    "debug/default/view",
    "console", "shell", "terminal",
]

# Sensitive file extensions to check
SENSITIVE_FILES = [
    "backup.sql", "database.sql", "dump.sql",
    "backup.zip", "backup.tar.gz", "site.zip",
    "config.php.bak", "config.old", "config.yml",
    "wp-config.php~", "settings.py~",
    ".bash_history", ".mysql_history",
]

# Status codes that indicate a found resource
FOUND_CODES = {200, 201, 301, 302, 307, 403}


class Scanner:
    name = "Directory Enumeration"
    phase = "vulnerability_scan"
    description = "Discovers hidden directories, backup files, and sensitive paths"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.threads = min(config.get("dir_enum_threads", 10), 20)

    def run(self) -> dict:
        findings = []
        raw_lines = [f"Directory enumeration for {self.target}"]

        base_url = f"https://{self.target}"
        # Test if HTTPS works, fall back to HTTP
        try:
            requests.head(base_url, timeout=5, verify=False)
        except Exception:
            base_url = f"http://{self.target}"

        all_paths = COMMON_PATHS + SENSITIVE_FILES
        raw_lines.append(f"Testing {len(all_paths)} paths with {self.threads} threads")

        session = requests.Session()
        session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CyberPulse/1.0"
        session.verify = False

        found_paths = []

        def check_path(path):
            url = f"{base_url}/{path}"
            try:
                resp = session.head(url, timeout=5, allow_redirects=False)
                if resp.status_code in FOUND_CODES:
                    # Double-check with GET for 200s to filter soft-404s
                    if resp.status_code == 200:
                        get_resp = session.get(url, timeout=5)
                        # Simple soft-404 detection
                        if len(get_resp.text) < 100 and ("not found" in get_resp.text.lower() or "404" in get_resp.text):
                            return None
                    return {
                        "path": path,
                        "url": url,
                        "status": resp.status_code,
                        "content_length": resp.headers.get("content-length", ""),
                    }
            except Exception:
                pass
            return None

        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = {executor.submit(check_path, p): p for p in all_paths}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    found_paths.append(result)

        # Classify findings
        for fp in sorted(found_paths, key=lambda x: x["path"]):
            severity = self._classify_severity(fp["path"], fp["status"])
            raw_lines.append(f"  [{fp['status']}] /{fp['path']} ({severity})")

            findings.append({
                "type": "discovered_path",
                "path": fp["path"],
                "url": fp["url"],
                "status_code": fp["status"],
                "severity": severity,
            })

        raw_lines.append(f"\nTotal discovered: {len(found_paths)} paths")
        raw_output = "\n".join(raw_lines)

        outfile = self.output_dir / "09_directories.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings, "discovered": found_paths}, f, indent=2)

        logger.info("Dir enum %s: %d paths discovered", self.target, len(found_paths))
        return {"findings": findings, "raw_output": raw_output}

    @staticmethod
    def _classify_severity(path: str, status: int) -> str:
        critical_paths = [".git", ".env", ".htpasswd", "id_rsa", ".ssh", "authorized_keys",
                          "backup.sql", "database.sql", "dump.sql", ".bash_history"]
        high_paths = [".svn", "wp-config", "config.php", "phpmyadmin", "elmah.axd",
                      "trace.axd", "actuator/env", "server-info", "debug", "console"]
        medium_paths = ["admin", "login", "backup", "test", "swagger", "graphiql",
                        "phpinfo", "info.php", "server-status", ".DS_Store"]

        path_lower = path.lower()
        for p in critical_paths:
            if p in path_lower:
                return "critical"
        for p in high_paths:
            if p in path_lower:
                return "high"
        for p in medium_paths:
            if p in path_lower:
                return "medium"
        if status == 403:
            return "low"
        return "info"
