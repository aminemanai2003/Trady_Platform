"""
Risk Manager Module
Centralized risk control with absolute veto power
Enforces position sizing, stop-loss, drawdown limits
"""
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

from django.conf import settings
from risk.position_sizer import PositionSizer

logger = logging.getLogger(__name__)


# Risk configuration (can be overridden in Django settings)
RISK_CONFIG = {
    'MAX_RISK_PER_TRADE_PCT': getattr(settings, 'MAX_RISK_PER_TRADE_PCT', 2.0),
    'MAX_DRAWDOWN_PCT': getattr(settings, 'MAX_DRAWDOWN_PCT', 15.0),
    'MIN_RR_RATIO': getattr(settings, 'MIN_RR_RATIO', 1.5),
    'MAX_CONCURRENT_POSITIONS': getattr(settings, 'MAX_CONCURRENT_POSITIONS', 4),
    'MIN_CONFIDENCE': getattr(settings, 'MIN_CONFIDENCE', 0.50),
    'MIN_EV_PIPS': getattr(settings, 'MIN_EV_PIPS', 5.0),
    'STOP_LOSS_ATR_MULTIPLIER': getattr(settings, 'STOP_LOSS_ATR_MULTIPLIER', 1.5),
    'TAKE_PROFIT_ATR_MULTIPLIER': getattr(settings, 'TAKE_PROFIT_ATR_MULTIPLIER', 2.5),
}


