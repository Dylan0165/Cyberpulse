#!/usr/bin/env python3
"""CyberPulse — AI-powered penetration testing tool.

Usage:
    python main.py web                  Start web interface
    python main.py scan <target>        Quick scan via CLI
    python main.py scan <target> --full Full scan via CLI
    python main.py scan <target> --modules 01,03,07
    python main.py scraper              Run scrapers once
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

from config import Config

console = Console()

# ── Logging setup ──────────────────────────────────────────
Config.ensure_dirs()

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format="%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        RichHandler(console=console, rich_tracebacks=True, show_path=False),
        logging.FileHandler(Config.LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("cyberpulse")


def cmd_web(args):
    """Start the FastAPI web interface via uvicorn."""
    import uvicorn

    logger.info("Starting CyberPulse web interface on %s:%s", Config.FLASK_HOST, Config.FLASK_PORT)
    console.print(
        f"\n[bold green]  CyberPulse[/bold green] running at "
        f"[bold cyan]http://{Config.FLASK_HOST}:{Config.FLASK_PORT}[/bold cyan]\n"
    )
    uvicorn.run(
        "web.app:app",
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        reload=Config.FLASK_DEBUG,
        reload_excludes=["data/*", "*.log", "*.json"] if Config.FLASK_DEBUG else None,
    )


def cmd_scan(args):
    """Run a scan from the command line."""
    from engine.scanner import Scanner

    target = args.target
    if args.full:
        modules = Config.ALL_MODULES
        scan_type = "full"
    elif args.modules:
        modules = [m.strip().zfill(2) for m in args.modules.split(",")]
        scan_type = "custom"
    else:
        modules = Config.QUICK_MODULES
        scan_type = "quick"

    console.print(f"\n[bold green]  CyberPulse[/bold green] — Starting {scan_type} scan")
    console.print(f"  Target : [bold cyan]{target}[/bold cyan]")
    console.print(f"  Modules: [bold]{', '.join(modules)}[/bold]\n")

    scanner = Scanner(target=target, modules=modules, scan_type=scan_type)

    for event in scanner.run():
        if event["type"] == "module_start":
            console.print(f"  [yellow]>>>[/yellow] {event['module']} — {event['name']}")
        elif event["type"] == "module_done":
            findings = event.get("findings_count", 0)
            duration = event.get("duration", 0)
            console.print(f"  [green][OK][/green] {event['module']} — {findings} findings ({duration:.1f}s)")
        elif event["type"] == "module_error":
            console.print(f"  [red][FOUT][/red] {event['module']} — {event.get('error', 'unknown')}")
        elif event["type"] == "log":
            console.print(f"  [dim]{event['message']}[/dim]")
        elif event["type"] == "scan_complete":
            report_path = event.get("report_path", "")
            console.print(f"\n  [bold green]Scan voltooid![/bold green]")
            console.print(f"  Rapport: [bold cyan]{report_path}[/bold cyan]\n")

    # AI analyse
    if Config.DEEPSEEK_API_KEY:
        console.print("  [yellow]>>>[/yellow] AI analyse starten via DeepSeek...")
        from ai.analyzer import analyze_scan
        scan_data_path = Config.SCANS_DIR / scanner.scan_id / "scan_data.json"
        if scan_data_path.exists():
            with open(scan_data_path, "r", encoding="utf-8") as f:
                scan_data = json.load(f)
            analysis = analyze_scan(scan_data)
            analysis_path = Config.SCANS_DIR / scanner.scan_id / "analysis.json"
            with open(analysis_path, "w", encoding="utf-8") as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
            console.print(f"  [green][OK][/green] AI analyse opgeslagen: {analysis_path}")

            # Generate PDF
            from reports.generator import generate_pdf
            pdf_path = generate_pdf(scanner.scan_id)
            if pdf_path:
                console.print(f"  [green][OK][/green] PDF rapport: {pdf_path}")
    else:
        console.print("  [yellow]DEEPSEEK_API_KEY niet ingesteld — AI analyse overgeslagen[/yellow]")


def cmd_scraper(args):
    """Run all scrapers once."""
    from scraper.cve_scraper import CVEScraper
    from scraper.technique_scraper import TechniqueScraper
    from scraper.tool_scraper import ToolScraper

    console.print("\n[bold green]  CyberPulse[/bold green] — Scrapers draaien\n")

    for ScraperClass in [CVEScraper, TechniqueScraper, ToolScraper]:
        name = ScraperClass.__name__
        console.print(f"  [yellow]>>>[/yellow] {name}...")
        try:
            scraper = ScraperClass()
            count = scraper.run()
            console.print(f"  [green][OK][/green] {name} — {count} items verwerkt")
        except Exception as e:
            console.print(f"  [red][FOUT][/red] {name} — {e}")
            logger.exception("Scraper %s failed", name)

    console.print("\n  [bold green]Klaar![/bold green]\n")


def main():
    parser = argparse.ArgumentParser(
        prog="cyberpulse",
        description="CyberPulse — AI-powered penetration testing tool",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # web
    sub.add_parser("web", help="Start web interface")

    # scan
    scan_p = sub.add_parser("scan", help="Run a scan")
    scan_p.add_argument("target", help="Target domain or IP address")
    scan_p.add_argument("--full", action="store_true", help="Run all 20 modules")
    scan_p.add_argument("--modules", type=str, help="Comma-separated module numbers (e.g. 01,03,07)")

    # scraper
    sub.add_parser("scraper", help="Run scrapers manually")

    args = parser.parse_args()

    # Show config warnings
    for issue in Config.validate():
        console.print(f"  [yellow][WAARSCHUWING][/yellow] {issue}")

    if args.command == "web":
        cmd_web(args)
    elif args.command == "scan":
        cmd_scan(args)
    elif args.command == "scraper":
        cmd_scraper(args)


if __name__ == "__main__":
    main()
