"""Module 38 — Backup File & Sensitive File Discovery.

Scans for backup files, configuration dumps, database exports,
and other sensitive files left on the web server.
"""

import json
import logging
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m38")

# Backup file patterns — {name} will be replaced with site-specific names
BACKUP_EXTENSIONS = [
    ".bak", ".backup", ".old", ".orig", ".save", ".swp", ".swo",
    "~", ".tmp", ".temp", ".copy", ".dist", ".sample",
    ".sql", ".sql.gz", ".sql.bz2", ".sql.zip",
    ".tar", ".tar.gz", ".tar.bz2", ".tgz", ".zip", ".rar", ".7z",
    ".log", ".err", ".dump",
]

SENSITIVE_FILES = [
    "/.env", "/.env.local", "/.env.production", "/.env.staging",
    "/.env.development", "/.env.backup", "/.env.bak", "/.env.old",
    "/config.php", "/config.php.bak", "/config.inc.php",
    "/wp-config.php", "/wp-config.php.bak", "/wp-config.php.old",
    "/configuration.php", "/settings.php", "/local_settings.py",
    "/config.yml", "/config.yaml", "/config.json",
    "/database.yml", "/secrets.yml", "/credentials.json",
    "/web.config", "/web.config.bak", "/appsettings.json",
    "/application.properties", "/application.yml",
    "/composer.json", "/composer.lock",
    "/package.json", "/package-lock.json", "/yarn.lock",
    "/Gemfile", "/Gemfile.lock",
    "/requirements.txt", "/Pipfile", "/Pipfile.lock",
    "/docker-compose.yml", "/Dockerfile",
    "/.docker/config.json",
    "/id_rsa", "/.ssh/id_rsa", "/.ssh/authorized_keys",
    "/htpasswd", "/.htpasswd", "/.htaccess",
    "/error_log", "/debug.log", "/access.log",
    "/.git/config", "/.git/HEAD",
    "/.svn/entries", "/.svn/wc.db",
    "/.hg/hgrc",
    "/.DS_Store",
    "/thumbs.db",
    "/crossdomain.xml",
    "/sitemap.xml",
    "/robots.txt",
    "/.well-known/security.txt",
    "/phpinfo.php", "/info.php", "/test.php",
    "/server-status", "/server-info",
    "/backup.sql", "/dump.sql", "/database.sql", "/db.sql",
    "/backup.zip", "/backup.tar.gz", "/site.zip",
    "/www.zip", "/public.zip", "/html.zip",
]


