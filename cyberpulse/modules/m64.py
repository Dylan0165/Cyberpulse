"""M64 — Kubernetes & Cloud-Native Exposure."""
import requests
import socket

class Scanner:
    name = "Kubernetes Exposure"
    phase = "reconnaissance"
    description = "Detect exposed Kubernetes dashboards, RBAC misconfigs, and cloud-native attack surfaces."

    def __init__(self, target, output_dir, config):
        self.target = target.split(":")[0]
        self.output_dir = output_dir
        self.config = config
        self.base = f"https://{self.target}"

    def run(self):
        findings, raw = [], []
        timeout = self.config.get("timeout", 8)

        # K8s API server endpoints
        k8s_api_paths = [
            ("/api", "K8s API root"),
            ("/api/v1/namespaces", "Namespaces list"),
            ("/api/v1/pods", "All pods"),
            ("/api/v1/secrets", "Secrets list"),
            ("/apis", "API groups"),
            ("/healthz", "Health endpoint"),
            ("/readyz", "Readiness endpoint"),
            ("/metrics", "Prometheus metrics"),
        ]

        for path, name in k8s_api_paths:
            for port in [443, 6443, 8443, 8080]:
                try:
                    proto = "https" if port != 8080 else "http"
                    url = f"{proto}://{self.target}:{port}{path}"
                    r = requests.get(url, timeout=3, verify=False)
                    raw.append(f"{name} {url}: {r.status_code}")
                    if r.status_code == 200:
                        findings.append({
                            "type": "k8s_exposed",
                            "detail": f"K8s API endpoint accessible without auth: {name} ({url})",
                            "severity": "critical",
                            "url": url,
                            "endpoint": path,
                        })
                    elif r.status_code == 401:
                        findings.append({
                            "type": "k8s_detected",
                            "detail": f"K8s API detected (authentication required): {url}",
                            "severity": "info",
                            "url": url,
                        })
                    break
                except Exception:
                    pass

        # Kubernetes Dashboard
        dashboard_paths = [
            "/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/",
            "/api/v1/namespaces/kube-system/services/https:kubernetes-dashboard:/proxy/",
        ]
        for path in dashboard_paths:
            try:
                r = requests.get(self.base + path, timeout=timeout, verify=False)
                raw.append(f"Dashboard {path}: {r.status_code}")
                if r.status_code == 200 and "kubernetes" in r.text.lower():
                    findings.append({
                        "type": "k8s_dashboard",
                        "detail": f"Kubernetes Dashboard accessible — potential unauthenticated admin access",
                        "severity": "critical",
                        "url": self.base + path,
                    })
            except Exception as e:
                raw.append(f"Dashboard probe {path}: {e}")

        # ETCD exposure (port 2379/2380)
        for port in [2379, 2380]:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                res = sock.connect_ex((self.target, port))
                sock.close()
                if res == 0:
                    findings.append({
                        "type": "etcd_exposed",
                        "detail": f"etcd port {port} open — Kubernetes cluster state/secrets may be accessible",
                        "severity": "critical",
                        "port": port,
                    })
                    raw.append(f"etcd port {port}: OPEN")
            except Exception as e:
                raw.append(f"etcd {port}: {e}")

        # Cloud metadata service (SSRF to internal)
        cloud_meta_urls = [
            "http://169.254.169.254/latest/meta-data/",  # AWS
            "http://metadata.google.internal/computeMetadata/v1/",  # GCP
            "http://169.254.169.254/metadata/instance",  # Azure
        ]
        ssrf_params = ["url", "endpoint", "proxy", "callback"]
        for meta_url in cloud_meta_urls:
            for param in ssrf_params:
                try:
                    r = requests.get(self.base, params={param: meta_url}, timeout=timeout, verify=False)
                    if "ami-id" in r.text or "instance-id" in r.text or "computeMetadata" in r.text:
                        findings.append({
                            "type": "cloud_ssrf",
                            "detail": f"SSRF to cloud metadata service via param '{param}' — cloud credentials may be exposed",
                            "severity": "critical",
                            "url": self.base,
                            "param": param,
                            "metadata_url": meta_url,
                        })
                except Exception:
                    pass

        if not findings:
            findings.append({"type": "info", "detail": "No Kubernetes or cloud-native exposure detected", "severity": "info"})

        return {"findings": findings, "raw_output": "\n".join(raw)}
