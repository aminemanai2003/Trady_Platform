"""
Django models for backtesting results
"""
from django.db import models


class BacktestRun(models.Model):
    """Record of a backtest execution"""
    
    class Status(models.TextChoices):
        RUNNING = 'running', 'Running'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
    
    name = models.CharField(max_length=200)
    symbol = models.CharField(max_length=20)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Strategy configuration
    strategy_config = models.JSONField(default=dict)
    
    # Execution
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RUNNING)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Performance metrics
    total_return = models.FloatField(null=True)
    sharpe_ratio = models.FloatField(null=True)
    max_drawdown = models.FloatField(null=True)
    win_rate = models.FloatField(null=True)
    profit_factor = models.FloatField(null=True)
    
    # Trade statistics
    total_trades = models.IntegerField(default=0)
    winning_trades = models.IntegerField(default=0)
    losing_trades = models.IntegerField(default=0)
    
    # Additional metrics
    metrics = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['symbol', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.symbol} ({self.status})"


class BacktestTrade(models.Model):
    """Individual trade in a backtest"""
    
    class TradeType(models.TextChoices):
        BUY = 'BUY', 'Buy'
        SELL = 'SELL', 'Sell'
    
    backtest = models.ForeignKey(BacktestRun, on_delete=models.CASCADE, related_name='trades')
    
    # Trade details
    trade_type = models.CharField(max_length=4, choices=TradeType.choices)
    entry_time = models.DateTimeField()
    exit_time = models.DateTimeField(null=True)
    
    entry_price = models.FloatField()
    exit_price = models.FloatField(null=True)
    
    # Position size
    size = models.FloatField(default=1.0)
    
    # Performance
    pnl = models.FloatField(null=True)  # Profit/Loss
    pnl_percent = models.FloatField(null=True)
    
    # Decision context
    decision_confidence = models.FloatField()
    risk_level = models.CharField(max_length=20)
    
    # Metadata
    entry_reasoning = models.TextField(blank=True)
    
    class Meta:
        ordering = ['entry_time']
        indexes = [
            models.Index(fields=['backtest', 'entry_time']),
        ]
    
    def __str__(self):
        return f"{self.trade_type} @ {self.entry_price} ({self.pnl_percent:.2f}%)"
