"""
Performance Tracker — Monitor agent performance over time.

Uses Django ORM against the AgentOutcome model (paper_trading app).
No PostgreSQL dependency — everything lives in Django's default DB (SQLite).
"""
from typing import Dict
from datetime import datetime, timedelta
import numpy as np
import logging

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """
    Track rolling performance metrics per agent.

    Metrics:
    - Sharpe Ratio (per-trade, not annualised)
    - Win Rate
    - Avg P&L
    - Max Drawdown
    """

    def record_agent_outcome(
        self,
        agent_name: str,
        pair: str,
        signal_direction: str,
        confidence: float,
        was_correct: bool,
        pnl: float,
        weight_used: float = 0.0,
        paper_position=None,
    ):
        """Record an agent's signal outcome after a paper trade settles."""
        from paper_trading.models import AgentOutcome

        AgentOutcome.objects.create(
            agent_name=agent_name,
            pair=pair,
            signal_direction=signal_direction,
            confidence=confidence,
            was_correct=was_correct,
            pnl=pnl,
            weight_used=weight_used,
            paper_position=paper_position,
        )
        logger.info(
            f"AgentOutcome recorded: {agent_name} {signal_direction} {pair} "
            f"correct={was_correct} pnl={pnl:.4f}"
        )

    def get_agent_performance(
        self,
        agent_name: str,
        days: int = 30,
    ) -> Dict:
        """
        Calculate rolling performance metrics from AgentOutcome records.

        Returns:
            {
                'sharpe_ratio': float,
                'win_rate': float,
                'avg_pnl': float,
                'max_drawdown': float,
                'trade_count': int,
                'avg_confidence': float,
                'period_days_used': int,
            }
        """
        from paper_trading.models import AgentOutcome

        empty_result = {
            'sharpe_ratio': 0.0,
            'win_rate': 0.0,
            'avg_pnl': 0.0,
            'max_drawdown': 0.0,
            'trade_count': 0,
            'avg_confidence': 0.0,
            'period_days_used': days,
        }

        # Expand window progressively if short period has too few records
        windows = [days, 90, 365, 3650]
        qs = None
        used_days = days

        try:
            for window in windows:
                cutoff = datetime.now() - timedelta(days=window)
                qs = AgentOutcome.objects.filter(
                    agent_name=agent_name,
                    created_at__gte=cutoff,
                ).order_by("created_at")
                if qs.exists():
                    used_days = window
                    break

            if qs is None or not qs.exists():
                return empty_result

            records = list(qs.values("pnl", "was_correct", "confidence"))
        except Exception as exc:
            logger.warning(f"PerformanceTracker query failed for {agent_name}: {exc}")
            return empty_result

        # Separate outcomes with P&L from pending ones
        pnl_records = [r for r in records if r["pnl"] is not None]
        if not pnl_records:
            avg_conf = np.mean([r["confidence"] for r in records]) if records else 0.0
            return {
                **empty_result,
                'trade_count': len(records),
                'avg_confidence': float(avg_conf),
                'period_days_used': used_days,
            }

        pnls = np.array([r["pnl"] for r in pnl_records])
        confs = np.array([r["confidence"] for r in records])

        sharpe = self._calculate_sharpe(pnls)
        win_rate = float((pnls > 0).sum() / len(pnls))
        avg_pnl = float(pnls.mean())
        max_dd = self._calculate_max_drawdown(pnls)
        avg_conf = float(confs.mean()) if len(confs) > 0 else 0.0

        return {
            'sharpe_ratio': float(sharpe),
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'max_drawdown': float(max_dd),
            'trade_count': len(pnl_records),
            'avg_confidence': avg_conf,
            'period_days_used': used_days,
        }

    @staticmethod
    def _calculate_sharpe(returns: np.ndarray, risk_free_rate: float = 0.0) -> float:
        """
        Per-trade Sharpe ratio (no annualisation).
        Typical range: -2 to +2 for real strategies.
        """
        if len(returns) < 2:
            return 0.0
        excess = returns - risk_free_rate
        std = excess.std()
        if std == 0:
            return 0.0
        return float(excess.mean() / std)

    @staticmethod
    def _calculate_max_drawdown(returns: np.ndarray) -> float:
        """Maximum drawdown from cumulative returns."""
        cumulative = (1 + returns).cumprod()
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        return float(drawdown.min())

    def should_disable_agent(
        self,
        agent_name: str,
        min_sharpe: float = -0.5,
        max_drawdown: float = -0.20,
    ) -> bool:
        """
        Safety: disable agents with persistent losses.
        Sharpe < -0.5 or drawdown > 20% over last 30 days.
        """
        perf = self.get_agent_performance(agent_name, days=30)
        if perf['trade_count'] < 10:
            return False
        return perf['sharpe_ratio'] < min_sharpe or perf['max_drawdown'] < max_drawdown

    def get_all_agents_performance(self, days: int = 30) -> Dict[str, Dict]:
        """Get performance summary for all agents."""
        agents = ['TechnicalV2', 'MacroV2', 'SentimentV2', 'GeopoliticalV2']
        return {agent: self.get_agent_performance(agent, days) for agent in agents}
