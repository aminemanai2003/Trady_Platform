"""
Actuarial Scorer Module
Probabilistic reasoning for trading decisions
Calculates Expected Value, P(win), Risk/Reward ratios
"""
from typing import Dict, Optional, List
import numpy as np
import logging

logger = logging.getLogger(__name__)


class ActuarialScorer:
    """
    Actuarial analysis for trading decisions.
    Converts confidence and historical performance into expected value.
    """
    
    def __init__(self):
        """Initialize ActuarialScorer"""
        pass
    
    def score_trade(
        self,
        coordinator_output: Dict,
        historical_stats: Optional[Dict] = None
    ) -> Dict:
        """
        Score a trade using actuarial analysis.
        
        Args:
            coordinator_output: Output from CoordinatorAgentV2
            historical_stats: Optional historical performance stats
        
        Returns:
            Dict with EV, P(win), RR ratio, recommendation
        """
        # Extract signal and confidence
        signal = coordinator_output.get('final_signal', 0)
        confidence = coordinator_output.get('confidence', 0.5)
        
        # Get historical stats or use defaults
        if historical_stats:
            win_rate = historical_stats.get('win_rate', 0.55)
            avg_win_pips = historical_stats.get('avg_win_pips', 42)
            avg_loss_pips = historical_stats.get('avg_loss_pips', 35)
        else:
            # Default conservative estimates
            win_rate = 0.55
            avg_win_pips = 42
            avg_loss_pips = 35
        
        # Estimate probabilities from confidence
        probabilities = self.estimate_probabilities(
            confidence, 
            signal,
            base_win_rate=win_rate
        )
        
        # Calculate expected value
        ev_pips = self.calculate_ev(
            probabilities['p_win'],
            probabilities['p_loss'],
            avg_win_pips,
            avg_loss_pips
        )
        
        # Calculate risk/reward ratio
        rr_ratio = self.calculate_risk_reward(avg_win_pips, avg_loss_pips)
        
        # Kelly Criterion fraction
        kelly_fraction = self.calculate_kelly_fraction(
            probabilities['p_win'],
            avg_win_pips,
            avg_loss_pips
        )
        
        # Recommendation
        recommendation = self._determine_recommendation(
            ev_pips, 
            probabilities['p_win'], 
            rr_ratio,
            confidence
        )
        
        return {
            'expected_value_pips': round(ev_pips, 2),
            'expected_value_usd': round(ev_pips * 10, 2),  # Assuming $10/pip
            'probability_win': round(probabilities['p_win'], 4),
            'probability_loss': round(probabilities['p_loss'], 4),
            'probability_neutral': round(probabilities['p_neutral'], 4),
            'risk_reward_ratio': round(rr_ratio, 2),
            'kelly_fraction': round(kelly_fraction, 4),
            'avg_win_pips': avg_win_pips,
            'avg_loss_pips': avg_loss_pips,
            'recommendation': recommendation,
            'verdict': 'TRADE' if ev_pips > 5.0 and probabilities['p_win'] > 0.52 else 'NO_TRADE'
        }
    
    def estimate_probabilities(
        self,
        confidence: float,
        signal: int,
        base_win_rate: float = 0.55
    ) -> Dict[str, float]:
        """
        Convert confidence score to P(win), P(loss), P(neutral).
        
        Args:
            confidence: Signal confidence (0-1)
            signal: Trading signal (1=BUY, -1=SELL, 0=NEUTRAL)
            base_win_rate: Historical base win rate
        
        Returns:
            Dict with p_win, p_loss, p_neutral
        """
        if signal == 0:  # NEUTRAL
            return {
                'p_win': 0.0,
                'p_loss': 0.0,
                'p_neutral': 1.0
            }
        
        # Adjust base win rate by confidence
        # High confidence → higher win probability
        # Low confidence → closer to 50/50
        confidence_adjusted = base_win_rate + (confidence - 0.5) * 0.3
        p_win = np.clip(confidence_adjusted, 0.4, 0.75)
        p_loss = 1.0 - p_win
        
        return {
            'p_win': p_win,
            'p_loss': p_loss,
            'p_neutral': 0.0
        }
    
    def calculate_ev(
        self,
        p_win: float,
        p_loss: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """
        Calculate Expected Value.
        EV = P(win) × avg_win - P(loss) × avg_loss
        
        Args:
            p_win: Probability of win
            p_loss: Probability of loss
            avg_win: Average winning trade size
            avg_loss: Average losing trade size
        
        Returns:
            Expected value
        """
        ev = p_win * avg_win - p_loss * avg_loss
        return ev
    
    def calculate_risk_reward(
        self,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """
        Calculate Risk/Reward ratio.
        RR = avg_win / avg_loss
        
        Args:
            avg_win: Average winning trade size
            avg_loss: Average losing trade size
        
        Returns:
            Risk/Reward ratio
        """
        if avg_loss == 0:
            return 0.0
        return avg_win / avg_loss
    
    def calculate_kelly_fraction(
        self,
        p_win: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """
        Calculate Kelly Criterion fraction.
        Kelly = W - (1-W)/R where W=win_rate, R=win/loss ratio
        
        Args:
            p_win: Probability of win
            avg_win: Average winning trade size
            avg_loss: Average losing trade size
        
        Returns:
            Kelly fraction (half-Kelly for safety)
        """
        if avg_loss == 0 or p_win <= 0:
            return 0.0
        R = avg_win / avg_loss
        kelly = p_win - (1 - p_win) / R
        # Half-Kelly for conservative sizing
        return max(0.0, min(kelly * 0.5, 0.25))
    
    def _determine_recommendation(
        self,
        ev: float,
        p_win: float,
        rr_ratio: float,
        confidence: float
    ) -> str:
        """
        Determine trading recommendation.
        
        Args:
            ev: Expected value
            p_win: Probability of win
            rr_ratio: Risk/reward ratio
            confidence: Signal confidence
        
        Returns:
            Recommendation string
        """
        if ev < 0:
            return "Negative expected value - avoid"
        elif ev < 5:
            return "Marginally profitable - low priority"
        elif ev < 15 and p_win < 0.55:
            return "Acceptable but not compelling"
        elif ev >= 15 and p_win >= 0.60 and rr_ratio >= 1.5:
            return "Strong setup - high priority"
        elif ev >= 10 and p_win >= 0.55:
            return "Good setup - tradeable"
        else:
            return "Positive but conditional - monitor"
    
    # Conservative Bayesian priors — used when sample size is small
    _PRIOR_WIN_RATE = 0.50
    _PRIOR_AVG_WIN_PIPS = 40.0
    _PRIOR_AVG_LOSS_PIPS = 38.0
    _PRIOR_SAMPLE_WEIGHT = 20  # virtual prior trades for blending

    def get_historical_stats(
        self,
        agent_name: str = None,
        symbol: str = None,
        confidence_range: tuple = (0.4, 1.0),
        lookback_days: int = 100
    ) -> Dict:
        """
        Get historical performance statistics from closed PaperPosition records.

        Uses Bayesian blending with conservative priors when sample < 20 trades,
        so the system remains stable during cold start while still using real data.

        Args:
            agent_name: Optional agent filter (unused for now — portfolio-level)
            symbol: Optional symbol filter (pair)
            confidence_range: Confidence range to filter (min, max)
            lookback_days: Days to look back

        Returns:
            Dict with win_rate, avg_win_pips, avg_loss_pips, total_trades, etc.
        """
        try:
            return self._query_real_stats(symbol, confidence_range, lookback_days)
        except Exception as exc:
            logger.warning(f"Failed to query real stats: {exc} — using priors")
            return self._prior_stats(confidence_range, lookback_days)

    def _query_real_stats(
        self,
        symbol: Optional[str],
        confidence_range: tuple,
        lookback_days: int,
    ) -> Dict:
        from paper_trading.models import PaperPosition
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(days=lookback_days)

        qs = PaperPosition.objects.filter(
            status="CLOSED",
            closed_at__gte=cutoff,
        )
        if symbol:
            qs = qs.filter(pair=symbol)

        closed = list(qs.values("pnl", "entry_price", "current_price", "side", "pair"))
        total_trades = len(closed)

        if total_trades == 0:
            logger.info("No closed paper trades yet — using pure priors")
            return self._prior_stats(confidence_range, lookback_days)

        # Calculate observed stats
        wins = [t for t in closed if t["pnl"] > 0]
        losses = [t for t in closed if t["pnl"] <= 0]

        observed_wr = len(wins) / total_trades if total_trades > 0 else 0.5

        def _pips(trade):
            """Convert price diff to pips."""
            pair = trade.get("pair", "")
            pip_div = 0.01 if "JPY" in pair else 0.0001
            diff = abs(trade["current_price"] - trade["entry_price"]) / pip_div
            return diff

        observed_avg_win = (
            np.mean([_pips(t) for t in wins]) if wins else self._PRIOR_AVG_WIN_PIPS
        )
        observed_avg_loss = (
            np.mean([_pips(t) for t in losses]) if losses else self._PRIOR_AVG_LOSS_PIPS
        )

        # Bayesian blending: blend observed with priors weighted by sample size
        n = total_trades
        p = self._PRIOR_SAMPLE_WEIGHT

        blended_wr = (n * observed_wr + p * self._PRIOR_WIN_RATE) / (n + p)
        blended_avg_win = (n * observed_avg_win + p * self._PRIOR_AVG_WIN_PIPS) / (n + p)
        blended_avg_loss = (n * observed_avg_loss + p * self._PRIOR_AVG_LOSS_PIPS) / (n + p)

        logger.info(
            f"Actuarial stats: {total_trades} trades, "
            f"observed_wr={observed_wr:.2f} → blended={blended_wr:.2f}, "
            f"avg_win={blended_avg_win:.1f} pips, avg_loss={blended_avg_loss:.1f} pips"
        )

        return {
            'win_rate': round(float(blended_wr), 4),
            'avg_win_pips': round(float(blended_avg_win), 1),
            'avg_loss_pips': round(float(blended_avg_loss), 1),
            'total_trades': total_trades,
            'sample_size': total_trades,
            'confidence_range': confidence_range,
            'lookback_days': lookback_days,
            'source': 'paper_trades' if n >= p else 'blended_with_priors',
        }

    def _prior_stats(self, confidence_range: tuple, lookback_days: int) -> Dict:
        """Return conservative prior estimates (no real data available)."""
        return {
            'win_rate': self._PRIOR_WIN_RATE,
            'avg_win_pips': self._PRIOR_AVG_WIN_PIPS,
            'avg_loss_pips': self._PRIOR_AVG_LOSS_PIPS,
            'total_trades': 0,
            'sample_size': 0,
            'confidence_range': confidence_range,
            'lookback_days': lookback_days,
            'source': 'priors',
        }
