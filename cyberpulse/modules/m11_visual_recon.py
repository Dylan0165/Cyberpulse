"""Module 11-VR — Visual Reconnaissance.

Screenshots all discovered web services using Playwright (if available).
Falls back to HTTP probing when Playwright is not installed.
"""

import logging
from pathlib import Path
from urllib.parse import urlparse

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger("cyberpulse.modules.m11_visual_recon")

_COMMON_PORTS = [80, 443, 8080, 8443, 8000, 3000, 5000, 8888]


class Scanner:
    name = "Visual Recon"
    phase = "custom"
    description = "Screenshots web services and collects page titles/technologies"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target.rstrip("/")
        self.output_dir = Path(output_dir)
        self.config = config or {}

    # ── URL helpers ───────────────────────────────────────────────────────────

    def _build_urls(self) -> list[str]:
        parsed = urlparse(self.target)
        hostname = parsed.hostname or self.target
        base_scheme = parsed.scheme or "http"

        urls = [self.target]
        for port in _COMMON_PORTS:
            if port in (80, 443):
                scheme = "https" if port == 443 else "http"
                url = f"{scheme}://{hostname}"
            else:
                url = f"{base_scheme}://{hostname}:{port}"
            if url not in urls:
                urls.append(url)
        return urls

    # ── HTTP probe (no Playwright) ─────────────────────────────────────────────

    def _http_probe(self, url: str) -> dict | None:
        try:
            r = requests.get(url, timeout=6, verify=False,
                             headers={"User-Agent": "CyberPulse-Scout/1.0"})
        except Exception:
            return None

        # Extract title from HTML
        title = ""
        if "text/html" in r.headers.get("content-type", ""):
            import re
            m = re.search(r"<title[^>]*>([^<]{1,200})</title>", r.text, re.IGNORECASE)
            if m:
                title = m.group(1).strip()

        server = r.headers.get("server", "")
        powered_by = r.headers.get("x-powered-by", "")
        return {
            "url": url,
            "status": r.status_code,
            "title": title,
            "server": server,
            "powered_by": powered_by,
            "screenshot": None,
        }

    # ── Playwright screenshot ──────────────────────────────────────────────────

    def _playwright_screenshot(self, url: str) -> dict | None:
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    args=["--no-sandbox", "--disable-setuid-sandbox",
                          "--disable-dev-shm-usage"])
                page = browser.new_page()
                page.goto(url, timeout=12_000, wait_until="domcontentloaded")
                title = page.title()
                screenshot_name = f"screenshot_{url.replace('://', '_').replace('/', '_').replace(':', '_')[:60]}.png"
                screenshot_path = self.output_dir / screenshot_name
                page.screenshot(path=str(screenshot_path), full_page=False)
                browser.close()
                return {
                    "url": url,
                    "title": title,
                    "screenshot": str(screenshot_path),
                    "status": 200,
                    "server": "",
                    "powered_by": "",
                }
        except ImportError:
            logger.debug("Playwright not installed — using HTTP probe fallback")
            return None
        except Exception as e:
            logger.debug("Playwright failed for %s: %s", url, e)
            return None

    # ── main ──────────────────────────────────────────────────────────────────

    def run(self) -> dict:
        findings: list[dict] = []
        screenshots: list[dict] = []
        raw_lines: list[str] = []

        raw_lines.append(f"[+] Visual Recon — target: {self.target}")
        urls = self._build_urls()
        raw_lines.append(f"[*] Probing {len(urls)} URLs")

        for url in urls:
            # Try Playwright first, fall back to HTTP probe
            info = self._playwright_screenshot(url) or self._http_probe(url)
            if info is None:
                raw_lines.append(f"    [-] {url} — not reachable")
                continue

            status = info.get("status", 0)
            title = info.get("title", "")
            raw_lines.append(f"    [+] {url} — HTTP {status} — {title or '(no title)'}")

            if status in range(200, 400):
                screenshots.append(info)
                findings.append({
                    "type": "web_service_discovered",
                    "severity": "INFO",
                    "title": f"Web service at {url}",
                    "description": (
                        f"HTTP {status} — Page title: '{title}'. "
                        f"Server: {info.get('server') or 'unknown'}."
                    ),
                    "impact": "Additional attack surface discovered.",
                    "recommendation": "Verify this service should be publicly accessible.",
                    "evidence": (
                        f"URL: {url}\nStatus: {status}\nTitle: {title}\n"
                        f"Server: {info.get('server','')}\nPowered-by: {info.get('powered_by','')}"
                    ),
                    "screenshot": info.get("screenshot"),
                })

        raw_lines.append(f"[+] Done — {len(screenshots)} services found")
        return {
            "findings": findings,
            "raw_output": "\n".join(raw_lines),
            "screenshots": screenshots,
        }
