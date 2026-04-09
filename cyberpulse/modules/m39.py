"""Module 39 — Source Code Leak Detection.

Detects exposed source code files, version control artifacts,
and code disclosure via error pages and misconfigurations.
"""

import json
import logging
import re
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m39")

# Paths that may expose source code
SOURCE_PATHS = [
    # PHP
    "/index.phps", "/config.phps", "/index.php~",
    "/index.php.bak", "/config.php.bak",
    # Python
    "/__pycache__/", "/app.py", "/wsgi.py", "/settings.py",
    "/manage.py", "/requirements.txt",
    # Node.js
    "/server.js", "/app.js", "/index.js",
    "/package.json", "/package-lock.json", "/.npmrc",
    "/node_modules/.package-lock.json",
    # Java
    "/WEB-INF/web.xml", "/WEB-INF/classes/",
    "/META-INF/MANIFEST.MF",
    # Ruby
    "/Gemfile", "/Rakefile", "/config/database.yml",
    "/config/secrets.yml",
    # .NET
    "/web.config", "/Global.asax", "/App_Code/",
    # Generic
    "/README.md", "/CHANGELOG.md", "/LICENSE",
    "/Makefile", "/Gruntfile.js", "/Gulpfile.js",
    "/webpack.config.js", "/tsconfig.json",
    "/.babelrc", "/.eslintrc", "/.prettierrc",
]

# Stack trace / error patterns that leak source code
ERROR_PATTERNS = [
    (r'File "([^"]+\.py)", line (\d+)', "Python traceback"),
    (r"at\s+[\w.]+\(([^)]+\.java):(\d+)\)", "Java stacktrace"),
    (r"in\s+(/[^\s]+\.php)\s+on\s+line\s+(\d+)", "PHP error"),
    (r"at\s+Object\.\<anonymous\>\s+\(([^)]+\.js):(\d+)", "Node.js trace"),
    (r"at\s+[\w.]+\(([^)]+\.cs):line\s+(\d+)", ".NET stacktrace"),
    (r"SQLSTATE\[", "SQL error disclosure"),
    (r"Warning.*mysql_", "MySQL error"),
    (r"pg_query\(\):", "PostgreSQL error"),
]


