"""M63 — Docker & Container Exposure Detection."""
import requests
import socket

class Scanner:
    name = "Docker & Container Exposure"
    phase = "reconnaissance"
    description = "Detect exposed Docker APIs, container management interfaces, and registry endpoints."

    def __init__(self, target, output_dir, config):
        self.target = target.split(":")[0]
        self.output_dir = output_dir
        self.config = config
        self.base = f"https://{self.target}"

    def run(self):
        findings, raw = [], []
        timeout = self.config.get("timeout", 8)

        # Docker API ports
        docker_ports = [2375, 2376, 2377, 4243, 4244]
        for port in docker_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((self.target, port))
                sock.close()
                raw.append(f"Docker port {port}: {'OPEN' if result == 0 else 'closed'}")
                if result == 0:
                    findings.append({
                        "type": "docker_exposed",
                        "detail": f"Docker API port {port} is open — potential unauthenticated container access",
                        "severity": "critical" if port == 2375 else "high",
                        "port": port,
                    })
                    # Try to access Docker API
                    try:
                        proto = "http" if port in (2375, 4243) else "https"
                        r = requests.get(f"{proto}://{self.target}:{port}/v1.41/version", timeout=3, verify=False)
                        if r.status_code == 200:
                            findings.append({
                                "type": "docker_unauthenticated",
                                "detail": f"Docker API accessible without authentication on port {port}",
                                "severity": "critical",
                                "port": port,
                                "version_info": r.text[:200],
                            })
                    except Exception:
                        pass
            except Exception as e:
                raw.append(f"Port {port} check error: {e}")

        # Kubernetes API ports
        k8s_ports = [6443, 8443, 10250, 10255, 8080]
        for port in k8s_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((self.target, port))
                sock.close()
                if result == 0:
                    raw.append(f"K8s port {port}: OPEN")
                    findings.append({
                        "type": "kubernetes_exposed",
                        "detail": f"Kubernetes API-related port {port} is open",
                        "severity": "high",
                        "port": port,
                    })
                    # Test /version endpoint
                    try:
                        r = requests.get(f"https://{self.target}:{port}/version", timeout=3, verify=False)
                        if r.status_code == 200:
                            findings.append({
                                "type": "kubernetes_unauthenticated",
                                "detail": f"Kubernetes API accessible on port {port} — check RBAC",
                                "severity": "critical",
                                "port": port,
                            })
                    except Exception:
                        pass
            except Exception as e:
                raw.append(f"K8s port {port}: {e}")

        # Container management UIs via web
        mgmt_paths = [
            ("/portainer", "Portainer"),
            ("/rancher", "Rancher"),
            ("/_dashboard", "Kubernetes Dashboard"),
            ("/k8s/", "Kubernetes"),
        ]
        for path, name in mgmt_paths:
            try:
                r = requests.get(self.base.rstrip("/") + path, timeout=timeout, verify=False)
                raw.append(f"{name} {path}: {r.status_code}")
                if r.status_code in (200, 301, 302):
                    findings.append({
                        "type": "container_mgmt",
                        "detail": f"Container management interface accessible: {name} at {path}",
                        "severity": "high",
                        "url": self.base + path,
                        "product": name,
                    })
            except Exception as e:
                raw.append(f"{name}: {e}")

        # Docker registry
        try:
            r = requests.get(f"{self.base}:5000/v2/", timeout=timeout, verify=False)
            raw.append(f"Registry /v2/: {r.status_code}")
            if r.status_code in (200, 401):
                severity = "critical" if r.status_code == 200 else "high"
                findings.append({
                    "type": "docker_registry",
                    "detail": f"Docker registry endpoint detected on port 5000 (status {r.status_code})",
                    "severity": severity,
                    "url": f"{self.base}:5000/v2/",
                })
        except Exception as e:
            raw.append(f"Registry probe: {e}")

        if not findings:
            findings.append({"type": "info", "detail": "No exposed container management APIs detected", "severity": "info"})

        return {"findings": findings, "raw_output": "\n".join(raw)}
