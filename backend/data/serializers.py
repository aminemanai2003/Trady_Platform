"""Serializers for data app."""
from rest_framework import serializers
from .models import EconomicIndicator, NewsArticle, EconomicEvent


class EconomicIndicatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = EconomicIndicator
        fields = ["id", "date", "series_id", "indicator_name", "value", "created_at"]


class NewsArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsArticle
        fields = ["article_id", "url", "title", "content", "source", "published_at", "scraped_at"]


class EconomicEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = EconomicEvent
        fields = "__all__"


class PriceDataSerializer(serializers.Serializer):
    """Serializer for InfluxDB OHLCV data."""
    time = serializers.DateTimeField()
    open = serializers.FloatField()
    high = serializers.FloatField()
    low = serializers.FloatField()
    close = serializers.FloatField()
    volume = serializers.IntegerField()
    symbol = serializers.CharField()
    timeframe = serializers.CharField()
