"""
Django models for storing engineered features
"""
from django.db import models


class TechnicalFeatures(models.Model):
    """Stores technical indicator features"""
    
    symbol = models.CharField(max_length=20, db_index=True)
    timestamp = models.DateTimeField(db_index=True)
    
    # Momentum indicators
    rsi_14 = models.FloatField(null=True)
    rsi_28 = models.FloatField(null=True)
    
    # MACD
    macd = models.FloatField(null=True)
    macd_signal = models.FloatField(null=True)
    macd_diff = models.FloatField(null=True)
    
    # Bollinger Bands
    bb_upper = models.FloatField(null=True)
    bb_middle = models.FloatField(null=True)
    bb_lower = models.FloatField(null=True)
    bb_width = models.FloatField(null=True)
    bb_position = models.FloatField(null=True)  # Where price is relative to bands
    
    # Volatility
    atr_14 = models.FloatField(null=True)
    rolling_vol_20 = models.FloatField(null=True)
    rolling_vol_60 = models.FloatField(null=True)
    
    # Trend
    trend_slope_20 = models.FloatField(null=True)
    trend_slope_60 = models.FloatField(null=True)
    
    # Support/Resistance
    distance_to_support = models.FloatField(null=True)
    distance_to_resistance = models.FloatField(null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['symbol', 'timestamp']
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['symbol', '-timestamp']),
        ]


class MacroFeatures(models.Model):
    """Stores macro-economic features"""
    
    currency_pair = models.CharField(max_length=20, db_index=True)
    date = models.DateField(db_index=True)
    
    # Rate differentials
    interest_rate_diff = models.FloatField(null=True)
    policy_rate_diff = models.FloatField(null=True)
    
    # Inflation
    inflation_diff = models.FloatField(null=True)
    
    # Economic surprise
    surprise_metric = models.FloatField(null=True)  # actual - forecast
    
    # Yield spread proxy
    yield_spread = models.FloatField(null=True)
    
    # Risk-on/Risk-off proxy
    risk_sentiment = models.FloatField(null=True)  # -1 to +1
    
    # GDP growth differential
    gdp_growth_diff = models.FloatField(null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['currency_pair', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['currency_pair', '-date']),
        ]


class SentimentFeatures(models.Model):
    """Stores sentiment features from news"""
    
    timestamp = models.DateTimeField(db_index=True)
    currency_mentioned = models.CharField(max_length=10, db_index=True)
    
    # Sentiment scores
    sentiment_score = models.FloatField()  # -1 to +1
    confidence = models.FloatField()  # 0 to 1
    
    # Entity relevance
    relevance_score = models.FloatField()  # How relevant is this news to the currency
    
    # Volume metrics
    news_volume_1h = models.IntegerField(default=0)
    news_volume_24h = models.IntegerField(default=0)
    
    # Source
    source = models.CharField(max_length=100)
    article_id = models.IntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['currency_mentioned', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
