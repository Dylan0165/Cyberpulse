"""Scope Validator — ensures scans stay within authorized target boundaries.

Blocks metadata endpoints, cloud provider internals, and out-of-scope hosts.
Injected into module_runner.py to validate targets BEFORE execution.
"""

import ipaddress
import logging
import re
import socket
from urllib.parse import urlparse

logger = logging.getLogger("cyberpulse.engine.scope_validator")

# IP ranges that must ALWAYS be blocked
ALWAYS_BLOCKED = [
    # AWS metadata
    ipaddress.ip_network("169.254.169.254/32"),
    # Azure metadata
    ipaddress.ip_network("169.254.169.254/32"),
    # GCP metadata
    ipaddress.ip_network("169.254.169.254/32"),
    # Link-local
    ipaddress.ip_network("169.254.0.0/16"),
    # Loopback (don't scan yourself)
    ipaddress.ip_network("127.0.0.0/8"),
    # IPv6 loopback
    ipaddress.ip_network("::1/128"),
]

# Hostnames that must always be blocked
BLOCKED_HOSTNAMES = {
    "metadata.google.internal",
    "metadata.google.com",
    "169.254.169.254",
}


class ScopeValidator:
    """Validates that scan targets are within authorized scope."""

    def __init__(self, allowed_target: str, config: dict | None = None):
        """Initialize with the primary authorized target.

        Args:
            allowed_target: The target string provided by the user (URL, IP, domain).
            config: Optional config dict.
        """
        self.config = config or {}
        self.allowed_target = allowed_target
        self.allowed_host = self._extract_host(allowed_target)
        self.allowed_ips: set[str] = set()
        self.allowed_domains: set[str] = set()
        self.violations: list[dict] = []

        # Resolve the primary target
        self._resolve_allowed()

    def _extract_host(self, target: str) -> str:
        """Extract hostname from URL or plain target."""
        target = target.strip()
        if "://" in target:
            parsed = urlparse(target)
            return parsed.hostname or ""
        return target.split("/")[0].split(":")[0]

    def _resolve_allowed(self):
        """Resolve allowed target to IPs and domains."""
        host = self.allowed_host
        if not host:
            return

        self.allowed_domains.add(host.lower())

        # Also allow subdomains of the same base domain
        parts = host.split(".")
        if len(parts) >= 2:
            base_domain = ".".join(parts[-2:])
            self.allowed_domains.add(base_domain.lower())

        try:
            ip = socket.gethostbyname(host)
            self.allowed_ips.add(ip)
        except socket.gaierror:
            pass

    def validate(self, target: str) -> bool:
        """Check if a target is within scope.

        Returns True if the target is allowed, False if blocked.
        """
        host = self._extract_host(target)
        if not host:
            return False

        # Check blocked hostnames
        if host.lower() in BLOCKED_HOSTNAMES:
            self._log_violation(target, "Geblokkeerd hostname")
            return False

        # Check blocked IP ranges
        try:
            ip = ipaddress.ip_address(host)
            for blocked_net in ALWAYS_BLOCKED:
                if ip in blocked_net:
                    self._log_violation(target, f"Geblokkeerd IP bereik: {blocked_net}")
                    return False
        except ValueError:
            # Not an IP, resolve it
            try:
                resolved_ip = socket.gethostbyname(host)
                ip = ipaddress.ip_address(resolved_ip)
                for blocked_net in ALWAYS_BLOCKED:
                    if ip in blocked_net:
                        self._log_violation(target, f"Resolved naar geblokkeerd IP: {resolved_ip}")
                        return False
            except (socket.gaierror, ValueError):
                pass

        # Check if target matches allowed scope
        host_lower = host.lower()

        # Exact match or subdomain of allowed domain
        for allowed in self.allowed_domains:
            if host_lower == allowed or host_lower.endswith("." + allowed):
                return True

        # IP match
        try:
            resolved = socket.gethostbyname(host)
            if resolved in self.allowed_ips:
                return True
        except socket.gaierror:
            pass

        self._log_violation(target, "Buiten scope")
        return False

    def _log_violation(self, target: str, reason: str):
        """Log a scope violation."""
        violation = {
            "target": target,
            "reason": reason,
        }
        self.violations.append(violation)
        logger.warning("Scope violation: %s — %s", target, reason)

    def get_violations(self) -> list[dict]:
        """Return all recorded violations."""
        return self.violations
