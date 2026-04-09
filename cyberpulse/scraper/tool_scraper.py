"""Tool Scraper — collects information about popular security tools and updates."""

import json
import logging
from pathlib import Path

import requests
import feedparser

from config import Config

logger = logging.getLogger("cyberpulse.scraper.tool")


class ToolScraper:
    """Scrapes security tool release info and news."""

    def __init__(self):
        self.output_dir = Config.DATA_DIR / "scraped"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = self.output_dir / "security_tools.json"
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "CyberPulse-Tool-Scraper/1.0"

    def run(self) -> int:
        """Fetch tool data from multiple sources. Returns count of items."""
        tools = self._load_existing()
        existing_names = {t["name"] for t in tools}
        new_count = 0

        # Source 1: GitHub releases for popular security tools
        github_tools = self._fetch_github_releases()
        for tool in github_tools:
            if tool["name"] not in existing_names:
                tools.append(tool)
                existing_names.add(tool["name"])
                new_count += 1
            else:
                # Update existing entry
                for i, t in enumerate(tools):
                    if t["name"] == tool["name"]:
                        tools[i] = tool
                        break

        # Source 2: Exploit-DB RSS
        exploit_items = self._fetch_exploit_feed()
        for item in exploit_items:
            key = item.get("name", "")
            if key and key not in existing_names:
                tools.append(item)
                existing_names.add(key)
                new_count += 1

        # Keep last 500 entries
        tools = tools[:500]

        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(tools, f, indent=2, ensure_ascii=False)

        logger.info("Tool scraper: %d new items, %d total", new_count, len(tools))
        return new_count

    def _load_existing(self) -> list:
        if self.output_file.exists():
            with open(self.output_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _fetch_github_releases(self) -> list[dict]:
        """Fetch latest releases from popular security tool repos."""
        repos = [
            ("nmap/nmap", "Nmap", "Network scanner"),
            ("sqlmapproject/sqlmap", "sqlmap", "SQL injection tool"),
            ("OJ/gobuster", "Gobuster", "Directory/DNS brute-forcer"),
            ("projectdiscovery/nuclei", "Nuclei", "Vulnerability scanner"),
            ("projectdiscovery/httpx", "httpx", "HTTP toolkit"),
            ("projectdiscovery/subfinder", "Subfinder", "Subdomain discovery"),
            ("ffuf/ffuf", "ffuf", "Web fuzzer"),
            ("vanhauser-thc/thc-hydra", "Hydra", "Password brute-forcer"),
            ("michenriksen/aquatone", "Aquatone", "Domain reconnaissance"),
            ("OWASP/ZAP", "OWASP ZAP", "Web app security scanner"),
        ]

        tools = []
        for repo, name, description in repos:
            try:
                resp = self.session.get(
                    f"https://api.github.com/repos/{repo}/releases/latest",
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    tools.append({
                        "name": name,
                        "description": description,
                        "latest_version": data.get("tag_name", ""),
                        "published": data.get("published_at", ""),
                        "url": data.get("html_url", ""),
                        "repo": repo,
                        "source": "github",
                        "type": "tool",
                    })
            except Exception as e:
                logger.debug("GitHub release fetch failed for %s: %s", repo, e)

        logger.info("GitHub: fetched releases for %d tools", len(tools))
        return tools

    def _fetch_exploit_feed(self) -> list[dict]:
        """Fetch recent exploits from Exploit-DB RSS."""
        items = []
        try:
            feed = feedparser.parse("https://www.exploit-db.com/rss.xml")
            for entry in feed.entries[:30]:
                items.append({
                    "name": entry.get("title", "")[:200],
                    "description": entry.get("summary", "")[:300],
                    "published": entry.get("published", ""),
                    "url": entry.get("link", ""),
                    "source": "exploit-db",
                    "type": "exploit",
                })
            logger.info("Exploit-DB: fetched %d items", len(items))
        except Exception as e:
            logger.warning("Exploit-DB RSS fetch failed: %s", e)
        return items
