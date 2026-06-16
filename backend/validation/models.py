"""
Django models for validation results
"""
from django.db import models
from django.contrib.postgres.fields import JSONField


class ValidationReport(models.Model):
    """Stores validation results"""
    
    class ReportType(models.TextChoices):
        TIMESERIES = 'timeseries', 'Time Series'
        MACRO = 'macro', 'Macro Data'
        NEWS = 'news', 'News Data'
    
    report_type = models.CharField(max_length=20, choices=ReportType.choices)
    symbol = models.CharField(max_length=20, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Validation results
    is_valid = models.BooleanField(default=True)
    issues_found = models.IntegerField(default=0)
    details = models.JSONField(default=dict)
    
    # Metrics
    records_checked = models.IntegerField(default=0)
    missing_count = models.IntegerField(default=0)
    duplicate_count = models.IntegerField(default=0)
    anomaly_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['report_type', '-timestamp']),
            models.Index(fields=['symbol', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.report_type} - {self.timestamp}"


class DataQualityMetric(models.Model):
    """Track data quality over time"""
    
    timestamp = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=50)
    metric_name = models.CharField(max_length=100)
    metric_value = models.FloatField()
    threshold = models.FloatField(null=True, blank=True)
    is_passing = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['source', 'metric_name', '-timestamp']),
        ]
