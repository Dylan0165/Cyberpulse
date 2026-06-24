"""TargetParser — auto-detect the type of a scan target.

Recognises CIDR networks, IP ranges (1.2.3.50-100), wildcard domains
(*.example.com / example.com/*) and falls back to a single host/domain.
Pure logic, no I/O — safe to unit test and call from request handlers.
"""

from __future__ import annotations

import ipaddress
import re

# Hard cap on hosts expanded from a CIDR/range so a /16 can't blow up memory.
MAX_HOSTS = 254

_RANGE_RE = re.compile(r"^(\d{1,3}\.\d{1,3}\.\d{1,3})\.(\d{1,3})-(\d{1,3})$")


class TargetParser:
    @staticmethod
    def parse(input_str: str) -> dict:
        """Return {type, ...} describing the target. type is one of
        'cidr' | 'range' | 'domain_with_subs' | 'single'."""
        input_str = (input_str or "").strip()

        # CIDR notation: 192.168.1.0/24 (also accepts a bare IP as /32).
        if "/" in input_str and not input_str.endswith("/*"):
            try:
                network = ipaddress.ip_network(input_str, strict=False)
                hosts = list(network.hosts())
                # A /32 or /31 has no "hosts"; treat the network address itself.
                if not hosts:
                    hosts = [network.network_address]
                return {
                    "type": "cidr",
                    "network": str(network),
                    "estimated_hosts": len(hosts),
                    "hosts": [str(h) for h in hosts[:MAX_HOSTS]],
                }
            except ValueError:
                pass

        # IP range: 192.168.1.50-100
        m = _RANGE_RE.match(input_str)
        if m:
            base, start, end = m.group(1), int(m.group(2)), int(m.group(3))
            if 0 <= start <= 255 and 0 <= end <= 255 and start <= end:
                hosts = [f"{base}.{i}" for i in range(start, end + 1)]
                return {
                    "type": "range",
                    "range_start": f"{base}.{start}",
                    "range_end": f"{base}.{end}",
                    "estimated_hosts": len(hosts),
                    "hosts": hosts[:MAX_HOSTS],
                }

        # Wildcard domain → subdomain discovery.
        if input_str.startswith("*.") or input_str.endswith("/*"):
            domain = input_str.replace("*.", "").replace("/*", "").strip("/")
            return {
                "type": "domain_with_subs",
                "domain": domain,
                "estimated_hosts": "onbekend (discovery vereist)",
            }

        # Single IP or domain — existing behaviour.
        return {"type": "single", "value": input_str, "estimated_hosts": 1}

    @staticmethod
    def credits_for_hosts(alive_count: int) -> int:
        """Credits required for a multi-host scan.

        Tiered for the common subnet sizes, otherwise ceil(hosts / 5)."""
        if alive_count <= 0:
            return 0
        if alive_count <= 6:    # /29
            return 3
        if alive_count <= 14:   # /28
            return 5
        if alive_count <= 254:  # /24 and below
            return 10
        return -(-alive_count // 5)  # ceil division
