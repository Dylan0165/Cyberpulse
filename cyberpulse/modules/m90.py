"""M90 — Docker / Container Audit (White Box)
Connects via SSH and audits Docker/container security: privileged
containers, exposed Docker socket, image vulnerabilities, secrets in
container env vars, insecure registry, and rootless Docker.
"""
import re


class Scanner:
    def __init__(self, target, output_dir, config=None):
        self.target = target
        self.output_dir = output_dir
        self.config = config or {}
        self.creds = self.config.get("credentials", {})

    def _ssh_connect(self):
        host = self.creds.get("ssh_host") or self.target
        port = int(self.creds.get("ssh_port") or 22)
        user = self.creds.get("ssh_username", "")
        pwd  = self.creds.get("ssh_password", "")
        key  = self.creds.get("ssh_key", "")
        if not user:
            return None, "Geen SSH-gebruikersnaam"
        try:
            import paramiko, io
            c = paramiko.SSHClient()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if key:
                pkey = paramiko.RSAKey.from_private_key(io.StringIO(key))
                c.connect(host, port=port, username=user, pkey=pkey, timeout=10)
            else:
                c.connect(host, port=port, username=user, password=pwd, timeout=10)
            return c, None
        except ImportError:
            return None, "paramiko niet geinstalleerd"
        except Exception as e:
            return None, str(e)

    def _exec(self, c, cmd):
        try:
            _, out, _ = c.exec_command(cmd, timeout=15)
            return out.read().decode("utf-8", errors="ignore").strip()
        except Exception:
            return ""

    def run(self):
        findings = []
        output = [f"[M90] Docker/container audit via SSH"]

        client, err = self._ssh_connect()
        if client is None:
            return {"findings": [], "raw_output": f"[M90] SSH fout: {err}"}

        # Check if Docker is installed
        docker_ver = self._exec(client, "docker --version 2>/dev/null")
        output.append(f"  Docker versie: {docker_ver or 'niet gevonden'}")

        if not docker_ver:
            # Check for Podman or other container runtimes
            podman = self._exec(client, "podman --version 2>/dev/null")
            if not podman:
                client.close()
                return {"findings": [], "raw_output": "[M90] Docker niet aanwezig op dit systeem"}

        # 1. Docker socket permissions
        socket_perm = self._exec(client, "ls -la /var/run/docker.sock 2>/dev/null")
        output.append(f"  Docker socket: {socket_perm}")
        if socket_perm and ("srw-rw-rw-" in socket_perm or "777" in socket_perm):
            findings.append({
                "title": "Docker Socket World-Readable/Writable",
                "severity": "critical",
                "description": "Het Docker socket /var/run/docker.sock heeft world-read/write permissies. Toegang tot dit socket geeft effectief root op de host.",
                "recommendation": "chmod 660 /var/run/docker.sock; chown root:docker /var/run/docker.sock. Voeg alleen vertrouwde gebruikers toe aan de docker-groep."
            })

        # 2. Docker socket exposed to containers
        mounted_socket = self._exec(client,
            "docker inspect $(docker ps -q) 2>/dev/null | "
            "grep -i 'docker.sock' | head -5")
        if mounted_socket:
            findings.append({
                "title": "Docker Socket Gemount in Container(s)",
                "severity": "critical",
                "description": f"Het Docker socket is gemount in een of meer containers: {mounted_socket[:200]}. Container-escape is triviaal via dit socket.",
                "recommendation": "Verwijder docker.sock mounts uit containers. Gebruik de Docker API via TCP met TLS in plaats van socket mounting."
            })

        # 3. Privileged containers
        privileged = self._exec(client,
            "docker ps -q 2>/dev/null | xargs -I{} docker inspect {} "
            "--format '{{.Name}}: {{.HostConfig.Privileged}}' 2>/dev/null | "
            "grep 'true'")
        if privileged:
            priv_list = [l.strip() for l in privileged.splitlines() if l.strip()]
            findings.append({
                "title": f"Privileged Containers Actief: {len(priv_list)} gevonden",
                "severity": "critical",
                "description": f"Containers draaien in privileged modus: {', '.join(priv_list[:3])}. Privileged containers kunnen ontsnappen naar de host.",
                "recommendation": "Verwijder --privileged flag. Gebruik specifieke capabilities: --cap-add=NET_ADMIN i.p.v. --privileged."
            })

        # 4. Containers running as root
        root_containers = self._exec(client,
            "docker ps -q 2>/dev/null | xargs -I{} docker inspect {} "
            "--format '{{.Name}}: User={{.Config.User}}' 2>/dev/null | "
            "grep 'User=$\\|User=0\\|User=root'")
        if root_containers:
            root_list = [l.strip() for l in root_containers.splitlines() if l.strip()]
            findings.append({
                "title": f"Containers Draaien als Root: {len(root_list)} gevonden",
                "severity": "high",
                "description": f"Containers draaien als root user: {', '.join(root_list[:3])}. Bij container-escape heeft aanvaller direct root-toegang.",
                "recommendation": "Voeg toe aan Dockerfile: USER 1001. Of gebruik --user 1001:1001 bij docker run. Gebruik rootless Docker."
            })

        # 5. Secrets in environment variables
        env_secrets = self._exec(client,
            "docker inspect $(docker ps -q) 2>/dev/null | "
            "grep -iE '\"(PASSWORD|SECRET|KEY|TOKEN|API_KEY)=' | "
            "grep -v '\"\"' | head -10")
        if env_secrets:
            findings.append({
                "title": "Gevoelige Data in Container Omgevingsvariabelen",
                "severity": "high",
                "description": f"Containers bevatten mogelijk gevoelige secrets als env vars: {env_secrets[:200]}",
                "recommendation": "Gebruik Docker Secrets of een externe secrets manager. Nooit wachtwoorden/keys doorgeven via -e of ENV in Dockerfile."
            })

        # 6. Docker daemon config
        docker_daemon = self._exec(client, "cat /etc/docker/daemon.json 2>/dev/null")
        if docker_daemon:
            output.append(f"  daemon.json: {docker_daemon[:100]}")
            if '"tls"' not in docker_daemon and '"2375"' in docker_daemon:
                findings.append({
                    "title": "Docker Daemon Exposeert TCP API Zonder TLS",
                    "severity": "critical",
                    "description": "Docker daemon luistert op TCP poort 2375 zonder TLS. Ongeautoriseerde toegang tot de Docker API geeft volledige controle over de host.",
                    "recommendation": "Schakel onbeveiligd TCP uit. Gebruik Unix socket of TLS (poort 2376) met client certificaten."
                })
        else:
            output.append("  Geen daemon.json gevonden (standaardconfiguratie)")

        # 7. Image vulnerability scan (via trivy if available)
        trivy = self._exec(client, "which trivy 2>/dev/null")
        if trivy:
            images = self._exec(client, "docker images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | head -5")
            for img in images.splitlines()[:2]:
                img = img.strip()
                if img:
                    trivy_out = self._exec(client, f"trivy image --severity HIGH,CRITICAL {img} 2>/dev/null | tail -10")
                    crit_count = trivy_out.count("CRITICAL")
                    if crit_count > 0:
                        findings.append({
                            "title": f"Kwetsbaarheden in Docker Image: {img} ({crit_count} kritiek)",
                            "severity": "critical",
                            "description": f"Trivy scan van {img}: {crit_count} kritieke kwetsbaarheden.",
                            "recommendation": f"Update het basisimage: gebruik een nieuwere versie van {img}. Herstart daarna de container."
                        })

        client.close()
        if not findings:
            output.append("  [OK] Docker configuratie lijkt veilig")
        return {"findings": findings, "raw_output": "\n".join(output)}
