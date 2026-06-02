"""
CyberPulse Scanner API — runs on the Kali VM at 192.168.121.28:5001

Receives tool execution requests from the Ubuntu backend and runs
the actual Kali tools as async subprocesses.

Start:
    export SCANNER_API_KEY=changeme
    uvicorn tool_api:app --host 0.0.0.0 --port 5001
"""

import asyncio
import os
import shlex
import shutil
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ── Auth ──────────────────────────────────────────────────────────────────────

SCANNER_API_KEY = os.getenv("SCANNER_API_KEY", "")


def _check_key(x_api_key: Optional[str] = Header(default=None)):
    if not SCANNER_API_KEY:
        return  # auth disabled if key not configured
    if x_api_key != SCANNER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Api-Key header",
        )


# ── Allowed tools ─────────────────────────────────────────────────────────────

ALLOWED_TOOLS = {
    "nmap", "nuclei", "sqlmap", "hydra", "gobuster", "ffuf",
    "nikto", "whatweb", "theharvester", "gitleaks", "testssl.sh",
    "subfinder", "httpx", "feroxbuster", "masscan",
}

# Per-tool default timeouts (seconds)
TOOL_TIMEOUTS: dict[str, int] = {
    "nmap":        300,
    "nuclei":      600,
    "sqlmap":      600,
    "hydra":       300,
    "gobuster":    300,
    "ffuf":        300,
    "nikto":       300,
    "whatweb":     120,
    "theharvester":300,
    "gitleaks":    120,
    "testssl.sh":  180,
    "subfinder":   300,
    "httpx":       120,
    "feroxbuster": 300,
    "masscan":     120,
}


# ── Job store ─────────────────────────────────────────────────────────────────

class JobStatus(str, Enum):
    RUNNING = "running"
    DONE    = "done"
    FAILED  = "failed"


class Job:
    def __init__(self, job_id: str, tool: str, args: str):
        self.job_id     = job_id
        self.tool       = tool
        self.args       = args
        self.status     = JobStatus.RUNNING
        self.stdout     = ""
        self.stderr     = ""
        self.returncode: Optional[int] = None
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.finished_at: Optional[str] = None
        self._process: Optional[asyncio.subprocess.Process] = None

    def to_dict(self) -> dict:
        return {
            "job_id":      self.job_id,
            "tool":        self.tool,
            "args":        self.args,
            "status":      self.status,
            "stdout":      self.stdout,
            "stderr":      self.stderr,
            "returncode":  self.returncode,
            "created_at":  self.created_at,
            "finished_at": self.finished_at,
        }


_jobs: dict[str, Job] = {}


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(title="CyberPulse Scanner API", version="1.0")


# ── Models ────────────────────────────────────────────────────────────────────

class RunToolRequest(BaseModel):
    tool:    str
    args:    str = ""
    timeout: int = 300


# ── Background task ───────────────────────────────────────────────────────────

async def _execute(job: Job, timeout: int):
    """Run the tool as an async subprocess and update job state."""
    tool_path = shutil.which(job.tool)
    if not tool_path:
        job.status = JobStatus.FAILED
        job.stderr = f"Tool '{job.tool}' not found on this system"
        job.finished_at = datetime.now(timezone.utc).isoformat()
        return

    # Split args safely; empty string → no extra args
    extra = shlex.split(job.args) if job.args.strip() else []
    cmd = [tool_path] + extra

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        job._process = proc

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=float(timeout)
            )
            job.stdout     = stdout_bytes.decode(errors="replace")
            job.stderr     = stderr_bytes.decode(errors="replace")
            job.returncode = proc.returncode
            job.status     = JobStatus.DONE if proc.returncode == 0 else JobStatus.FAILED
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            job.status     = JobStatus.FAILED
            job.stderr     = f"Timeout: tool exceeded {timeout}s"
            job.returncode = -1

    except Exception as exc:
        job.status     = JobStatus.FAILED
        job.stderr     = str(exc)
        job.returncode = -1

    job.finished_at = datetime.now(timezone.utc).isoformat()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "node": "kali-tool-api"}


@app.get("/tools")
async def list_tools(x_api_key: Optional[str] = Header(default=None)):
    _check_key(x_api_key)
    return {
        tool: {"available": shutil.which(tool) is not None}
        for tool in sorted(ALLOWED_TOOLS)
    }


@app.post("/run-tool", status_code=status.HTTP_202_ACCEPTED)
async def run_tool(
    body: RunToolRequest,
    x_api_key: Optional[str] = Header(default=None),
):
    _check_key(x_api_key)

    if body.tool not in ALLOWED_TOOLS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tool '{body.tool}' is not in the allowed list",
        )

    effective_timeout = min(
        max(body.timeout, 10),
        TOOL_TIMEOUTS.get(body.tool, 600),
    )

    job_id = str(uuid.uuid4())
    job = Job(job_id=job_id, tool=body.tool, args=body.args)
    _jobs[job_id] = job

    asyncio.create_task(_execute(job, effective_timeout))

    return {"job_id": job_id}


@app.get("/job/{job_id}")
async def get_job(
    job_id: str,
    x_api_key: Optional[str] = Header(default=None),
):
    _check_key(x_api_key)
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@app.delete("/job/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    x_api_key: Optional[str] = Header(default=None),
):
    _check_key(x_api_key)
    job = _jobs.pop(job_id, None)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # Kill if still running
    if job._process and job.status == JobStatus.RUNNING:
        try:
            job._process.kill()
        except Exception:
            pass
