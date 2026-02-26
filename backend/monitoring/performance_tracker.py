"""
Performance Tracker - Monitor agent performance over time
"""
from typing import Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from core.database import DatabaseManager


class PerformanceTracker:
    """
    Track rolling performance metrics per agent
    
    Metrics:
    - Sharpe Ratio (30-day rolling)
    - Win Rate
    - Avg Profit/Loss
    - Max Drawdown
    """
    
    def __init__(self):
        self.db = DatabaseManager()
    
    def record_signal_outcome(
        self,
        agent_name: str,
        signal: int,
        entry_price: float,
        exit_price: float,
        timestamp: datetime
    ):
        """Record an agent's signal outcome"""
        pnl = (exit_price - entry_price) / entry_price if signal == 1 else (entry_price - exit_price) / entry_price
        
        with self.db.get_postgres_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO agent_performance_log
                (agent_name, signal, entry_price, exit_price, pnl, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (agent_name, signal, entry_price, exit_price, pnl, timestamp))
            conn.commit()
    
    def get_agent_performance(
        self,
        agent_name: str,
        days: int = 30
    ) -> Dict:
        """
        Calculate rolling performance metrics
        
        Returns:
            {
                'sharpe_ratio': float,
                'win_rate': float,
                'avg_pnl': float,
                'max_drawdown': float,
                'trade_count': int
            }
        """
        start_date = datetime.now() - timedelta(days=days)
        
        with self.db.get_postgres_connection() as conn:
            query = """
            SELECT pnl, timestamp
            FROM agent_performance_log
            WHERE agent_name = %s
            AND timestamp >= %s
            ORDER BY timestamp
            """
            df = pd.read_sql(query, conn, params=(agent_name, start_date))
        
        if df.empty:
            return {
                'sharpe_ratio': 0.0,
                'win_rate': 0.0,
                'avg_pnl': 0.0,
                'max_drawdown': 0.0,
                'trade_count': 0
            }
        
        # Calculate metrics
        returns = df['pnl'].values
        
        sharpe = self._calculate_sharpe(returns)
        win_rate = (returns > 0).sum() / len(returns)
        avg_pnl = returns.mean()
        max_dd = self._calculate_max_drawdown(returns)
        
        return {
            'sharpe_ratio': float(sharpe),
            'win_rate': float(win_rate),
            'avg_pnl': float(avg_pnl),
            'max_drawdown': float(max_dd),
            'trade_count': len(returns)
        }
    
    @staticmethod
    def _calculate_sharpe(returns: np.ndarray, risk_free_rate: float = 0.0) -> float:
        """Calculate Sharpe ratio"""
        if len(returns) < 2:
            return 0.0
        
        excess_returns = returns - risk_free_rate
        if excess_returns.std() == 0:
            return 0.0
        
        return excess_returns.mean() / excess_returns.std() * np.sqrt(252)  # Annualized
    
    @staticmethod
    def _calculate_max_drawdown(returns: np.ndarray) -> float:
        """Calculate maximum drawdown"""
        cumulative = (1 + returns).cumprod()
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        return float(drawdown.min())
    
    def should_disable_agent(
        self,
        agent_name: str,
        min_sharpe: float = -0.5,
        max_drawdown: float = -0.20
    ) -> bool:
        """
        Check if agent should be disabled due to poor performance
        
        Safety mechanism: Disable agents with:
        - Sharpe < -0.5 (consistent losses)
        - Drawdown > 20%
        """
        perf = self.get_agent_performance(agent_name, days=30)
        
        if perf['trade_count'] < 10:
            return False  # Need more data
        
        if perf['sharpe_ratio'] < min_sharpe:
            return True
        
        if perf['max_drawdown'] < max_drawdown:
            return True
        
        return False
    
    def get_all_agents_performance(self, days: int = 30) -> Dict[str, Dict]:
        """Get performance summary for all agents"""
        agents = ['TechnicalV2', 'MacroV2', 'SentimentV2']
        
        return {
            agent: self.get_agent_performance(agent, days)
            for agent in agents
        }
