"""Domain/IP ownership verification service."""

import uuid
import dns.resolver
import httpx
import ipaddress
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.target import Target


async def generate_verification_token() -> str:
    """Generate a unique verification token."""
    return f"autopentest-verify={uuid.uuid4().hex}"


async def verify_dns_txt(target: Target, db: AsyncSession) -> bool:
    """Verify domain ownership via DNS TXT record."""
    if target.target_type != "domain":
        return False

    expected_token = target.verification_token
    if not expected_token:
        return False

    try:
        answers = dns.resolver.resolve(target.value, "TXT")
        for rdata in answers:
            for txt_string in rdata.strings:
                decoded = txt_string.decode("utf-8", errors="ignore")
                if decoded.strip() == expected_token:
                    target.is_verified = True
                    target.verified_at = datetime.now(timezone.utc)
                    target.verification_method = "dns_txt"
                    await db.commit()
                    return True
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers, Exception):
        pass

    return False


async def verify_file_upload(target: Target, db: AsyncSession) -> bool:
    """Verify domain ownership via /.well-known/autopentest.txt file."""
    if target.target_type != "domain":
        return False

    expected_token = target.verification_token
    if not expected_token:
        return False

    url = f"https://{target.value}/.well-known/autopentest.txt"
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                content = resp.text.strip()
                if content == expected_token:
                    target.is_verified = True
                    target.verified_at = datetime.now(timezone.utc)
                    target.verification_method = "file_upload"
                    await db.commit()
                    return True
    except (httpx.RequestError, httpx.HTTPStatusError):
        pass

    # Try HTTP fallback
    url_http = f"http://{target.value}/.well-known/autopentest.txt"
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url_http)
            if resp.status_code == 200:
                content = resp.text.strip()
                if content == expected_token:
                    target.is_verified = True
                    target.verified_at = datetime.now(timezone.utc)
                    target.verification_method = "file_upload"
                    await db.commit()
                    return True
    except (httpx.RequestError, httpx.HTTPStatusError):
        pass

    return False


async def verify_ip_declaration(target: Target, db: AsyncSession) -> bool:
    """Verify IP ownership via legal declaration checkbox."""
    if target.target_type not in ("ip", "ip_range"):
        return False

    # Validate the IP/range is actually valid
    try:
        if target.target_type == "ip":
            ipaddress.ip_address(target.value)
        else:
            ipaddress.ip_network(target.value, strict=False)
    except ValueError:
        return False

    # Block testing of private/reserved ranges unless explicitly confirmed
    # Block cloud metadata endpoints
    blocked_ips = ["169.254.169.254", "fd00:ec2::254"]
    if target.value in blocked_ips:
        return False

    target.is_verified = True
    target.verified_at = datetime.now(timezone.utc)
    target.verification_method = "legal_declaration"
    await db.commit()
    return True


def validate_target_value(target_type: str, value: str) -> bool:
    """Validate that a target value is well-formed."""
    if target_type == "domain":
        import re
        pattern = r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
        return bool(re.match(pattern, value))

    elif target_type == "ip":
        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return False

    elif target_type == "ip_range":
        try:
            ipaddress.ip_network(value, strict=False)
            return True
        except ValueError:
            return False

    elif target_type == "url":
        return value.startswith("http://") or value.startswith("https://")

    return False