class Scanner:
    name = "Source Code Leak Detection"
    phase = "reconnaissance"
    description = "Detects exposed source code, error disclosures, and code artifacts"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"Source code leak detection for {self.target}"]
        base_url = self._get_base_url()

        # Phase 1: Direct source file access
        raw_lines.append("\n[Phase 1: Direct Source File Access]")
        for path in SOURCE_PATHS:
            url = base_url + path
            try:
                resp = self.session.get(url, timeout=8, allow_redirects=False)
                if resp.status_code == 200:
                    if self._looks_like_source(resp.text, path):
                        findings.append({
                            "type": "source_exposed",
                            "path": path,
                            "size": len(resp.text),
                            "detail": f"Source code file accessible: {path}",
                            "severity": "high",
                        })
                        raw_lines.append(f"  HIGH: {path} ({len(resp.text)} bytes)")
            except Exception:
                continue

        # Phase 2: Error-based source code disclosure
        raw_lines.append("\n[Phase 2: Error-based Disclosure]")
        error_triggers = [
            "/?id='",
            "/?id=1%27",
            "/nonexistent_page_xyzzy",
            "/?debug=1",
            "/?test[]=1",
            "/api/undefined",
            "/%00",
            "/index.php?foo[bar=baz",
        ]
        for trigger in error_triggers:
            url = base_url + trigger
            try:
                resp = self.session.get(url, timeout=10)
                for pattern, desc in ERROR_PATTERNS:
                    matches = re.findall(pattern, resp.text)
                    if matches:
                        findings.append({
                            "type": "error_disclosure",
                            "trigger": trigger,
                            "error_type": desc,
                            "detail": f"{desc} exposed via {trigger}",
                            "severity": "medium",
                        })
                        raw_lines.append(f"  MEDIUM: {desc} via {trigger}")
                        break
            except Exception:
                continue

        # Phase 3: Source map files
        raw_lines.append("\n[Phase 3: JavaScript Source Maps]")
        try:
            resp = self.session.get(base_url, timeout=10)
            js_files = re.findall(r'src=["\']([^"\']*\.js)["\']', resp.text)
            for js_file in js_files[:10]:
                js_url = js_file if js_file.startswith("http") else base_url + js_file
                map_url = js_url + ".map"
                try:
                    map_resp = self.session.get(map_url, timeout=8)
                    if map_resp.status_code == 200:
                        try:
                            data = map_resp.json()
                            if "sources" in data:
                                findings.append({
                                    "type": "source_map",
                                    "url": map_url,
                                    "sources_count": len(data["sources"]),
                                    "detail": f"Source map exposed: {map_url} ({len(data['sources'])} sources)",
                                    "severity": "medium",
                                })
                                raw_lines.append(f"  MEDIUM: Source map {map_url[:60]}")
                        except Exception:
                            pass
                except Exception:
                    continue
        except Exception:
            pass

        # Phase 4: .DS_Store parsing
        raw_lines.append("\n[Phase 4: .DS_Store Analysis]")
        try:
            resp = self.session.get(f"{base_url}/.DS_Store", timeout=8)
            if resp.status_code == 200 and resp.content[:4] == b"\x00\x00\x00\x01":
                # Binary .DS_Store file — extract filenames
                text = resp.content.decode(errors="ignore")
                # Simple extraction of readable strings
                names = re.findall(r"[\x20-\x7e]{4,}", text)
                interesting = [n for n in names if "." in n and len(n) < 100]
                if interesting:
                    findings.append({
                        "type": "ds_store",
                        "files_found": interesting[:20],
                        "detail": f".DS_Store exposes {len(interesting)} filenames",
                        "severity": "medium",
                    })
                    raw_lines.append(f"  MEDIUM: .DS_Store — {len(interesting)} names leaked")
        except Exception:
            pass

        # Phase 5: Stack technology fingerprinting from headers/content
        raw_lines.append("\n[Phase 5: Technology Fingerprinting]")
        try:
            resp = self.session.get(base_url, timeout=10)
            tech_indicators = {
                "X-Powered-By": resp.headers.get("X-Powered-By"),
                "Server": resp.headers.get("Server"),
                "X-AspNet-Version": resp.headers.get("X-AspNet-Version"),
                "X-Runtime": resp.headers.get("X-Runtime"),
                "X-Generator": resp.headers.get("X-Generator"),
            }
            for header, value in tech_indicators.items():
                if value:
                    findings.append({
                        "type": "tech_fingerprint",
                        "header": header,
                        "value": value,
                        "detail": f"Technology disclosure: {header}: {value}",
                        "severity": "low",
                    })
                    raw_lines.append(f"  LOW: {header}: {value}")

            # HTML meta generators
            generators = re.findall(
                r'<meta\s+name=["\']generator["\']\s+content=["\']([^"\']+)["\']',
                resp.text, re.I,
            )
            for gen in generators:
                findings.append({
                    "type": "tech_fingerprint",
                    "source": "meta_generator",
                    "value": gen,
                    "detail": f"Generator tag: {gen}",
                    "severity": "low",
                })
                raw_lines.append(f"  LOW: Generator: {gen}")
        except Exception:
            pass

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "39_source_leak.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("Source leak scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _looks_like_source(self, content: str, path: str) -> bool:
        """Check if the response looks like actual source code."""
        ext = Path(path).suffix.lower()
        source_indicators = {
            ".py": ["import ", "def ", "class ", "from "],
            ".js": ["function ", "const ", "var ", "module.exports"],
            ".php": ["<?php", "<?=", "function ", "class "],
            ".rb": ["require ", "class ", "def ", "end"],
            ".java": ["public class", "import ", "package "],
            ".cs": ["using ", "namespace ", "class "],
            ".json": ["{", '"name"', '"version"'],
            ".yml": ["---", ":", "- "],
            ".yaml": ["---", ":", "- "],
            ".xml": ["<?xml", "<web-app", "<configuration"],
        }
        indicators = source_indicators.get(ext, [])
        if indicators:
            return any(ind in content for ind in indicators)
        # Fallback: check if not HTML
        return "<html" not in content.lower()[:500]

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
