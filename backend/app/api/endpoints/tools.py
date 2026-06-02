"""Kali VM tool availability endpoint."""

import os

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()

KALI_VM_HOST = os.getenv("KALI_VM_HOST", "192.168.121.28")
KALI_VM_PORT = os.getenv("KALI_VM_PORT", "5001")
SCANNER_API_KEY = os.getenv("SCANNER_API_KEY", "")

TOOL_CATEGORIES = {
    "nmap":          {"phase": 1, "category": "Reconnaissance"},
    "subfinder":     {"phase": 1, "category": "Reconnaissance"},
    "httpx":         {"phase": 1, "category": "Reconnaissance"},
    "whatweb":       {"phase": 1, "category": "Reconnaissance"},
    "masscan":       {"phase": 1, "category": "Reconnaissance"},
    "nuclei":        {"phase": 2, "category": "Vulnerability Detection"},
    "nikto":         {"phase": 2, "category": "Vulnerability Detection"},
    "sqlmap":        {"phase": 3, "category": "Web Application"},
    "ffuf":          {"phase": 3, "category": "Web Application"},
    "gobuster":      {"phase": 3, "category": "Web Application"},
    "feroxbuster":   {"phase": 3, "category": "Web Application"},
    "hydra":         {"phase": 5, "category": "Authentication"},
    "testssl.sh":    {"phase": 6, "category": "SSL/TLS"},
    "theharvester":  {"phase": 7, "category": "OSINT"},
    "gitleaks":      {"phase": 7, "category": "OSINT"},
}


@router.get("/tools/available")
async def get_available_tools():
    """Fetch tool availability from the Kali VM and enrich with phase/category metadata."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"http://{KALI_VM_HOST}:{KALI_VM_PORT}/tools",
                headers={"x-api-key": SCANNER_API_KEY},
            )
            kali_tools = response.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Kali VM not reachable: {e}")

    result = []
    for tool, status in kali_tools.items():
        result.append({
            "name":      tool,
            "available": status.get("available", False),
            "phase":     TOOL_CATEGORIES.get(tool, {}).get("phase", 0),
            "category":  TOOL_CATEGORIES.get(tool, {}).get("category", "Other"),
        })

    return {
        "tools":           sorted(result, key=lambda x: x["phase"]),
        "total":           len(result),
        "available_count": sum(1 for t in result if t["available"]),
        "kali_vm":         f"{KALI_VM_HOST}:{KALI_VM_PORT}",
    }


@router.get("/tools/check")
async def check_kali_connection():
    """Quick reachability check for the Kali VM."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(
                f"http://{KALI_VM_HOST}:{KALI_VM_PORT}/health",
                headers={"x-api-key": SCANNER_API_KEY},
            )
        return {"reachable": resp.ok, "kali_vm": f"{KALI_VM_HOST}:{KALI_VM_PORT}"}
    except Exception:
        return {"reachable": False, "kali_vm": f"{KALI_VM_HOST}:{KALI_VM_PORT}"}
