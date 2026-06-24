"""Subdomain discovery.

Primary path: ask the Kali scanner's /subdomain-discovery endpoint (theHarvester
+ DNS brute force + CT logs, with an nmap -sn alive check). If that endpoint is
unavailable, fall back to a Certificate Transparency lookup (crt.sh) directly so
discovery still returns something useful. Returns a deduplicated, sorted list.
"""

from __future__ import annotations

import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Cap to keep previews snappy and credits predictable.
MAX_SUBDOMAINS = 50


def _base_url() -> str:
    return f"http://{settings.kali_vm_host}:{settings.kali_vm_port}"


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    if settings.scanner_api_key:
        h["x-api-key"] = settings.scanner_api_key
    return h


async def _via_scanner(domain: str) -> list[str] | None:
    """Try the scanner's dedicated discovery endpoint. None if unavailable."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{_base_url()}/subdomain-discovery",
                json={"domain": domain, "api_key": settings.scanner_api_key},
                headers=_headers(),
            )
            if resp.status_code == 404:
                return None  # endpoint not deployed on this scanner
            resp.raise_for_status()
            data = resp.json()
            subs = data.get("subdomains") or data.get("hosts") or []
            return [str(s).strip().lower() for s in subs if s]
    except Exception as exc:  # noqa: BLE001 — discovery is best-effort
        logger.warning("scanner subdomain-discovery unavailable: %s", exc)
        return None


async def _via_crtsh(domain: str) -> list[str]:
    """Certificate Transparency fallback via crt.sh."""
    import httpx

    out: set[str] = set()
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                "https://crt.sh/", params={"q": f"%.{domain}", "output": "json"}
            )
            resp.raise_for_status()
            for row in resp.json():
                for name in str(row.get("name_value", "")).splitlines():
                    name = name.strip().lower().lstrip("*.")
                    if name.endswith(domain) and "@" not in name:
                        out.add(name)
    except Exception as exc:  # noqa: BLE001
        logger.warning("crt.sh lookup failed for %s: %s", domain, exc)
    return sorted(out)


async def discover_subdomains(domain: str) -> list[str]:
    """Return deduplicated live subdomains for a domain (best-effort)."""
    domain = (domain or "").strip().lower().lstrip("*.").rstrip("/")
    if not domain:
        return []

    found = await _via_scanner(domain)
    if found is None:
        found = await _via_crtsh(domain)

    # Always include the apex domain, dedupe, cap.
    result = sorted({domain, *found})
    return result[:MAX_SUBDOMAINS]
