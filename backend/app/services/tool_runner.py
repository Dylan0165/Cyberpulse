"""
ToolRunner — HTTP client for the Kali VM scanner API.

Two variants:
  ToolRunner       — synchronous, for Celery workers
  AsyncToolRunner  — async (httpx), for FastAPI endpoints
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

logger = logging.getLogger(__name__)


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class ToolResult:
    tool:       str
    args:       str
    stdout:     str = ""
    stderr:     str = ""
    returncode: int = 0
    success:    bool = True
    error:      str = ""
    duration_s: float = 0.0


class ScannerUnavailableError(Exception):
    """Raised when the Kali VM is unreachable."""


def _is_success(tool: str, returncode: int, stdout: str, stderr: str) -> bool:
    """Determine real success for security tools.

    Many security tools exit non-zero even when they ran correctly
    (e.g. nikto/sqlmap finding nothing, testssl with no HTTPS). A plain
    `returncode == 0` check wrongly marks those as failures.
    """
    combined = (stdout + stderr).lower()

    if tool == "nikto":
        return "target ip:" in combined or "+ " in combined
    if tool == "sqlmap":
        return "starting @" in combined  # ran fine, no SQLi = expected
    if tool == "testssl.sh":
        return "testssl.sh version" in combined  # ran fine, no HTTPS = info
    if tool == "hydra":
        return len(stdout) > 100  # actually attempted connections
    if tool == "theharvester":
        return True  # deprecation warning is not a failure
    if tool == "gitleaks":
        return "scanned" in combined  # ran fine, no leaks = good
    if tool == "ffuf":
        return "method" in combined or "status:" in combined

    # Default: success if returncode 0 OR produced meaningful output
    return returncode == 0 or len(stdout.strip()) > 100


# ── Sync ToolRunner (Celery workers) ──────────────────────────────────────────

class ToolRunner:
    """Synchronous HTTP client — use inside Celery tasks."""

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
        self._poll = poll_interval
        self._timeout = connect_timeout

    @property
    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self._api_key:
            h["x-api-key"] = self._api_key
        return h

    def _get(self, path: str, timeout: float = 10.0) -> requests.Response:
        return requests.get(f"{self.base_url}{path}", headers=self._headers, timeout=timeout)

    def _post(self, path: str, body: dict) -> requests.Response:
        return requests.post(f"{self.base_url}{path}", json=body, headers=self._headers, timeout=15.0)

    def _del(self, path: str) -> None:
        try:
            requests.delete(f"{self.base_url}{path}", headers=self._headers, timeout=5.0)
        except Exception:
            pass

    def health_check(self) -> bool:
        try:
            return self._get("/health", timeout=self._timeout).ok
        except Exception:
            return False

    def get_available_tools(self) -> dict:
        """Return tool availability dict from the Kali VM."""
        try:
            resp = self._get("/tools")
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.warning("Could not fetch tool list: %s", exc)
            return {}

    def run_tool(self, tool: str, args: str, timeout: int = 300) -> ToolResult:
        """Submit a job and block until done. Returns a ToolResult."""
        t0 = time.time()
        try:
            resp = self._post("/run-tool", {"tool": tool, "args": args, "timeout": timeout})
        except requests.ConnectionError as exc:
            raise ScannerUnavailableError(f"Cannot reach Kali VM: {exc}") from exc
        except requests.Timeout as exc:
            raise ScannerUnavailableError(f"Kali VM timeout: {exc}") from exc

        if resp.status_code == 400:
            return ToolResult(tool=tool, args=args, success=False, error=resp.json().get("detail", "bad request"))
        resp.raise_for_status()

        job_id = resp.json()["job_id"]
        deadline = time.time() + timeout + 30

        while time.time() < deadline:
            time.sleep(self._poll)
            try:
                data = self._get(f"/job/{job_id}").json()
            except Exception:
                continue

            status = data.get("status")
            if status in ("done", "failed"):
                self._del(f"/job/{job_id}")
                stdout = data.get("stdout", "")
                stderr = data.get("stderr", "")
                returncode = data.get("returncode", 0 if status == "done" else -1)
                success = _is_success(tool, returncode, stdout, stderr)
                return ToolResult(
                    tool=tool, args=args,
                    stdout=stdout, stderr=stderr, returncode=returncode,
                    success=success,
                    error="" if success else (stderr[:200] or "tool failed"),
                    duration_s=round(time.time() - t0, 1),
                )

        self._del(f"/job/{job_id}")
        return ToolResult(tool=tool, args=args, success=False, error=f"timeout after {timeout}s")

    def run_safe(self, tool: str, args: str, timeout: int = 300) -> ToolResult:
        """Like run_tool() but never raises — returns failed ToolResult on errors."""
        try:
            return self.run_tool(tool, args, timeout)
        except ScannerUnavailableError as exc:
            logger.error("Kali VM unavailable — skipping %s: %s", tool, exc)
            return ToolResult(tool=tool, args=args, success=False, error=str(exc))
        except Exception as exc:
            logger.warning("Tool %s failed: %s", tool, exc)
            return ToolResult(tool=tool, args=args, success=False, error=str(exc))

    def run_parallel(self, commands: list[dict], max_workers: int = 4) -> list[ToolResult]:
        """
        Run multiple tools in parallel using threads.

        Each command dict: {"tool": str, "args": str, "timeout": int}
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results: list[ToolResult] = [None] * len(commands)  # type: ignore

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(
                    self.run_safe,
                    cmd["tool"],
                    cmd.get("args", ""),
                    cmd.get("timeout", 300),
                ): i
                for i, cmd in enumerate(commands)
            }
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    results[idx] = future.result()
                except Exception as exc:
                    cmd = commands[idx]
                    results[idx] = ToolResult(tool=cmd["tool"], args=cmd.get("args",""), success=False, error=str(exc))

        return results


