"""M69 — Dependency Confusion Attack Vector Detection."""
import requests
import re
import json

class Scanner:
    name = "Dependency Confusion"
    phase = "reconnaissance"
    description = "Detect exposed package manifests that could enable dependency confusion attacks."

    def __init__(self, target, output_dir, config):
        self.target = target
        self.output_dir = output_dir
        self.config = config
        self.base = f"https://{target}" if not target.startswith("http") else target

    def run(self):
        findings, raw = [], []
        timeout = self.config.get("timeout", 10)

        # Package manifest files to check
        manifest_paths = [
            ("/package.json",           "npm/Node.js"),
            ("/package-lock.json",      "npm lockfile (internal deps)"),
            ("/yarn.lock",              "Yarn lockfile"),
            ("/requirements.txt",       "Python pip"),
            ("/Pipfile",                "Python Pipenv"),
            ("/Pipfile.lock",           "Python Pipenv lockfile"),
            ("/poetry.lock",            "Python Poetry lockfile"),
            ("/setup.py",               "Python setup.py"),
            ("/pom.xml",                "Java Maven"),
            ("/build.gradle",           "Java Gradle"),
            ("/build.gradle.kts",       "Kotlin Gradle"),
            ("/composer.json",          "PHP Composer"),
            ("/composer.lock",          "PHP Composer lockfile"),
            ("/Gemfile",                "Ruby Gems"),
            ("/Gemfile.lock",           "Ruby Gems lockfile"),
            ("/go.mod",                 "Go modules"),
            ("/go.sum",                 "Go modules checksum"),
            ("/Cargo.toml",             "Rust Cargo"),
            ("/pubspec.yaml",           "Dart/Flutter"),
            ("/.npmrc",                 "npm config (may reveal private registry)"),
            ("/nuget.config",           "NuGet config (may reveal private feed)"),
        ]

        exposed_manifests = []

        for path, pkg_system in manifest_paths:
            url = self.base.rstrip("/") + path
            try:
                r = requests.get(url, timeout=timeout, verify=False, allow_redirects=False)
                if r.status_code == 200 and len(r.text) > 10:
                    exposed_manifests.append((path, pkg_system, r.text))
                    raw.append(f"EXPOSED {url}")
                    findings.append({
                        "type": "manifest_exposed",
                        "detail": f"Package manifest exposed: {path} ({pkg_system})",
                        "severity": "medium",
                        "path": path,
                        "pkg_system": pkg_system,
                    })
            except Exception:
                pass

        # Analyze package.json for internal/scoped packages
        for path, pkg_system, content in exposed_manifests:
            if path == "/package.json":
                try:
                    data = json.loads(content)
                    deps = {}
                    deps.update(data.get("dependencies", {}))
                    deps.update(data.get("devDependencies", {}))

                    # Scoped private packages (@company/...) are high-risk for dependency confusion
                    scoped = [name for name in deps if name.startswith("@") and "/" in name]
                    if scoped:
                        findings.append({
                            "type": "dependency_confusion",
                            "detail": f"Scoped npm packages found ({len(scoped)}): {', '.join(scoped[:5])} — vulnerable to dependency confusion if published to public registry",
                            "severity": "high",
                            "packages": scoped,
                        })
                except json.JSONDecodeError:
                    pass

            # Check requirements.txt for internal package names (heuristic)
            if path == "/requirements.txt":
                lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("#")]
                # Internal packages often have no version pin or company prefixes
                unpinned = [l for l in lines if "==" not in l and not l.startswith("-")]
                if unpinned:
                    findings.append({
                        "type": "dependency_confusion",
                        "detail": f"Python packages without version pin ({len(unpinned)}): {', '.join(unpinned[:5])} — dependency confusion risk",
                        "severity": "medium",
                        "packages": unpinned,
                    })

        # Check for private registry configuration exposure
        registry_paths = ["/.npmrc", "/nuget.config", "/.pypirc", "/pip.conf"]
        for path in registry_paths:
            url = self.base.rstrip("/") + path
            try:
                r = requests.get(url, timeout=timeout, verify=False, allow_redirects=False)
                if r.status_code == 200:
                    content_l = r.text.lower()
                    if any(k in content_l for k in ["registry", "token", "password", "auth", "feed"]):
                        findings.append({
                            "type": "registry_config_exposed",
                            "detail": f"Registry config file exposed: {path} — may reveal private registry URL or credentials",
                            "severity": "high",
                            "path": path,
                        })
                        raw.append(f"CRITICAL registry config: {url}")
            except Exception:
                pass

        if not findings:
            findings.append({"type": "info", "detail": "No package manifests or registry configs exposed", "severity": "info"})

        return {"findings": findings, "raw_output": "\n".join(raw)}
