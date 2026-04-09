"""
Actuarial Scorer Module
Probabilistic reasoning for trading decisions
Calculates Expected Value, P(win), Risk/Reward ratios
"""
from typing import Dict, Optional
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
    
    def get_historical_stats(
        self,
        agent_name: str = None,
        symbol: str = None,
        confidence_range: tuple = (0.4, 1.0),
        lookback_days: int = 100
    ) -> Dict:
        """
        Get historical performance statistics.
        This would query the database for actual historical performance.
        
        Args:
            agent_name: Optional agent filter
            symbol: Optional symbol filter
            confidence_range: Confidence range to filter (min, max)
            lookback_days: Days to look back
        
        Returns:
            Dict with win_rate, avg_win_pips, avg_loss_pips
        """
        # TODO: Implement database query
        # For now, return conservative defaults
        logger.warning("Using default historical stats - implement database query")
        
        return {
            'win_rate': 0.55,
            'avg_win_pips': 42,
            'avg_loss_pips': 35,
            'total_trades': 100,
            'sample_size': 100,
            'confidence_range': confidence_range,
            'lookback_days': lookback_days
        }