# ── Async ToolRunner (FastAPI endpoints) ──────────────────────────────────────

class AsyncToolRunner:
    """Async HTTP client — use inside async FastAPI route handlers."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        api_key: Optional[str] = None,
        poll_interval: float = 2.0,
    ):
        import httpx
        self._httpx = httpx
        self.base_url = (
            f"http://{host or os.getenv('KALI_VM_HOST', '192.168.121.28')}"
            f":{port or int(os.getenv('KALI_VM_PORT', '5001'))}"
        )
        self._api_key = api_key or os.getenv("SCANNER_API_KEY", "")
        self._poll = poll_interval

    @property
    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self._api_key:
            h["x-api-key"] = self._api_key
        return h

    async def get_available_tools(self) -> dict:
        async with self._httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/tools", headers=self._headers)
            resp.raise_for_status()
            return resp.json()

    async def run_tool(self, tool: str, args: str, timeout: int = 300) -> ToolResult:
        t0 = time.time()
        async with self._httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.base_url}/run-tool",
                json={"tool": tool, "args": args, "timeout": timeout},
                headers=self._headers,
            )
            resp.raise_for_status()
            job_id = resp.json()["job_id"]

        deadline = time.time() + timeout + 30
        async with self._httpx.AsyncClient(timeout=10.0) as client:
            while time.time() < deadline:
                await asyncio.sleep(self._poll)
                try:
                    r = await client.get(f"{self.base_url}/job/{job_id}", headers=self._headers)
                    data = r.json()
                except Exception:
                    continue

                if data.get("status") in ("done", "failed"):
                    await client.delete(f"{self.base_url}/job/{job_id}", headers=self._headers)
                    stdout = data.get("stdout", "")
                    stderr = data.get("stderr", "")
                    returncode = data.get("returncode", 0 if data.get("status") == "done" else -1)
                    success = _is_success(tool, returncode, stdout, stderr)
                    return ToolResult(
                        tool=tool, args=args,
                        stdout=stdout, stderr=stderr, returncode=returncode,
                        success=success,
                        error="" if success else (stderr[:200] or "tool failed"),
                        duration_s=round(time.time()-t0,1),
                    )

        return ToolResult(tool=tool, args=args, success=False, error=f"timeout after {timeout}s")

    async def run_parallel(self, commands: list[dict], max_workers: int = 4) -> list[ToolResult]:
        """Run up to max_workers tools concurrently."""
        sem = asyncio.Semaphore(max_workers)

        async def _run(cmd: dict) -> ToolResult:
            async with sem:
                return await self.run_tool(
                    cmd["tool"], cmd.get("args",""), cmd.get("timeout", 300)
                )

        return list(await asyncio.gather(*[_run(c) for c in commands], return_exceptions=False))
