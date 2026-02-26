"""
Django models for agent signals and decisions
"""
from django.db import models


class AgentSignal(models.Model):
    """Individual agent trading signal"""
    
    class AgentType(models.TextChoices):
        TECHNICAL = 'technical', 'Technical Agent'
        MACRO = 'macro', 'Macro Agent'
        SENTIMENT = 'sentiment', 'Sentiment Agent'
    
    class SignalType(models.TextChoices):
        BUY = 'BUY', 'Buy'
        SELL = 'SELL', 'Sell'
        NEUTRAL = 'NEUTRAL', 'Neutral'
    
    agent_type = models.CharField(max_length=20, choices=AgentType.choices)
    symbol = models.CharField(max_length=20, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Signal details
    signal = models.CharField(max_length=10, choices=SignalType.choices)
    confidence = models.FloatField()  # 0 to 1
    reasoning = models.TextField()
    
    # Feature snapshot (JSON)
    features_used = models.JSONField(default=dict)
    
    # Performance tracking
    tokens_used = models.IntegerField(default=0)
    latency_ms = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['agent_type', 'symbol', '-timestamp']),
            models.Index(fields=['symbol', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.agent_type} - {self.symbol} - {self.signal} ({self.confidence:.2f})"


class CoordinatorDecision(models.Model):
    """Final coordinated trading decision"""
    
    class DecisionType(models.TextChoices):
        BUY = 'BUY', 'Buy'
        SELL = 'SELL', 'Sell'
        NEUTRAL = 'NEUTRAL', 'Neutral'
    
    class RiskLevel(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
    
    symbol = models.CharField(max_length=20, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Final decision
    decision = models.CharField(max_length=10, choices=DecisionType.choices)
    confidence = models.FloatField()
    risk_level = models.CharField(max_length=10, choices=RiskLevel.choices)
    
    # Agent signals incorporated
    technical_signal = models.ForeignKey(
        AgentSignal, 
        on_delete=models.CASCADE, 
        related_name='technical_decisions',
        null=True
    )
    macro_signal = models.ForeignKey(
        AgentSignal, 
        on_delete=models.CASCADE, 
        related_name='macro_decisions',
        null=True
    )
    sentiment_signal = models.ForeignKey(
        AgentSignal, 
        on_delete=models.CASCADE, 
        related_name='sentiment_decisions',
        null=True
    )
    
    # Weights used
    weights = models.JSONField(default=dict)  # {'technical': 0.5, 'macro': 0.3, 'sentiment': 0.2}
    
    # Explanation
    reasoning = models.TextField()
    
    # Market regime context
    volatility_regime = models.CharField(max_length=20, default='normal')
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['symbol', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.symbol} - {self.decision} ({self.confidence:.2f}) - {self.risk_level}"


class AgentPerformance(models.Model):
    """Track agent performance over time"""
    
    agent_type = models.CharField(max_length=20)
    symbol = models.CharField(max_length=20)
    date = models.DateField(db_index=True)
    
    # Performance metrics
    accuracy = models.FloatField(default=0.0)
    precision = models.FloatField(default=0.0)
    recall = models.FloatField(default=0.0)
    sharpe_ratio = models.FloatField(default=0.0)
    
    # Signal counts
    total_signals = models.IntegerField(default=0)
    correct_signals = models.IntegerField(default=0)
    
    # Current weight in coordinator
    current_weight = models.FloatField(default=0.333)
    
    class Meta:
        unique_together = ['agent_type', 'symbol', 'date']
        ordering = ['-date']

