"""
MCP Scheduler for FX Alpha Platform.
Auto-fetches News (NewsAPI), OHLCV (Alpha Vantage) and Macro (FRED) data
on a configurable schedule using APScheduler.

Schedule (configurable via env):
  NEWS_REFRESH_MINUTES  default 120   (every 2 hours)
  OHLCV_REFRESH_MINUTES default 240   (every 4 hours)
  MACRO_REFRESH_HOUR    default 0     (midnight daily)
"""

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from django.apps import AppConfig

logger = logging.getLogger(__name__)

scheduler = None

# ── configurable intervals ────────────────────────────────────────────────────
NEWS_MINUTES = int(os.getenv("NEWS_REFRESH_MINUTES", "120"))
OHLCV_MINUTES = int(os.getenv("OHLCV_REFRESH_MINUTES", "240"))
MACRO_HOUR = int(os.getenv("MACRO_REFRESH_HOUR", "0"))


# ── job functions ─────────────────────────────────────────────────────────────

def _job_refresh_news():
    """Scheduled: fetch financial news from NewsAPI.org → SQLite."""
    logger.info("[MCP] ▶ news refresh start")
    try:
        from scheduling.collectors.newsapi_collector import collect_newsapi
        result = collect_newsapi()
        logger.info(f"[MCP] ✓ news: inserted={result['inserted']} skipped={result['skipped']}")
    except Exception as exc:
        logger.error(f"[MCP] ✗ news error: {exc}", exc_info=True)


def _job_refresh_ohlcv():
    """Scheduled: fetch OHLCV candles from Alpha Vantage → SQLite."""
    logger.info("[MCP] ▶ ohlcv refresh start")
    try:
        from scheduling.collectors.alpha_vantage_collector import collect_alpha_vantage_ohlcv
        result = collect_alpha_vantage_ohlcv()
        logger.info(f"[MCP] ✓ ohlcv: inserted={result['inserted']} skipped={result['skipped']}")
    except Exception as exc:
        logger.error(f"[MCP] ✗ ohlcv error: {exc}", exc_info=True)


def _job_refresh_macro():
    """Scheduled: fetch macro indicators from FRED → SQLite."""
    logger.info("[MCP] ▶ macro refresh start")
    try:
        from scheduling.collectors.fred_collector_sqlite import collect_fred_macro
        result = collect_fred_macro()
        logger.info(f"[MCP] ✓ macro: inserted={result['inserted']} skipped={result['skipped']}")
    except Exception as exc:
        logger.error(f"[MCP] ✗ macro error: {exc}", exc_info=True)


def _job_refresh_yfinance():
    """Scheduled: fetch hourly OHLCV from Yahoo Finance → SQLite."""
    logger.info("[MCP] ▶ yfinance 1h refresh start")
    try:
        from scheduling.collectors.yfinance_collector import collect_yfinance_ohlcv
        result = collect_yfinance_ohlcv()
        logger.info(f"[MCP] ✓ yfinance 1h: inserted={result['inserted']} skipped={result['skipped']}")
        if result['errors']:
            logger.warning(f"[MCP] yfinance warnings: {result['errors']}")
    except Exception as exc:
        logger.error(f"[MCP] ✗ yfinance error: {exc}", exc_info=True)


def _job_settle_paper_trades():
    """Scheduled: settle open paper positions (SL/TP/expiry) and record agent outcomes."""
    logger.info("[MCP] ▶ paper trade settlement start")
    try:
        from paper_trading.services.settler import settle_open_positions
        result = settle_open_positions()
        logger.info(
            f"[MCP] ✓ settler: closed={result['closed']} "
            f"updated={result['updated']} errors={result['errors']}"
        )
    except Exception as exc:
        logger.error(f"[MCP] ✗ settler error: {exc}", exc_info=True)


# ── scheduler lifecycle ───────────────────────────────────────────────────────

def start_scheduler():
    global scheduler
    if scheduler is not None and scheduler.running:
        return

    try:
        scheduler = BackgroundScheduler(timezone="UTC")

        # News: every NEWS_MINUTES
        scheduler.add_job(
            _job_refresh_news,
            IntervalTrigger(minutes=NEWS_MINUTES),
            id="mcp_news",
            name=f"MCP News (every {NEWS_MINUTES}min)",
            replace_existing=True,
            max_instances=1,
        )

        # OHLCV AV daily+weekly: every OHLCV_MINUTES
        scheduler.add_job(
            _job_refresh_ohlcv,
            IntervalTrigger(minutes=OHLCV_MINUTES),
            id="mcp_ohlcv",
            name=f"MCP OHLCV (every {OHLCV_MINUTES}min)",
            replace_existing=True,
            max_instances=1,
        )

        # OHLCV yfinance hourly: every 4 hours
        scheduler.add_job(
            _job_refresh_yfinance,
            IntervalTrigger(hours=4),
            id="mcp_yfinance",
            name="MCP yfinance 1h (every 4h)",
            replace_existing=True,
            max_instances=1,
        )

        # Macro: daily at MACRO_HOUR:00 UTC
        scheduler.add_job(
            _job_refresh_macro,
            CronTrigger(hour=MACRO_HOUR, minute=0),
            id="mcp_macro",
            name=f"MCP Macro (daily {MACRO_HOUR:02d}:00 UTC)",
            replace_existing=True,
            max_instances=1,
        )

        # Paper trade settler: every 4 hours (aligned with OHLCV refresh)
        scheduler.add_job(
            _job_settle_paper_trades,
            IntervalTrigger(hours=4),
            id="mcp_settler",
            name="MCP Settler (every 4h)",
            replace_existing=True,
            max_instances=1,
        )

        scheduler.start()
        logger.info(
            f"[MCP] Scheduler started — "
            f"news every {NEWS_MINUTES}min | "
            f"ohlcv every {OHLCV_MINUTES}min | "
            f"yfinance 1h every 4h | "
            f"macro daily at {MACRO_HOUR:02d}:00 UTC | "
            f"settler every 4h"
        )

        # Run an initial fetch on startup — staggered to avoid SQLite lock contention
        import threading
        import time as _time

        def _staggered_start():
            _job_refresh_news()
            _time.sleep(5)
            _job_refresh_macro()
            _time.sleep(5)
            _job_refresh_ohlcv()
            _time.sleep(5)
            _job_refresh_yfinance()
            _time.sleep(5)
            _job_settle_paper_trades()

        threading.Thread(target=_staggered_start, daemon=True).start()

    except Exception as exc:
        logger.error(f"[MCP] Failed to start scheduler: {exc}", exc_info=True)


def stop_scheduler():
    global scheduler
    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[MCP] Scheduler stopped")


class SchedulerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "scheduling"

    def ready(self):
        """Start MCP scheduler when Django is ready (skip in manage.py commands)."""
        import sys
        # In `runserver`, Django spawns two processes:
        #   - parent (monitor/watcher): RUN_MAIN is NOT set → skip
        #   - child (actual worker):   RUN_MAIN="true"      → start scheduler
        # In production (gunicorn/uvicorn): only one process, RUN_MAIN not set either
        # so we allow it unless we're clearly in the monitor process.
        in_runserver = "runserver" in sys.argv
        is_worker = os.environ.get("RUN_MAIN") == "true"

        if in_runserver and not is_worker:
            return  # Skip the monitor/watcher process to avoid double-start

        if os.environ.get("MCP_SCHEDULER_DISABLED", "").lower() != "true":
            start_scheduler()
