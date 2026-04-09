"""Module 23 — GraphQL Endpoint Testing.

Discovers and tests GraphQL endpoints for introspection exposure,
query depth abuse, batching attacks, and information disclosure.
"""

import json
import logging
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m23")

GRAPHQL_PATHS = [
    "/graphql", "/graphiql", "/gql", "/api/graphql", "/api/gql",
    "/v1/graphql", "/v2/graphql", "/query", "/api/query",
    "/graphql/console", "/playground",
]

INTROSPECTION_QUERY = """
{
  __schema {
    types {
      name
      kind
      fields {
        name
        type { name kind }
      }
    }
    queryType { name }
    mutationType { name }
    subscriptionType { name }
  }
}
"""

DEPTH_QUERY = """
{
  __schema {
    types {
      fields {
        type {
          fields {
            type {
              fields {
                type { name }
              }
            }
          }
        }
      }
    }
  }
}
"""


class Scanner:
    name = "GraphQL Testing"
    phase = "scanning"
    description = "Tests GraphQL endpoints for introspection, depth attacks, and misconfigurations"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 CyberPulse/1.0",
            "Content-Type": "application/json",
        })
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"GraphQL endpoint testing for {self.target}"]

        base_url = self._get_base_url()

        # Phase 1: Discover GraphQL endpoints
        raw_lines.append("\n[Phase 1: Endpoint Discovery]")
        live_endpoints = []
        for path in GRAPHQL_PATHS:
            url = base_url + path
            try:
                resp = self.session.post(url, json={"query": "{__typename}"}, timeout=10)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        if "data" in data or "errors" in data:
                            live_endpoints.append(path)
                            raw_lines.append(f"  FOUND: {path}")
                    except ValueError:
                        pass
                elif resp.status_code == 400:
                    # GraphQL often returns 400 for bad queries
                    try:
                        data = resp.json()
                        if "errors" in data:
                            live_endpoints.append(path)
                            raw_lines.append(f"  FOUND (400): {path}")
                    except ValueError:
                        pass
            except Exception:
                continue

        if not live_endpoints:
            raw_lines.append("  No GraphQL endpoints found")
            findings.append({
                "type": "no_graphql",
                "detail": "No GraphQL endpoints detected",
                "severity": "info",
            })
        else:
            findings.append({
                "type": "graphql_endpoints",
                "endpoints": live_endpoints,
                "detail": f"Found {len(live_endpoints)} GraphQL endpoint(s): {', '.join(live_endpoints)}",
                "severity": "info",
            })

        # Phase 2: Test each live endpoint
        for ep in live_endpoints:
            url = base_url + ep
            raw_lines.append(f"\n[Phase 2: Testing {ep}]")

            # Test introspection
            raw_lines.append("  [Introspection]")
            try:
                resp = self.session.post(url, json={"query": INTROSPECTION_QUERY}, timeout=15)
                data = resp.json()
                if "data" in data and data["data"].get("__schema"):
                    schema = data["data"]["__schema"]
                    type_count = len(schema.get("types", []))
                    has_mutations = schema.get("mutationType") is not None
                    raw_lines.append(f"    EXPOSED! {type_count} types, mutations: {has_mutations}")

                    findings.append({
                        "type": "graphql_introspection",
                        "endpoint": ep,
                        "type_count": type_count,
                        "has_mutations": has_mutations,
                        "detail": f"Introspection enabled on {ep} — exposes {type_count} types",
                        "severity": "high",
                    })

                    # Extract sensitive type names
                    sensitive_types = []
                    for t in schema.get("types", []):
                        name = t.get("name", "").lower()
                        for kw in ["user", "admin", "password", "token", "secret",
                                    "auth", "credential", "payment", "billing"]:
                            if kw in name and not name.startswith("__"):
                                sensitive_types.append(t.get("name"))
                                break

                    if sensitive_types:
                        raw_lines.append(f"    Sensitive types: {', '.join(sensitive_types)}")
                        findings.append({
                            "type": "graphql_sensitive_types",
                            "endpoint": ep,
                            "types": sensitive_types,
                            "detail": f"Sensitive data types exposed: {', '.join(sensitive_types)}",
                            "severity": "high",
                        })
                else:
                    raw_lines.append("    Introspection disabled or restricted")
            except Exception as e:
                raw_lines.append(f"    Error: {e}")

            # Test query depth limit
            raw_lines.append("  [Depth Limit]")
            try:
                resp = self.session.post(url, json={"query": DEPTH_QUERY}, timeout=10)
                data = resp.json()
                if "data" in data:
                    raw_lines.append("    No depth limit — DoS risk via deep queries!")
                    findings.append({
                        "type": "graphql_no_depth_limit",
                        "endpoint": ep,
                        "detail": f"No query depth limit on {ep} — potential DoS vector",
                        "severity": "medium",
                    })
                elif "errors" in data:
                    raw_lines.append("    Depth limit enforced")
            except Exception:
                pass

            # Test batching
            raw_lines.append("  [Batch Query]")
            try:
                batch = [{"query": "{__typename}"} for _ in range(10)]
                resp = self.session.post(url, json=batch, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) == 10:
                        raw_lines.append("    Batching allowed — brute force amplification risk")
                        findings.append({
                            "type": "graphql_batching",
                            "endpoint": ep,
                            "detail": f"Query batching enabled on {ep} — amplification risk",
                            "severity": "medium",
                        })
            except Exception:
                pass

            # Test for debug/verbose errors
            raw_lines.append("  [Error Verbosity]")
            try:
                resp = self.session.post(url, json={"query": "{ invalidField }"}, timeout=10)
                data = resp.json()
                errors = data.get("errors", [])
                if errors:
                    error_text = json.dumps(errors)
                    if any(kw in error_text.lower() for kw in ["stack", "trace", "internal",
                                                                  "debug", "sql", "postgres"]):
                        raw_lines.append("    Verbose error messages — information disclosure!")
                        findings.append({
                            "type": "graphql_verbose_errors",
                            "endpoint": ep,
                            "detail": "GraphQL returns verbose error messages with internal details",
                            "severity": "medium",
                        })
            except Exception:
                pass

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "23_graphql.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("GraphQL scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
