"""Scraper Scheduler — runs scrapers on a daily schedule using APScheduler."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from config import Config
from scraper.cve_scraper import CVEScraper
from scraper.technique_scraper import TechniqueScraper
from scraper.tool_scraper import ToolScraper

logger = logging.getLogger("cyberpulse.scraper.scheduler")

_scheduler = None


def run_all_scrapers():
    """Execute all scrapers sequentially."""
    logger.info("Running scheduled scraper job")
    for ScraperClass in [CVEScraper, TechniqueScraper, ToolScraper]:
        name = ScraperClass.__name__
        try:
            scraper = ScraperClass()
            count = scraper.run()
            logger.info("Scraper %s completed: %d items", name, count)
        except Exception:
            logger.exception("Scraper %s failed", name)


def start_scheduler():
    """Start the background APScheduler for daily scraping."""
    global _scheduler
    if _scheduler is not None:
        logger.warning("Scheduler already running")
        return

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        run_all_scrapers,
        "cron",
        hour=int(Config.SCRAPER_HOUR),
        minute=0,
        id="daily_scrapers",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scraper scheduler started (daily at %s:00)", Config.SCRAPER_HOUR)


def stop_scheduler():
    """Stop the background scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scraper scheduler stopped")
