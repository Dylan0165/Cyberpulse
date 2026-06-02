"""
ToolRunner — synchronous client for the Kali VM scanner API.

Runs on the Ubuntu backend / Celery workers. Sends tool jobs to
the Kali VM (192.168.121.28:5001) and blocks until done.

Usage:
    runner = ToolRunner()                          # reads env vars
    stdout = runner.run("nmap", "-sV 10.0.0.1")
"""

import logging
import os
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class ScannerUnavailableError(Exception):
    """Raised when the Kali VM is unreachable."""


class ToolRunner:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        api_key: Optional[str] = None,
        poll_interval: float = 3.0,
        connect_timeout: float = 5.0,
    ):
        self.base_url = (
            f"http://{host or os.getenv('KALI_VM_HOST', '192.168.121.28')}"
            f":{port or int(os.getenv('KALI_VM_PORT', '5001'))}"
        )
        self._api_key = api_key or os.getenv("SCANNER_API_KEY", "")
        self._poll_interval = poll_interval
        self._connect_timeout = connect_timeout

    # ── Internal helpers ──────────────────────────────────────────────

    @property
    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self._api_key:
            h["x-api-key"] = self._api_key
        return h

    def _get(self, path: str, timeout: float = 10.0) -> requests.Response:
        return requests.get(
            f"{self.base_url}{path}",
            headers=self._headers,
            timeout=timeout,
        )

    def _post(self, path: str, body: dict, timeout: float = 15.0) -> requests.Response:
        return requests.post(
            f"{self.base_url}{path}",
            json=body,
            headers=self._headers,
            timeout=timeout,
        )

    def _delete(self, path: str) -> None:
        try:
            requests.delete(
                f"{self.base_url}{path}",
                headers=self._headers,
                timeout=5.0,
            )
        except Exception:
            pass

    # ── Public API ────────────────────────────────────────────────────

    def health_check(self) -> bool:
        """Return True if the Kali VM scanner API is reachable."""
        try:
            resp = self._get("/health", timeout=self._connect_timeout)
            return resp.ok
        except Exception:
            return False

    def available_tools(self) -> dict[str, bool]:
        """Return a dict of tool → available on the Kali VM."""
        try:
            resp = self._get("/tools")
            resp.raise_for_status()
            data = resp.json()
            return {name: info.get("available", False) for name, info in data.items()}
        except Exception as exc:
            logger.warning("Could not fetch tool list from Kali VM: %s", exc)
            return {}

    def run(
        self,
        tool: str,
        args: str,
        timeout: int = 300,
    ) -> str:
        """
        Submit a tool job, poll until done, and return stdout.

        Args:
            tool:    Tool name, e.g. "nmap"
            args:    Raw arg string, e.g. "-sV -p 1-1000 192.168.56.20"
            timeout: Max seconds to wait for the tool to complete

        Returns:
            stdout string (may be empty if the tool produced no output)

        Raises:
            ScannerUnavailableError: if the Kali VM can't be reached
            RuntimeError:            if the job fails or times out on the Kali side
        """
        # Submit
        try:
            resp = self._post("/run-tool", {"tool": tool, "args": args, "timeout": timeout})
        except requests.ConnectionError as exc:
            raise ScannerUnavailableError(
                f"Cannot reach Kali VM at {self.base_url}: {exc}"
            ) from exc
        except requests.Timeout as exc:
            raise ScannerUnavailableError(
                f"Kali VM did not respond within {self._connect_timeout}s"
            ) from exc

        if resp.status_code == 400:
            raise ValueError(resp.json().get("detail", "Bad request"))
        resp.raise_for_status()

        job_id = resp.json()["job_id"]
        logger.info("Kali job submitted: tool=%s job=%s", tool, job_id)

        # Poll
        deadline = time.time() + timeout + 30  # a bit more than the tool timeout
        while time.time() < deadline:
            time.sleep(self._poll_interval)
            try:
                job_resp = self._get(f"/job/{job_id}")
            except Exception as exc:
                logger.warning("Poll error for job %s: %s", job_id, exc)
                continue

            if not job_resp.ok:
                logger.warning("Job %s returned HTTP %s", job_id, job_resp.status_code)
                continue

            data = job_resp.json()
            status = data.get("status")

            if status == "done":
                logger.info(
                    "Kali job done: tool=%s job=%s returncode=%s",
                    tool, job_id, data.get("returncode"),
                )
                stdout = data.get("stdout", "")
                self._delete(f"/job/{job_id}")
                return stdout

            if status == "failed":
                error = data.get("stderr", "") or "unknown error"
                self._delete(f"/job/{job_id}")
                raise RuntimeError(f"Kali tool '{tool}' failed: {error}")

            # still running — keep polling

        # Deadline exceeded
        self._delete(f"/job/{job_id}")
        raise RuntimeError(f"Kali tool '{tool}' timed out after {timeout}s")

    def run_safe(self, tool: str, args: str, timeout: int = 300) -> str:
        """
        Like run() but never raises — returns empty string on any error.
        Suitable for non-critical scan steps where a missing tool is acceptable.
        """
        try:
            return self.run(tool, args, timeout)
        except ScannerUnavailableError:
            logger.error("Kali VM unavailable — skipping tool %s", tool)
            return ""
        except Exception as exc:
            logger.warning("Tool %s failed (non-fatal): %s", tool, exc)
            return ""
