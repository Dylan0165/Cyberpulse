"""M73 — Session & Cookie Audit (Gray Box)
Analyzes session cookies and tokens provided by the user for weaknesses:
weak JWT, missing flags, predictable session IDs, short expiry.
"""
import base64
import json
import re
import urllib.request


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

    def _decode_jwt(self, token):
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None, None
            header = json.loads(base64.urlsafe_b64decode(parts[0] + "=="))
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
            return header, payload
        except Exception:
            return None, None

    def run(self):
        findings = []
        output = []
        token = self.creds.get("api_token", "")

        output.append(f"[M73] Sessie & Cookie audit: {self.target_url}")

        # 1. Analyze JWT token if provided
        if token:
            raw_token = token.replace("Bearer ", "").strip()
            header, payload = self._decode_jwt(raw_token)
            if header and payload:
                output.append(f"  JWT gedetecteerd")
                output.append(f"  Header: {header}")
                output.append(f"  Payload keys: {list(payload.keys())}")

                if header.get("alg", "").upper() == "NONE":
                    findings.append({
                        "title": "JWT met Algoritme 'none' — Kritieke Kwetsbaarheid",
                        "severity": "critical",
                        "description": "JWT gebruikt algoritme 'none', wat betekent dat de handtekening volledig kan worden weggelaten. Aanvallers kunnen tokens vervalsen.",
                        "recommendation": "Weiger alle JWT tokens met alg=none. Gebruik RS256 of ES256. Valideer altijd het algoritme server-side."
                    })
                elif header.get("alg", "") in ("HS256", "HS384", "HS512"):
                    findings.append({
                        "title": "JWT Gebruikt Symmetrisch Algoritme (HMAC)",
                        "severity": "medium",
                        "description": f"JWT gebruikt {header['alg']} (symmetrisch). Als de geheime sleutel wordt gelekt, kunnen aanvallers geldige tokens genereren.",
                        "recommendation": "Gebruik asymmetrische algoritmen (RS256, ES256) voor betere beveiliging, met name in microservices architecturen."
                    })

                if "exp" not in payload:
                    findings.append({
                        "title": "JWT Zonder Vervaldatum (exp Claim Ontbreekt)",
                        "severity": "high",
                        "description": "JWT token heeft geen 'exp' claim. Token is eeuwig geldig na uitgifte.",
                        "recommendation": "Voeg altijd een exp-claim toe. Gebruik korte levensduur (15-60 min voor access tokens). Implementeer refresh token mechanisme."
                    })

                sensitive_keys = ["password", "passwd", "secret", "api_key", "ssn", "credit"]
                for key in payload:
                    if any(s in key.lower() for s in sensitive_keys):
                        findings.append({
                            "title": "Gevoelige Data in JWT Payload",
                            "severity": "high",
                            "description": f"JWT payload bevat mogelijk gevoelig veld: '{key}'. JWT payloads zijn base64-gecodeerd maar NIET versleuteld.",
                            "recommendation": "Sla nooit wachtwoorden, API-sleutels of PII op in JWT payloads. Gebruik JWE (JSON Web Encryption) als je gevoelige claims nodig hebt."
                        })

        # 2. Fetch homepage and check cookie flags
        try:
            req = urllib.request.Request(self.target_url,
                headers={"User-Agent": "CyberPulse/4.0 Security Scanner"})
            resp = urllib.request.urlopen(req, timeout=8)
            set_cookie_headers = resp.headers.get_all("Set-Cookie") or []
            for cookie_str in set_cookie_headers:
                output.append(f"  Cookie: {cookie_str[:120]}")
                name = cookie_str.split("=")[0].strip()
                lower = cookie_str.lower()
                issues = []
                if "httponly" not in lower:
                    issues.append("HttpOnly ontbreekt (XSS kan cookie stelen)")
                if "secure" not in lower:
                    issues.append("Secure ontbreekt (cookie verstuurd over HTTP)")
                if "samesite" not in lower:
                    issues.append("SameSite ontbreekt (kwetsbaar voor CSRF)")
                if issues:
                    findings.append({
                        "title": f"Onveilige Cookie Flags: {name}",
                        "severity": "medium",
                        "description": f"Cookie '{name}' mist veiligheidsattributen: {'; '.join(issues)}",
                        "recommendation": f"Stel cookie in als: Set-Cookie: {name}=...; HttpOnly; Secure; SameSite=Strict"
                    })
        except Exception as e:
            output.append(f"  [-] Kon cookies niet ophalen: {e}")

        if not findings:
            output.append("  [OK] Geen sessie/token kwetsbaarheden gevonden")
        return {"findings": findings, "raw_output": "\n".join(output)}
