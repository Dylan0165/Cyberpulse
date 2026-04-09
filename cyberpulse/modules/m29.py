"""Module 29 — JWT Token Analysis.

Analyzes JSON Web Tokens for weak algorithms, missing claims,
expired tokens, and signature bypass vulnerabilities.
"""

import json
import logging
import base64
import time
import re
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m29")


class Scanner:
    name = "JWT Token Analysis"
    phase = "scanning"
    description = "Analyzes JWT tokens for weak algorithms, bypass techniques, and misconfigurations"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"JWT token analysis for {self.target}"]
        base_url = self._get_base_url()

        # Phase 1: Find JWT tokens
        raw_lines.append("\n[Phase 1: JWT Token Discovery]")
        tokens = self._discover_jwts(base_url)
        raw_lines.append(f"  Found {len(tokens)} JWT token(s)")

        if not tokens:
            raw_lines.append("  No JWT tokens found in responses")
            findings.append({
                "type": "no_jwt",
                "detail": "No JWT tokens discovered in responses",
                "severity": "info",
            })
            raw_output = "\n".join(raw_lines)
            self._save(findings, raw_output)
            return {"findings": findings, "raw_output": raw_output}

        # Phase 2: Analyze each token
        for i, (source, token) in enumerate(tokens):
            raw_lines.append(f"\n[Phase 2: Analyzing JWT #{i+1} from {source}]")

            header, payload = self._decode_jwt(token)
            if not header:
                raw_lines.append("  Failed to decode token")
                continue

            raw_lines.append(f"  Header: {json.dumps(header)}")
            raw_lines.append(f"  Payload keys: {list(payload.keys())}")

            # Check algorithm
            alg = header.get("alg", "")
            raw_lines.append(f"  Algorithm: {alg}")

            if alg.lower() == "none":
                findings.append({
                    "type": "jwt_none_algorithm",
                    "source": source,
                    "detail": "JWT uses 'none' algorithm — no signature verification!",
                    "severity": "critical",
                })
                raw_lines.append("    CRITICAL: 'none' algorithm!")

            if alg in ("HS256", "HS384", "HS512"):
                findings.append({
                    "type": "jwt_hmac_symmetric",
                    "source": source,
                    "algorithm": alg,
                    "detail": f"JWT uses symmetric HMAC ({alg}) — susceptible to brute force if key is weak",
                    "severity": "medium",
                })
                raw_lines.append(f"    Symmetric HMAC: {alg}")

                # Test common weak secrets
                weak = self._test_weak_secrets(token, alg)
                if weak:
                    findings.append({
                        "type": "jwt_weak_secret",
                        "source": source,
                        "secret": weak,
                        "detail": f"JWT signed with weak/common secret: '{weak}'",
                        "severity": "critical",
                    })
                    raw_lines.append(f"    CRITICAL: Weak secret found: '{weak}'")

            # Check for missing claims
            if "exp" not in payload:
                findings.append({
                    "type": "jwt_no_expiry",
                    "source": source,
                    "detail": "JWT has no expiration claim (exp) — token never expires",
                    "severity": "high",
                })
                raw_lines.append("    No expiration!")

            if "exp" in payload:
                exp_ts = payload["exp"]
                if isinstance(exp_ts, (int, float)) and exp_ts < time.time():
                    findings.append({
                        "type": "jwt_expired_accepted",
                        "source": source,
                        "detail": "Server accepted an expired JWT token",
                        "severity": "high",
                    })
                    raw_lines.append("    Expired token still accepted!")

                if isinstance(exp_ts, (int, float)):
                    iat = payload.get("iat", time.time())
                    lifetime = exp_ts - iat
                    if lifetime > 86400 * 30:  # > 30 days
                        findings.append({
                            "type": "jwt_long_lifetime",
                            "source": source,
                            "lifetime_days": round(lifetime / 86400),
                            "detail": f"JWT has very long lifetime: {round(lifetime / 86400)} days",
                            "severity": "medium",
                        })

            if "iss" not in payload:
                findings.append({
                    "type": "jwt_no_issuer",
                    "source": source,
                    "detail": "JWT missing issuer (iss) claim",
                    "severity": "low",
                })

            if "aud" not in payload:
                findings.append({
                    "type": "jwt_no_audience",
                    "source": source,
                    "detail": "JWT missing audience (aud) claim",
                    "severity": "low",
                })

            # Check for sensitive data in payload
            sensitive_keys = ["password", "secret", "ssn", "credit_card",
                              "api_key", "private_key", "cc_number"]
            for key in payload:
                if key.lower() in sensitive_keys:
                    findings.append({
                        "type": "jwt_sensitive_data",
                        "source": source,
                        "field": key,
                        "detail": f"JWT contains sensitive field: '{key}'",
                        "severity": "high",
                    })
                    raw_lines.append(f"    Sensitive data in token: {key}")

            # Check kid header injection
            kid = header.get("kid", "")
            if kid:
                raw_lines.append(f"  Key ID (kid): {kid}")
                findings.append({
                    "type": "jwt_kid_present",
                    "source": source,
                    "kid": kid,
                    "detail": f"JWT uses 'kid' header ({kid}) — potential injection vector",
                    "severity": "info",
                })

            # Check jku/x5u header
            for dangerous_header in ("jku", "x5u", "x5c"):
                if dangerous_header in header:
                    findings.append({
                        "type": f"jwt_{dangerous_header}_header",
                        "source": source,
                        "value": header[dangerous_header],
                        "detail": f"JWT uses '{dangerous_header}' header — potential key injection",
                        "severity": "high",
                    })
                    raw_lines.append(f"    Dangerous header: {dangerous_header}")

        # Phase 3: Test algorithm confusion (RS256 -> HS256)
        raw_lines.append("\n[Phase 3: Algorithm Confusion Test]")
        for source, token in tokens:
            alg_result = self._test_alg_confusion(base_url, token)
            if alg_result:
                findings.append(alg_result)
                raw_lines.append(f"  CRITICAL: {alg_result['detail']}")

        raw_output = "\n".join(raw_lines)
        self._save(findings, raw_output)
        logger.info("JWT analysis %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _discover_jwts(self, base_url: str) -> list[tuple]:
        """Find JWT tokens in responses, cookies, and headers."""
        tokens = []
        jwt_pattern = r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*'

        # Check common auth endpoints
        auth_endpoints = [
            "/", "/api", "/api/v1", "/login", "/auth",
            "/api/user", "/api/me", "/dashboard",
        ]

        for ep in auth_endpoints:
            try:
                resp = self.session.get(base_url + ep, timeout=10)

                # Check response body
                matches = re.findall(jwt_pattern, resp.text)
                for m in matches:
                    tokens.append((f"body:{ep}", m))

                # Check headers
                for header_name in ("Authorization", "X-Auth-Token", "X-JWT",
                                    "X-Access-Token", "Token"):
                    val = resp.headers.get(header_name, "")
                    matches = re.findall(jwt_pattern, val)
                    for m in matches:
                        tokens.append((f"header:{header_name}", m))

                # Check cookies
                for cookie_name, cookie_val in resp.cookies.items():
                    matches = re.findall(jwt_pattern, cookie_val)
                    for m in matches:
                        tokens.append((f"cookie:{cookie_name}", m))

            except Exception:
                continue

        # Deduplicate
        seen = set()
        unique = []
        for source, token in tokens:
            if token not in seen:
                seen.add(token)
                unique.append((source, token))
        return unique

    def _decode_jwt(self, token: str) -> tuple:
        """Decode JWT header and payload without verification."""
        try:
            parts = token.split(".")
            if len(parts) < 2:
                return None, None

            # Pad base64
            header_b64 = parts[0] + "=" * (4 - len(parts[0]) % 4)
            payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)

            header = json.loads(base64.urlsafe_b64decode(header_b64))
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            return header, payload
        except Exception:
            return None, None

    def _test_weak_secrets(self, token: str, alg: str) -> str | None:
        """Test JWT against common weak secrets."""
        try:
            import hmac
            import hashlib

            parts = token.split(".")
            message = f"{parts[0]}.{parts[1]}".encode()
            sig = parts[2]

            # Pad signature
            sig_padded = sig + "=" * (4 - len(sig) % 4)
            original_sig = base64.urlsafe_b64decode(sig_padded)

            hash_func = {
                "HS256": hashlib.sha256,
                "HS384": hashlib.sha384,
                "HS512": hashlib.sha512,
            }.get(alg, hashlib.sha256)

            weak_secrets = [
                "secret", "password", "123456", "admin", "key",
                "jwt_secret", "changeme", "test", "default",
                "supersecret", "mysecret", "jwt", "token",
            ]

            for secret in weak_secrets:
                computed = hmac.new(secret.encode(), message, hash_func).digest()
                if computed == original_sig:
                    return secret
        except Exception:
            pass
        return None

    def _test_alg_confusion(self, base_url: str, token: str):
        """Test if server accepts none algorithm."""
        header, payload = self._decode_jwt(token)
        if not header:
            return None

        # Create token with alg: none
        header["alg"] = "none"
        new_header = base64.urlsafe_b64encode(
            json.dumps(header).encode()).decode().rstrip("=")
        new_payload = token.split(".")[1]
        forged = f"{new_header}.{new_payload}."

        # Try using it
        try:
            resp = self.session.get(base_url + "/api/me",
                headers={"Authorization": f"Bearer {forged}"}, timeout=10)
            if resp.status_code == 200:
                return {
                    "type": "jwt_alg_none_bypass",
                    "detail": "Server accepts JWT with 'none' algorithm — full auth bypass!",
                    "severity": "critical",
                }
        except Exception:
            pass
        return None

    def _save(self, findings: list, raw_output: str):
        outfile = self.output_dir / "29_jwt.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
