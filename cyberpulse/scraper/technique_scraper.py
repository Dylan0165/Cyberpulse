"""Technique Scraper — fetches MITRE ATT&CK techniques and maps them."""

import json
import logging
from pathlib import Path

import requests

from config import Config

logger = logging.getLogger("cyberpulse.scraper.technique")


class TechniqueScraper:
    """Scrapes MITRE ATT&CK Enterprise techniques and stores locally."""

    def __init__(self):
        self.output_dir = Config.DATA_DIR / "scraped"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = self.output_dir / "attack_techniques.json"
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "CyberPulse-Technique-Scraper/1.0"

    def run(self) -> int:
        """Fetch ATT&CK techniques. Returns count of techniques stored."""
        techniques = []

        # MITRE ATT&CK STIX data (Enterprise)
        try:
            resp = self.session.get(
                "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json",
                timeout=60,
            )
            if resp.status_code == 200:
                data = resp.json()
                for obj in data.get("objects", []):
                    if obj.get("type") == "attack-pattern":
                        technique = self._parse_technique(obj)
                        if technique:
                            techniques.append(technique)

                logger.info("ATT&CK: fetched %d techniques", len(techniques))
        except Exception as e:
            logger.warning("ATT&CK fetch failed: %s", e)

        if not techniques:
            # Fallback: use a curated subset
            techniques = self._get_fallback_techniques()
            logger.info("Using %d fallback techniques", len(techniques))

        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(techniques, f, indent=2, ensure_ascii=False)

        return len(techniques)

    def _parse_technique(self, obj: dict) -> dict | None:
        """Parse a STIX attack-pattern object into our format."""
        technique_id = ""
        for ref in obj.get("external_references", []):
            if ref.get("source_name") == "mitre-attack":
                technique_id = ref.get("external_id", "")
                break

        if not technique_id:
            return None

        name = obj.get("name", "")
        description = obj.get("description", "")[:500]

        # Extract tactics (kill chain phases)
        tactics = []
        for phase in obj.get("kill_chain_phases", []):
            if phase.get("kill_chain_name") == "mitre-attack":
                tactics.append(phase.get("phase_name", ""))

        # Extract platforms
        platforms = obj.get("x_mitre_platforms", [])

        # Detection
        detection = obj.get("x_mitre_detection", "")[:300]

        return {
            "technique_id": technique_id,
            "name": name,
            "description": description,
            "tactics": tactics,
            "platforms": platforms,
            "detection": detection,
            "url": f"https://attack.mitre.org/techniques/{technique_id.replace('.', '/')}/",
        }

    @staticmethod
    def _get_fallback_techniques() -> list[dict]:
        """Return a minimal set of common techniques if fetch fails."""
        return [
            {
                "technique_id": "T1190",
                "name": "Exploit Public-Facing Application",
                "description": "Adversaries may attempt to exploit a weakness in an Internet-facing host or system to initially access a network.",
                "tactics": ["initial-access"],
                "platforms": ["Linux", "Windows", "macOS"],
            },
            {
                "technique_id": "T1110",
                "name": "Brute Force",
                "description": "Adversaries may use brute force techniques to gain access to accounts when passwords are unknown.",
                "tactics": ["credential-access"],
                "platforms": ["Linux", "Windows", "macOS"],
            },
            {
                "technique_id": "T1071",
                "name": "Application Layer Protocol",
                "description": "Adversaries may communicate using application layer protocols to avoid detection.",
                "tactics": ["command-and-control"],
                "platforms": ["Linux", "Windows", "macOS"],
            },
            {
                "technique_id": "T1059",
                "name": "Command and Scripting Interpreter",
                "description": "Adversaries may abuse command and script interpreters to execute commands.",
                "tactics": ["execution"],
                "platforms": ["Linux", "Windows", "macOS"],
            },
            {
                "technique_id": "T1078",
                "name": "Valid Accounts",
                "description": "Adversaries may obtain and abuse credentials of existing accounts.",
                "tactics": ["defense-evasion", "persistence", "initial-access"],
                "platforms": ["Linux", "Windows", "macOS"],
            },
        ]
