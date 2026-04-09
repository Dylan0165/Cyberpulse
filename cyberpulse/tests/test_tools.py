"""Tests for tool wrappers — parse methods with fixture data."""

import json
import sys
from pathlib import Path

# Ensure the cyberpulse root is on sys.path
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "tool_outputs"


def _load_fixture(name: str) -> dict:
    with open(FIXTURES / name, "r", encoding="utf-8") as f:
        return json.load(f)


# ── John the Ripper ──────────────────────────────────────────────

class TestJohnWrapper:
    def test_parse_cracked(self):
        from tools.password.john import JohnWrapper
        data = _load_fixture("john_output.json")
        wrapper = JohnWrapper()
        findings = wrapper.parse(data["stdout"], data["stderr"], "/tmp/hashes.txt")
        assert len(findings) >= 1
        assert any("gekraakt" in f.title.lower() or "cracked" in f.title.lower() for f in findings)

    def test_parse_empty(self):
        from tools.password.john import JohnWrapper
        wrapper = JohnWrapper()
        findings = wrapper.parse("", "", "/tmp/hashes.txt")
        assert len(findings) == 0


# ── Nikto ────────────────────────────────────────────────────────

class TestNiktoWrapper:
    def test_parse_findings(self):
        from tools.web.nikto import NiktoWrapper
        data = _load_fixture("nikto_output.json")
        wrapper = NiktoWrapper()
        findings = wrapper.parse(data["stdout"], data["stderr"], "example.com")
        assert len(findings) >= 1

    def test_parse_empty(self):
        from tools.web.nikto import NiktoWrapper
        wrapper = NiktoWrapper()
        findings = wrapper.parse("", "", "example.com")
        assert len(findings) == 0


# ── Nuclei ───────────────────────────────────────────────────────

class TestNucleiWrapper:
    def test_parse_jsonl(self):
        from tools.web.nuclei import NucleiWrapper
        data = _load_fixture("nuclei_output.json")
        wrapper = NucleiWrapper()
        findings = wrapper.parse(data["stdout"], data["stderr"], "example.com")
        assert len(findings) == 2
        assert any("cve" in f.title.lower() for f in findings)


# ── Trivy ────────────────────────────────────────────────────────

class TestTrivyWrapper:
    def test_parse_json(self):
        from tools.vulnanalysis.trivy import TrivyWrapper
        data = _load_fixture("trivy_output.json")
        wrapper = TrivyWrapper()
        findings = wrapper.parse(data["stdout"], data["stderr"], "/app")
        assert len(findings) == 2
        assert any(f.cve and f.cve.startswith("CVE") for f in findings)


# ── Tool Runner ──────────────────────────────────────────────────

class TestToolRunner:
    def test_registry_populated(self):
        from tools.tool_runner import get_registry
        registry = get_registry()
        assert len(registry) > 0
        assert "nikto" in registry or "nuclei" in registry

    def test_scan_profiles_exist(self):
        from tools.tool_runner import TOOL_SCAN_PROFILES
        assert "web_quick" in TOOL_SCAN_PROFILES
        assert "web_full" in TOOL_SCAN_PROFILES
        assert len(TOOL_SCAN_PROFILES["web_quick"]) > 0


# ── CyberChef (pure Python) ─────────────────────────────────────

class TestCyberchef:
    def test_run_native_detect(self):
        from tools.crypto.cyberchef_headless import CyberchefWrapper
        wrapper = CyberchefWrapper()
        stdout, stderr = wrapper.run_native("SGVsbG8gV29ybGQ=", operation="detect")
        data = json.loads(stdout)
        assert "base64_decoded" in data
        assert "Hello World" in data["base64_decoded"]

    def test_run_native_hash(self):
        from tools.crypto.cyberchef_headless import CyberchefWrapper
        wrapper = CyberchefWrapper()
        stdout, _ = wrapper.run_native("test", operation="hash")
        data = json.loads(stdout)
        assert "md5" in data
        assert "sha256" in data


# ── HashID (pure Python) ────────────────────────────────────────

class TestHashId:
    def test_instantiation(self):
        from tools.crypto.hashid import HashidWrapper
        wrapper = HashidWrapper()
        assert wrapper.name == "hashid"
        assert wrapper.category.value == "crypto"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