class RiskManager:
    """
    Centralized Risk Management with absolute veto power.
    Can override Judge-approved trades if risk parameters violated.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize RiskManager with configuration.
        
        Args:
            config: Optional risk configuration override
        """
        self.config = config or RISK_CONFIG
        self.position_sizer = PositionSizer()
    
    def validate_trade(
        self,
        signal: int,
        confidence: float,
        symbol: str,
        entry_price: float,
        atr: float,
        capital: float,
        current_equity: float,
        peak_equity: float,
        current_positions: int,
        expected_value_pips: float = 0.0,
        win_rate: float = 0.55,
        avg_win: float = 1.5,
        avg_loss: float = 1.0
    ) -> Dict:
        """
        Validate trade against all risk parameters.
        ABSOLUTE VETO: Returns approved=False if any limit violated.
        
        Args:
            signal: Trading signal (1=BUY, -1=SELL, 0=NEUTRAL)
            confidence: Signal confidence (0-1)
            symbol: Trading symbol
            entry_price: Proposed entry price
            atr: Average True Range
            capital: Total account capital
            current_equity: Current account equity
            peak_equity: Peak equity (for drawdown calculation)
            current_positions: Number of open positions
            expected_value_pips: Expected value from actuarial scorer
            win_rate: Historical win rate
            avg_win: Average win size
            avg_loss: Average loss size
        
        Returns:
            Dict with 'approved', 'reason', 'position_size', 'stop_loss', 'take_profit', etc.
        """
        violations = []
        
        # 1. Check confidence threshold
        if confidence < self.config['MIN_CONFIDENCE']:
            violations.append(
                f"Confidence {confidence:.2f} below minimum {self.config['MIN_CONFIDENCE']}"
            )
        
        # 2. Check neutral signal (should not trade)
        if signal == 0:
            violations.append("NEUTRAL signal - no directional bias")
        
        # 3. Check expected value
        if expected_value_pips < self.config['MIN_EV_PIPS']:
            violations.append(
                f"Expected value {expected_value_pips:.2f} pips below minimum {self.config['MIN_EV_PIPS']}"
            )
        
        # 4. Check drawdown
        drawdown_pct = self._calculate_drawdown(current_equity, peak_equity)
        if drawdown_pct < -self.config['MAX_DRAWDOWN_PCT']:
            violations.append(
                f"Drawdown {drawdown_pct:.2f}% exceeds limit {-self.config['MAX_DRAWDOWN_PCT']}%"
            )
        
        # 5. Check concurrent positions
        if current_positions >= self.config['MAX_CONCURRENT_POSITIONS']:
            violations.append(
                f"Max concurrent positions {self.config['MAX_CONCURRENT_POSITIONS']} reached"
            )
        
        # Calculate position sizing (even if rejected, for audit trail)
        sizing = self.position_sizer.combined_size(
            capital=capital,
            confidence=confidence,
            atr=atr,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            risk_pct=self.config['MAX_RISK_PER_TRADE_PCT'] / 100
        )
        
        # 6. Check risk/reward ratio
        rr_ratio = sizing['take_profit_pips'] / sizing['stop_loss_pips'] if sizing['stop_loss_pips'] > 0 else 0
        if rr_ratio < self.config['MIN_RR_RATIO']:
            violations.append(
                f"Risk/Reward ratio {rr_ratio:.2f} below minimum {self.config['MIN_RR_RATIO']}"
            )
        
        # 7. Check risk per trade
        if sizing['risk_pct'] > self.config['MAX_RISK_PER_TRADE_PCT']:
            violations.append(
                f"Risk per trade {sizing['risk_pct']:.2f}% exceeds limit {self.config['MAX_RISK_PER_TRADE_PCT']}%"
            )
        
        # Calculate stop-loss and take-profit prices
        stop_loss_price = self.position_sizer.calculate_stop_loss(
            entry_price, atr, signal, self.config['STOP_LOSS_ATR_MULTIPLIER']
        )
        take_profit_price = self.position_sizer.calculate_take_profit(
            entry_price, atr, signal, self.config['TAKE_PROFIT_ATR_MULTIPLIER']
        )
        
        # Decision
        approved = len(violations) == 0
        
        if approved:
            reason = "All risk parameters satisfied"
            logger.info(f"Trade APPROVED: {symbol} {signal} @ {entry_price:.5f}")
        else:
            reason = f"Risk violations: {'; '.join(violations)}"
            logger.warning(f"Trade REJECTED: {symbol} - {reason}")
        
        return {
            'approved': approved,
            'reason': reason,
            'violations': violations,
            'position_size': sizing['lot_size'] if approved else 0.0,
            'stop_loss': stop_loss_price if approved else None,
            'take_profit': take_profit_price if approved else None,
            'stop_loss_pips': sizing['stop_loss_pips'],
            'take_profit_pips': sizing['take_profit_pips'],
            'risk_reward_ratio': rr_ratio,
            'risk_pct': sizing['risk_pct'],
            'risk_amount': sizing['risk_amount'],
            'kelly_fraction': sizing['kelly_fraction'],
            'drawdown_pct': drawdown_pct,
            'current_positions': current_positions,
            'max_positions': self.config['MAX_CONCURRENT_POSITIONS'],
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_drawdown(self, current_equity: float, peak_equity: float) -> float:
        """
        Calculate current drawdown percentage.
        
        Args:
            current_equity: Current account equity
            peak_equity: Peak equity in history
        
        Returns:
            Drawdown as negative percentage (e.g., -12.5 for 12.5% drawdown)
        """
        if peak_equity <= 0:
            return 0.0
        drawdown = ((current_equity - peak_equity) / peak_equity) * 100
        return min(0.0, drawdown)  # Always <= 0
    
    def check_emergency_stop(
        self,
        current_equity: float,
        peak_equity: float
    ) -> Dict:
        """
        Emergency stop check - should halt all trading.
        
        Args:
            current_equity: Current account equity
            peak_equity: Peak equity in history
        
        Returns:
            Dict with 'emergency_stop', 'reason', 'drawdown_pct'
        """
        drawdown_pct = self._calculate_drawdown(current_equity, peak_equity)
        emergency_stop = drawdown_pct < -self.config['MAX_DRAWDOWN_PCT']
        
        if emergency_stop:
            reason = f"EMERGENCY STOP: Drawdown {drawdown_pct:.2f}% exceeds limit {-self.config['MAX_DRAWDOWN_PCT']}%"
            logger.critical(reason)
        else:
            reason = f"Within limits: Drawdown {drawdown_pct:.2f}%"
        
        return {
            'emergency_stop': emergency_stop,
            'reason': reason,
            'drawdown_pct': drawdown_pct,
            'threshold': -self.config['MAX_DRAWDOWN_PCT']
        }
    
    def get_available_risk(
        self,
        capital: float,
        current_equity: float,
        peak_equity: float,
        current_positions: int
    ) -> Dict:
        """
        Calculate available risk capacity.
        
        Args:
            capital: Total account capital
            current_equity: Current equity
            peak_equity: Peak equity
            current_positions: Current open positions
        
        Returns:
            Dict with available risk metrics
        """
        drawdown_pct = self._calculate_drawdown(current_equity, peak_equity)
        drawdown_remaining = self.config['MAX_DRAWDOWN_PCT'] + drawdown_pct  # How much before limit
        positions_remaining = self.config['MAX_CONCURRENT_POSITIONS'] - current_positions
        
        max_risk_per_trade = capital * (self.config['MAX_RISK_PER_TRADE_PCT'] / 100)
        
        return {
            'max_risk_per_trade_usd': max_risk_per_trade,
            'max_risk_per_trade_pct': self.config['MAX_RISK_PER_TRADE_PCT'],
            'drawdown_current_pct': drawdown_pct,
            'drawdown_remaining_pct': drawdown_remaining,
            'positions_current': current_positions,
            'positions_remaining': positions_remaining,
            'can_trade': positions_remaining > 0 and drawdown_remaining > 0,
            'config': self.config
        }
