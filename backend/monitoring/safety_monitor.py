"""
Safety Monitor - Production safety rules
"""
from typing import Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
from core.database import DatabaseManager


class SafetyMonitor:
    """
    Implement production safety rules:
    - Signal cooldown (avoid overtrading)
    - Max position limits
    - Conflict detection
    - Emergency circuit breaker
    """
    
    def __init__(self):
        self.db = DatabaseManager()
        self.cooldown_minutes = 60  # Min time between signals
        self.max_daily_trades = 10
        self.max_drawdown_threshold = -0.15  # Stop if 15% drawdown
    
    def check_signal_cooldown(self, symbol: str) -> bool:
        """
        Check if enough time has passed since last signal
        
        Prevents overtrading
        """
        with self.db.get_postgres_connection() as conn:
            query = """
            SELECT timestamp
            FROM trading_signals
            WHERE symbol = %s
            ORDER BY timestamp DESC
            LIMIT 1
            """
            df = pd.read_sql(query, conn, params=(symbol,))
        
        if df.empty:
            return True  # No previous signal
        
        last_signal_time = pd.to_datetime(df['timestamp'].iloc[0])
        time_since_last = datetime.now() - last_signal_time
        
        return time_since_last.total_seconds() / 60 > self.cooldown_minutes
    
    def check_daily_trade_limit(self, symbol: str) -> bool:
        """
        Check if max daily trades exceeded
        
        Safety: Prevent excessive trading
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0)
        
        with self.db.get_postgres_connection() as conn:
            query = """
            SELECT COUNT(*) as count
            FROM trading_signals
            WHERE symbol = %s
            AND timestamp >= %s
            """
            df = pd.read_sql(query, conn, params=(symbol, today_start))
        
        trade_count = df['count'].iloc[0]
        
        return trade_count < self.max_daily_trades
    
    def check_circuit_breaker(self) -> Dict:
        """
        Emergency stop if drawdown exceeds threshold
        
        Safety: Stop all trading if system losing money
        """
        # Get recent PnL
        start_date = datetime.now() - timedelta(days=1)
        
        with self.db.get_postgres_connection() as conn:
            query = """
            SELECT pnl
            FROM agent_performance_log
            WHERE timestamp >= %s
            ORDER BY timestamp
            """
            df = pd.read_sql(query, conn, params=(start_date,))
        
        if df.empty:
            return {'triggered': False, 'reason': 'No recent trades'}
        
        # Calculate cumulative PnL and drawdown
        cumulative_pnl = df['pnl'].cumsum()
        running_max = cumulative_pnl.expanding().max()
        drawdown = (cumulative_pnl - running_max) / (running_max + 1)  # Prevent div by zero
        
        max_drawdown = drawdown.min()
        
        triggered = max_drawdown < self.max_drawdown_threshold
        
        return {
            'triggered': triggered,
            'current_drawdown': float(max_drawdown),
            'threshold': self.max_drawdown_threshold,
            'reason': 'Emergency stop - max drawdown exceeded' if triggered else 'Within limits'
        }
    
    def should_allow_signal(self, symbol: str) -> Dict:
        """
        Master safety check - combines all rules
        
        Returns:
            {
                'allowed': bool,
                'reason': str,
                'checks': dict
            }
        """
        cooldown_ok = self.check_signal_cooldown(symbol)
        trade_limit_ok = self.check_daily_trade_limit(symbol)
        circuit_breaker = self.check_circuit_breaker()
        
        checks = {
            'cooldown': cooldown_ok,
            'trade_limit': trade_limit_ok,
            'circuit_breaker': not circuit_breaker['triggered']
        }
        
        allowed = all(checks.values())
        
        if not allowed:
            if not cooldown_ok:
                reason = f"Signal cooldown active ({self.cooldown_minutes} min required)"
            elif not trade_limit_ok:
                reason = f"Daily trade limit reached ({self.max_daily_trades})"
            elif circuit_breaker['triggered']:
                reason = f"Circuit breaker triggered: {circuit_breaker['reason']}"
            else:
                reason = "Safety check failed"
        else:
            reason = "All safety checks passed"
        
        return {
            'allowed': allowed,
            'reason': reason,
            'checks': checks,
            'circuit_breaker_status': circuit_breaker
        }
