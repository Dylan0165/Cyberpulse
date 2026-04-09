"""M68 — CI/CD Pipeline & Build System Exposure."""
import requests

class Scanner:
    name = "CI/CD Pipeline Exposure"
    phase = "reconnaissance"
    description = "Detect exposed CI/CD pipelines, build configs, and DevOps artifacts."

    def __init__(self, target, output_dir, config):
        self.target = target
        self.output_dir = output_dir
        self.config = config
        self.base = f"https://{target}" if not target.startswith("http") else target

    def run(self):
        findings, raw = [], []
        timeout = self.config.get("timeout", 10)

        # CI/CD config files and pages
        ci_paths = [
            # Config files
            ("/.github/workflows/ci.yml",       "GitHub Actions workflow (YAML)"),
            ("/.github/workflows/deploy.yml",    "GitHub Actions deploy workflow"),
            ("/.github/workflows/main.yml",      "GitHub Actions main workflow"),
            ("/Jenkinsfile",                     "Jenkins pipeline definition"),
            ("/.gitlab-ci.yml",                  "GitLab CI/CD pipeline config"),
            ("/.travis.yml",                     "Travis CI configuration"),
            ("/.circleci/config.yml",            "CircleCI configuration"),
            ("/bitbucket-pipelines.yml",         "Bitbucket Pipelines config"),
            ("/azure-pipelines.yml",             "Azure DevOps Pipelines config"),
            ("/Makefile",                        "Makefile (may expose build targets)"),
            ("/Dockerfile",                      "Dockerfile exposed"),
            ("/docker-compose.yml",              "Docker Compose file exposed"),
            ("/docker-compose.prod.yml",         "Production Docker Compose exposed"),
            ("/.env.example",                    ".env.example (may leak env var names)"),
            ("/deploy.sh",                       "Deployment shell script exposed"),
            ("/build.sh",                        "Build shell script exposed"),
            # CI server UIs
            ("/jenkins",                         "Jenkins UI"),
            ("/jenkins/api/json",                "Jenkins API"),
            ("/:8080",                           "Jenkins default port path"),
            ("/blue/rest/organizations/jenkins", "Jenkins Blue Ocean API"),
            ("/builds",                          "Build listing page"),
            ("/pipelines",                       "Pipeline listing page"),
            ("/ci",                              "Generic CI page"),
            # Artifact endpoints
            ("/artifacts",                       "Build artifacts"),
            ("/.buildinfo",                      "Build info file"),
            ("/build/reports",                   "Build reports"),
        ]

        for path, description in ci_paths:
            url = self.base.rstrip("/") + path
            try:
                r = requests.get(url, timeout=timeout, verify=False, allow_redirects=False)
                if r.status_code not in (404, 410):
                    severity = "high" if r.status_code == 200 else "low"
                    # Elevate severity for secrets-bearing files
                    secret_keywords = ["password", "secret", "token", "credentials", "aws_access", "private_key"]
                    if any(k in r.text.lower() for k in secret_keywords):
                        severity = "critical"
                        findings.append({
                            "type": "ci_secret_exposure",
                            "detail": f"CI/CD config with potential secrets: {path} — {description}",
                            "severity": "critical",
                            "path": path,
                        })
                    else:
                        findings.append({
                            "type": "ci_exposure",
                            "detail": f"Accessible CI/CD resource: {path} (HTTP {r.status_code}) — {description}",
                            "severity": severity,
                            "path": path,
                            "status_code": r.status_code,
                        })
                    raw.append(f"{r.status_code} {url}")
            except Exception as e:
                raw.append(f"ERR {url}: {e}")

        # Environment file exposure
        env_paths = ["/.env", "/.env.local", "/.env.production", "/.env.staging", "/config/.env"]
        for path in env_paths:
            url = self.base.rstrip("/") + path
            try:
                r = requests.get(url, timeout=timeout, verify=False, allow_redirects=False)
                if r.status_code == 200 and ("=" in r.text or "KEY" in r.text.upper()):
                    findings.append({
                        "type": "env_file_exposed",
                        "detail": f"Environment file exposed: {path} — may contain secrets",
                        "severity": "critical",
                        "path": path,
                    })
                    raw.append(f"CRITICAL .env exposed: {url}")
            except Exception:
                pass

        if not findings:
            findings.append({"type": "info", "detail": "No CI/CD pipeline artifacts exposed", "severity": "info"})

        return {"findings": findings, "raw_output": "\n".join(raw)}
