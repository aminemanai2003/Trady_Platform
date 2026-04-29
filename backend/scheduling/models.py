"""
SQLite models for MCP data ingestion.
Stores News, Macro and OHLCV data locally so the platform works without Docker.
"""
from django.db import models


class NewsArticle(models.Model):
    """Financial news article fetched from NewsAPI.org or RSS feeds."""
    title = models.CharField(max_length=500)
    content = models.TextField(blank=True, default="")
    source = models.CharField(max_length=100, blank=True, default="")
    url = models.URLField(max_length=800, blank=True, default="")
    published_at = models.DateTimeField(db_index=True)
    currencies = models.JSONField(default=list)          # e.g. ["EUR", "USD"]
    sentiment_score = models.FloatField(null=True, blank=True)  # -1.0 to 1.0

    class Meta:
        ordering = ["-published_at"]
        indexes = [models.Index(fields=["published_at"])]

    def __str__(self):
        return self.title[:80]


class MacroIndicator(models.Model):
    """Macroeconomic indicator value fetched from FRED."""
    series_id = models.CharField(max_length=50, db_index=True)   # e.g. "FEDFUNDS"
    indicator_name = models.CharField(max_length=200)
    value = models.FloatField(null=True, blank=True)
    date = models.DateField(db_index=True)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("series_id", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.series_id} {self.date}: {self.value}"


class OHLCVCandle(models.Model):
    """OHLCV candle fetched from Alpha Vantage (forex)."""
    TIMEFRAME_CHOICES = [
        ("1h", "1 Hour"),
        ("4h", "4 Hours"),
        ("1d", "Daily"),
    ]
    symbol = models.CharField(max_length=10, db_index=True)       # e.g. "EURUSD"
    timeframe = models.CharField(max_length=5, choices=TIMEFRAME_CHOICES, db_index=True)
    timestamp = models.DateTimeField(db_index=True)
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.BigIntegerField(default=0)

    class Meta:
        unique_together = ("symbol", "timeframe", "timestamp")
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.symbol}/{self.timeframe} @ {self.timestamp}: C={self.close}"


class IngestionLog(models.Model):
    """Track ingestion runs for freshness monitoring."""
    SOURCE_CHOICES = [("news", "News"), ("macro", "Macro"), ("ohlcv", "OHLCV")]
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, db_index=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    records_inserted = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default="running")  # running / success / error
    error_message = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.source} @ {self.started_at} [{self.status}]"