class Scanner:
    name = "Backup & Sensitive File Discovery"
    phase = "reconnaissance"
    description = "Discovers backup files, config dumps, and sensitive files on the server"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"Backup & sensitive file scan for {self.target}"]
        base_url = self._get_base_url()

        # Phase 1: Known sensitive files
        raw_lines.append("\n[Phase 1: Known Sensitive Files]")
        for file_path in SENSITIVE_FILES:
            url = base_url + file_path
            try:
                resp = self.session.get(url, timeout=8, allow_redirects=False)
                if resp.status_code == 200 and len(resp.content) > 0:
                    # Skip generic 404 pages that return 200
                    if self._is_real_content(resp, file_path):
                        sev = self._classify_severity(file_path)
                        findings.append({
                            "type": "sensitive_file",
                            "path": file_path,
                            "size": len(resp.content),
                            "content_type": resp.headers.get("Content-Type", ""),
                            "detail": f"Sensitive file found: {file_path} ({len(resp.content)} bytes)",
                            "severity": sev,
                        })
                        raw_lines.append(f"  {sev.upper()}: {file_path} ({len(resp.content)} bytes)")
            except Exception:
                continue

        # Phase 2: Domain-specific backup files
        raw_lines.append("\n[Phase 2: Domain-specific Backups]")
        domain_names = self._get_domain_names()
        for name in domain_names:
            for ext in BACKUP_EXTENSIONS[:12]:
                path = f"/{name}{ext}"
                url = base_url + path
                try:
                    resp = self.session.get(url, timeout=8, allow_redirects=False)
                    if resp.status_code == 200 and len(resp.content) > 100:
                        findings.append({
                            "type": "backup_file",
                            "path": path,
                            "size": len(resp.content),
                            "detail": f"Backup file: {path} ({len(resp.content)} bytes)",
                            "severity": "high",
                        })
                        raw_lines.append(f"  HIGH: {path} ({len(resp.content)} bytes)")
                except Exception:
                    continue

        # Phase 3: Git repository exposure
        raw_lines.append("\n[Phase 3: Git Repository Exposure]")
        git_files = [
            "/.git/config", "/.git/HEAD", "/.git/index",
            "/.git/logs/HEAD", "/.git/refs/heads/main",
            "/.git/refs/heads/master",
        ]
        git_found = False
        for path in git_files:
            url = base_url + path
            try:
                resp = self.session.get(url, timeout=8)
                if resp.status_code == 200:
                    if any(kw in resp.text for kw in ["[core]", "ref:", "DIRC"]):
                        git_found = True
                        findings.append({
                            "type": "git_exposed",
                            "path": path,
                            "detail": f"Git repository exposed: {path}",
                            "severity": "critical",
                        })
                        raw_lines.append(f"  CRITICAL: Git repo exposed {path}")
            except Exception:
                continue

        if git_found:
            findings.append({
                "type": "git_source_leak",
                "detail": "Full source code may be downloadable via .git directory!",
                "severity": "critical",
            })

        # Phase 4: SVN / HG exposure
        raw_lines.append("\n[Phase 4: SVN/HG Exposure]")
        vcs_files = [
            ("/.svn/entries", "SVN"),
            ("/.svn/wc.db", "SVN"),
            ("/.hg/hgrc", "Mercurial"),
            ("/.bzr/README", "Bazaar"),
        ]
        for path, vcs in vcs_files:
            try:
                resp = self.session.get(f"{base_url}{path}", timeout=8)
                if resp.status_code == 200 and len(resp.content) > 10:
                    findings.append({
                        "type": "vcs_exposed",
                        "vcs": vcs,
                        "path": path,
                        "detail": f"{vcs} repository exposed: {path}",
                        "severity": "critical",
                    })
                    raw_lines.append(f"  CRITICAL: {vcs} exposed at {path}")
            except Exception:
                continue

        # Phase 5: IDE and editor temp files
        raw_lines.append("\n[Phase 5: IDE/Editor Temp Files]")
        ide_files = [
            "/.idea/workspace.xml", "/.vscode/settings.json",
            "/.project", "/.classpath", "/nbproject/project.xml",
            "/.sublime-workspace", "/.sublime-project",
        ]
        for path in ide_files:
            try:
                resp = self.session.get(f"{base_url}{path}", timeout=8)
                if resp.status_code == 200 and len(resp.content) > 20:
                    findings.append({
                        "type": "ide_file",
                        "path": path,
                        "detail": f"IDE file exposed: {path}",
                        "severity": "medium",
                    })
                    raw_lines.append(f"  MEDIUM: {path}")
            except Exception:
                continue

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "38_backup_files.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("Backup scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _is_real_content(self, resp, file_path: str) -> bool:
        """Filter out custom 404 pages that return HTTP 200."""
        ct = resp.headers.get("Content-Type", "")
        ext = Path(file_path).suffix.lower()
        # Config/env files are usually text
        if ext in (".env", ".yml", ".yaml", ".json", ".xml", ".php",
                    ".py", ".rb", ".properties", ".txt", ".log"):
            if "text/html" in ct and len(resp.text) > 5000:
                return False  # Probably custom 404
            return True
        # Binary files
        if ext in (".sql", ".zip", ".gz", ".bz2", ".tar", ".rar", ".7z",
                    ".dump", ".db"):
            if "text/html" in ct:
                return False
            return True
        return len(resp.content) > 20

    def _classify_severity(self, path: str) -> str:
        critical = [".env", "id_rsa", "htpasswd", ".git", ".svn",
                    "config.php", "wp-config", "secrets", "credentials",
                    "appsettings", "application.properties"]
        high = [".sql", ".dump", ".bak", ".backup", ".zip", ".tar",
                "database", "docker-compose"]
        for kw in critical:
            if kw in path.lower():
                return "critical"
        for kw in high:
            if kw in path.lower():
                return "high"
        return "medium"

    def _get_domain_names(self) -> list[str]:
        parts = self.target.replace("www.", "").split(".")
        names = [self.target.replace(".", "_"), self.target.replace("www.", "")]
        if len(parts) >= 2:
            names.append(parts[0])
            names.append(".".join(parts[:2]))
        return list(set(names))

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
