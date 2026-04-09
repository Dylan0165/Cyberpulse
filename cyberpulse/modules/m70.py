"""M70 — Attack Chain Simulation & Kill-Chain Analysis."""
import json
import os
import glob

class Scanner:
    name = "Attack Chain Simulation"
    phase = "reporting"
    description = "Synthesize all module findings into attack chains and kill-chain paths."

    def __init__(self, target, output_dir, config):
        self.target = target
        self.output_dir = output_dir
        self.config = config

    def _load_findings(self):
        """Load all JSON result files from the output directory."""
        all_findings = {}
        pattern = os.path.join(self.output_dir, "m*.json")
        for fpath in sorted(glob.glob(pattern)):
            mname = os.path.basename(fpath)
            try:
                with open(fpath) as f:
                    data = json.load(f)
                all_findings[mname] = data.get("findings", [])
            except Exception:
                pass
        return all_findings

    def _classify(self, all_findings):
        """Map findings to MITRE ATT&CK-like categories."""
        classes = {
            "recon": [],
            "initial_access": [],
            "persistence": [],
            "privilege_escalation": [],
            "lateral_movement": [],
            "exfiltration": [],
            "impact": [],
        }

        recon_types = {"subdomain", "dns", "port_open", "technology_stack", "certificate", "threat_intel"}
        access_types = {"sqli", "xss", "ssti", "rce", "rfi", "lfi", "open_redirect", "deserialization",
                        "http_smuggling", "prototype_pollution", "cache_poisoning"}
        persistence_types = {"admin_panel", "default_credentials", "auth_bypass", "jwt_exposure"}
        privesc_types = {"docker_exposed", "k8s_exposed", "idor", "broken_access"}
        exfil_types = {"api_exposure", "manifest_exposed", "env_file_exposed", "registry_config_exposed",
                       "secret_exposure", "ci_secret_exposure"}
        impact_types = {"ssl_expired", "cors_wildcard", "csrf", "clickjacking"}

        for module, findings in all_findings.items():
            for f in findings:
                ftype = f.get("type", "")
                sev = f.get("severity", "info")
                if sev == "info":
                    continue
                entry = {"module": module, "finding": f.get("detail", ""), "severity": sev}
                if ftype in recon_types:
                    classes["recon"].append(entry)
                elif ftype in access_types:
                    classes["initial_access"].append(entry)
                elif ftype in persistence_types:
                    classes["persistence"].append(entry)
                elif ftype in privesc_types:
                    classes["privilege_escalation"].append(entry)
                elif ftype in exfil_types:
                    classes["exfiltration"].append(entry)
                elif ftype in impact_types:
                    classes["impact"].append(entry)
                else:
                    # Default classification based on severity
                    if sev in ("critical", "high"):
                        classes["initial_access"].append(entry)
                    else:
                        classes["recon"].append(entry)

        return classes

    def _build_chains(self, classified):
        """Build realistic attack chains from classified findings."""
        chains = []

        # Chain 1: Reconnaissance → Exploitation
        if classified["recon"] and classified["initial_access"]:
            chains.append({
                "chain_id": "AC-01",
                "name": "Recon-to-Exploitation",
                "description": "Attacker uses reconnaissance data to identify and exploit a vulnerability.",
                "steps": [
                    classified["recon"][0],
                    classified["initial_access"][0],
                ],
                "risk": "critical",
            })

        # Chain 2: Exposure → Data Exfiltration
        if classified["exfiltration"]:
            entry = classified["exfiltration"][0]
            chain = {
                "chain_id": "AC-02",
                "name": "Exposure-to-Exfiltration",
                "description": "Exposed configuration or manifest allows attacker to exfiltrate secrets.",
                "steps": [entry],
                "risk": entry["severity"],
            }
            if classified["recon"]:
                chain["steps"].insert(0, classified["recon"][0])
            chains.append(chain)

        # Chain 3: Initial Access → Privilege Escalation
        if classified["initial_access"] and classified["privilege_escalation"]:
            chains.append({
                "chain_id": "AC-03",
                "name": "Access-to-PrivEsc",
                "description": "Initial foothold leads to privilege escalation via container or IDOR.",
                "steps": [
                    classified["initial_access"][0],
                    classified["privilege_escalation"][0],
                ],
                "risk": "critical",
            })

        # Chain 4: Impact chain
        if classified["impact"]:
            chains.append({
                "chain_id": "AC-04",
                "name": "Direct-Impact",
                "description": "Vulnerability with direct end-user or data impact.",
                "steps": classified["impact"][:2],
                "risk": classified["impact"][0]["severity"],
            })

        return chains

    def run(self):
        findings, raw = [], []

        all_module_findings = self._load_findings()
        raw.append(f"Loaded results from {len(all_module_findings)} modules")

        if not all_module_findings:
            return {
                "findings": [{"type": "info", "detail": "No prior module results found — run other modules first", "severity": "info"}],
                "raw_output": "No module JSON files found in output directory",
            }

        classified = self._classify(all_module_findings)
        total_non_info = sum(len(v) for v in classified.values())
        raw.append(f"Total actionable findings: {total_non_info}")
        for cat, items in classified.items():
            if items:
                raw.append(f"  {cat}: {len(items)} findings")

        chains = self._build_chains(classified)
        raw.append(f"Attack chains identified: {len(chains)}")

        for chain in chains:
            steps_desc = " → ".join(s.get("finding", "")[:60] for s in chain["steps"])
            findings.append({
                "type": "attack_chain",
                "detail": f"[{chain['chain_id']}] {chain['name']}: {steps_desc}",
                "severity": chain["risk"],
                "chain_id": chain["chain_id"],
                "chain_name": chain["name"],
                "steps": chain["steps"],
            })

        # Overall risk summary
        sev_counts = {}
        for mod_findings in all_module_findings.values():
            for f in mod_findings:
                s = f.get("severity", "info")
                sev_counts[s] = sev_counts.get(s, 0) + 1

        findings.append({
            "type": "summary",
            "detail": f"Risk summary — Critical: {sev_counts.get('critical', 0)}, High: {sev_counts.get('high', 0)}, Medium: {sev_counts.get('medium', 0)}, Low: {sev_counts.get('low', 0)}",
            "severity": "info",
            "counts": sev_counts,
        })

        if not chains:
            findings.append({"type": "info", "detail": "No multi-step attack chains could be constructed from available findings", "severity": "info"})

        return {"findings": findings, "raw_output": "\n".join(raw)}
