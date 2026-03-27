"""
Scheduled tasks for FX Alpha Platform using APScheduler
"""

from apscheduler.schedulers.background import BackgroundScheduler
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

scheduler = None


def start_scheduler():
    """Start the background scheduler"""
    global scheduler
    if scheduler is not None and scheduler.running:
        return

    try:
        scheduler = BackgroundScheduler()
        
        # Add job to refresh news every 90 minutes
        scheduler.add_job(
            refresh_news_data,
            "interval",
            minutes=90,
            id="refresh_news_data",
            name="Refresh news data",
            replace_existing=True,
            max_instances=1,
        )
        
        scheduler.start()
        logger.info("✓ Scheduler started successfully")
    except Exception as e:
        logger.error(f"✗ Failed to start scheduler: {e}")


def stop_scheduler():
    """Stop the background scheduler"""
    global scheduler
    if scheduler is not None and scheduler.running:
        scheduler.shutdown()
        logger.info("✓ Scheduler stopped")


def refresh_news_data():
    """Periodically refresh news data from RSS feeds"""
    try:
        from acquisition.news_collector import collect_news_data
        
        logger.info("📰 Running scheduled news refresh...")
        result = collect_news_data()
        logger.info(f"✓ News refresh completed: {result}")
    except Exception as e:
        logger.error(f"✗ News refresh failed: {e}", exc_info=True)


class SchedulerConfig(AppConfig):
    """AppConfig for scheduler"""
    default_auto_field = "django.db.models.BigAutoField"
    name = "scheduling"

    def ready(self):
        """Start scheduler when Django is ready"""
        import os
        if os.environ.get("RUN_MAIN") == "true":  # Avoid duplicate in reload
            start_scheduler()
