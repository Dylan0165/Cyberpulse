"""Docker-based scan orchestrator — spawns ephemeral containers for each scan."""

import json
import logging
from datetime import datetime, timezone

try:
    import docker
    from docker.errors import DockerException
except ImportError:
    docker = None  # type: ignore
    DockerException = Exception  # type: ignore

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_docker_client() -> "docker.DockerClient":
    if docker is None:
        raise RuntimeError("docker package is not installed. Scanner is unavailable in local dev mode.")
    return docker.from_env()


def create_scanner_network() -> None:
    """Create the isolated Docker network for scanner containers."""
    client = get_docker_client()
    try:
        client.networks.get(settings.scanner_network)
    except docker.errors.NotFound:
        client.networks.create(
            settings.scanner_network,
            driver="bridge",
            internal=False,  # Needs outbound access to targets
            labels={"autopentest": "scanner-network"},
        )
        logger.info(f"Created scanner network: {settings.scanner_network}")


def launch_scan_container(
    scan_id: str,
    scan_config: dict,
    phase: str,
) -> str:
    """
    Launch an ephemeral Docker container for a scan phase.
    Returns the container ID.
    """
    client = get_docker_client()

    # Ensure network exists
    create_scanner_network()

    env_vars = {
        "SCAN_ID": scan_id,
        "SCAN_CONFIG": json.dumps(scan_config),
        "SCAN_PHASE": phase,
        "REDIS_URL": settings.redis_url,
        "REDIS_HOST": "redis",
        "SHODAN_API_KEY": settings.shodan_api_key or "",
        "HAVEIBEENPWNED_API_KEY": settings.haveibeenpwned_api_key or "",
    }

    container = client.containers.run(
        image=settings.scanner_image,
        environment=env_vars,
        network=settings.scanner_network,
        mem_limit=settings.scan_container_memory_limit,
        nano_cpus=int(settings.scan_container_cpu_limit * 1e9),
        detach=True,
        auto_remove=True,  # Ephemeral — destroyed after exit
        labels={
            "autopentest.scan_id": scan_id,
            "autopentest.phase": phase,
            "autopentest": "scanner",
        },
        cap_add=["NET_ADMIN"],  # Needed for iptables scope enforcement
        read_only=False,
        tmpfs={"/tmp": "size=500M"},
    )

    logger.info(f"Launched scanner container {container.short_id} for scan {scan_id} phase {phase}")
    return container.id


def stop_scan_container(container_id: str) -> None:
    """Stop and remove a scanner container."""
    client = get_docker_client()
    try:
        container = client.containers.get(container_id)
        container.stop(timeout=10)
        logger.info(f"Stopped scanner container {container_id[:12]}")
    except docker.errors.NotFound:
        logger.warning(f"Container {container_id[:12]} already removed")
    except DockerException as e:
        logger.error(f"Error stopping container {container_id[:12]}: {e}")


def get_container_status(container_id: str) -> str:
    """Get the status of a scanner container."""
    client = get_docker_client()
    try:
        container = client.containers.get(container_id)
        return container.status
    except docker.errors.NotFound:
        return "removed"
    except DockerException:
        return "unknown"


def get_container_logs(container_id: str, tail: int = 100) -> str:
    """Get recent logs from a scanner container."""
    client = get_docker_client()
    try:
        container = client.containers.get(container_id)
        return container.logs(tail=tail).decode("utf-8", errors="replace")
    except docker.errors.NotFound:
        return ""
    except DockerException:
        return ""


def cleanup_stale_containers(max_age_seconds: int = 28800) -> int:
    """Remove any scanner containers older than max_age_seconds."""
    client = get_docker_client()
    removed = 0
    try:
        containers = client.containers.list(
            filters={"label": "autopentest=scanner"},
        )
        for container in containers:
            created = container.attrs.get("Created", "")
            if created:
                # Docker returns ISO format timestamp
                try:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    age = (datetime.now(timezone.utc) - created_dt).total_seconds()
                    if age > max_age_seconds:
                        container.stop(timeout=5)
                        removed += 1
                        logger.info(f"Cleaned up stale container {container.short_id} (age: {age:.0f}s)")
                except (ValueError, TypeError):
                    pass
    except DockerException as e:
        logger.error(f"Error during cleanup: {e}")

    return removed
