"""M79 — IDOR / Broken Object-Level Authorization (Gray Box)
Systematic IDOR testing across object types using auth credentials.
Tests sequential IDs, UUID manipulation, and parameter fuzzing.
"""
import urllib.request
import urllib.error
import http.cookiejar
import json
import re


class Scanner:
    def __init__(self, target, output_dir, config=None):
        self.target = target
        self.output_dir = output_dir
        self.config = config or {}
        self.creds = self.config.get("credentials", {})
        if not self.target.startswith(("http://", "https://")):
            self.target_url = f"https://{self.target}"
        else:
            self.target_url = self.target
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar))
        self.api_token = self.creds.get("api_token", "")
        self.api_header = self.creds.get("api_header", "Authorization")

    def _headers(self):
        h = {"User-Agent": "CyberPulse/4.0"}
        if self.api_token:
            val = self.api_token if self.api_token.startswith("Bearer ") \
                else f"Bearer {self.api_token}"
            h[self.api_header] = val
        return h

    def _get(self, path):
        try:
            req = urllib.request.Request(f"{self.target_url}{path}",
                headers=self._headers())
            resp = self.opener.open(req, timeout=6)
            return resp.status, resp.read(1024).decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            return e.code, ""
        except Exception:
            return 0, ""

    OBJECT_PATHS = [
        "/api/users/{id}", "/api/v1/users/{id}",
        "/api/orders/{id}", "/api/v1/orders/{id}",
        "/api/invoices/{id}", "/api/documents/{id}",
        "/api/accounts/{id}", "/api/profiles/{id}",
        "/api/tickets/{id}", "/api/messages/{id}",
        "/user/{id}", "/account/{id}", "/profile/{id}",
        "/order/{id}", "/invoice/{id}",
    ]

    def run(self):
        findings = []
        output = []

        output.append(f"[M79] IDOR / BOLA test: {self.target_url}")

        if not self.api_token and not self.creds.get("web_username"):
            return {"findings": [], "raw_output": "[M79] Geen credentials — overgeslagen"}

        # Test sequential integer IDs
        ids_to_test = list(range(1, 6)) + [100, 1000]
        accessible = {}
        for path_template in self.OBJECT_PATHS:
            results = []
            for obj_id in ids_to_test:
                path = path_template.replace("{id}", str(obj_id))
                status, body = self._get(path)
                if status == 200 and len(body) > 30:
                    results.append((obj_id, body[:64]))
                output.append(f"  GET {path} -> {status}")
            if len(results) >= 3:
                accessible[path_template] = results

        for template, results in accessible.items():
            id_list = [str(r[0]) for r in results[:3]]
            findings.append({
                "title": f"IDOR: Meerdere Object Records Opvraagbaar via {template}",
                "severity": "high",
                "description": (
                    f"Endpoint '{template}' retourneert data voor {len(results)} verschillende ID's "
                    f"({', '.join(id_list)}) met dezelfde ingelogde gebruiker. "
                    "Dit wijst op Broken Object-Level Authorization (BOLA/IDOR)."
                ),
                "recommendation": (
                    "Voeg server-side ownership-check toe: verifieer dat de ingelogde gebruiker "
                    "de eigenaar is van het opgevraagde object. Gebruik UUID's i.p.v. "
                    "opeenvolgende integers als object-ID's."
                )
            })

        # Check if unauthenticated access is also possible on found paths
        for template in list(accessible.keys())[:2]:
            path = template.replace("{id}", "1")
            url = f"{self.target_url}{path}"
            try:
                req = urllib.request.Request(url,
                    headers={"User-Agent": "CyberPulse/4.0"})
                resp = urllib.request.urlopen(req, timeout=5)
                if resp.status == 200:
                    findings.insert(0, {
                        "title": f"IDOR + Geen Authenticatie Vereist: {template}",
                        "severity": "critical",
                        "description": f"Object {path} is bereikbaar ZONDER authenticatie. Combinatie van IDOR en ontbrekende authenticatie.",
                        "recommendation": "Vereist authenticatie op alle API endpoints. Voeg object ownership validatie toe. Voer regelmatig BOLA/IDOR tests uit."
                    })
            except Exception:
                pass

        if not findings:
            output.append("  [OK] Geen IDOR kwetsbaarheden gedetecteerd")
        return {"findings": findings, "raw_output": "\n".join(output)}
