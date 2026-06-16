"""Models for data app — maps to existing PostgreSQL tables from Data Acquisition."""
from django.db import models


class EconomicIndicator(models.Model):
    """Macro-economic indicators from FRED API (existing table: economic_indicators)."""
    date = models.DateField()
    series_id = models.CharField(max_length=50)
    indicator_name = models.CharField(max_length=200)
    value = models.DecimalField(max_digits=20, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "economic_indicators"
        managed = False  # Table already exists from Data Acquisition
        unique_together = ("date", "series_id")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.series_id} - {self.date}: {self.value}"


class NewsArticle(models.Model):
    """News articles from Reuters RSS (existing table: news_articles)."""
    article_id = models.AutoField(primary_key=True)
    url = models.TextField(unique=True)
    title = models.TextField()
    content = models.TextField(blank=True, null=True)
    source = models.CharField(max_length=100)
    published_at = models.DateTimeField(blank=True, null=True)
    scraped_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "news_articles"
        managed = False
        ordering = ["-published_at"]

    def __str__(self):
        return self.title[:80]


class EconomicEvent(models.Model):
    """Economic calendar events (existing table: economic_events)."""
    event_id = models.AutoField(primary_key=True)
    event_date = models.DateTimeField()
    currency = models.CharField(max_length=10)
    event_name = models.CharField(max_length=200)
    importance = models.CharField(max_length=20)
    forecast = models.DecimalField(max_digits=20, decimal_places=6, null=True)
    actual = models.DecimalField(max_digits=20, decimal_places=6, null=True)
    previous = models.DecimalField(max_digits=20, decimal_places=6, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "economic_events"
        managed = False
        ordering = ["-event_date"]

    def __str__(self):
        return f"{self.currency} - {self.event_name}"
