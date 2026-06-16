"""
Position Sizing Module
Kelly Criterion + ATR-based risk management (DSO2.3)

Extracted from backend/backtesting/engine_v2.py for centralized use
"""
from typing import Dict


class PositionSizer:
    """
    Position sizing using Kelly Criterion + ATR-based risk management (DSO2.3).
    """

    @staticmethod
    def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Kelly fraction = W - (1-W)/R
        where W = win rate, R = win/loss ratio
        
        Args:
            win_rate: Historical win rate (0.0 to 1.0)
            avg_win: Average winning trade size
            avg_loss: Average losing trade size
        
        Returns:
            Kelly fraction (0.0 to 0.25, half-Kelly for safety)
        """
        if avg_loss == 0 or win_rate <= 0:
            return 0.0
        R = abs(avg_win / avg_loss)
        kelly = win_rate - (1 - win_rate) / R
        # Half-Kelly for safety
        return max(0.0, min(kelly * 0.5, 0.25))

    @staticmethod
    def atr_based_size(
        capital: float,
        atr: float,
        risk_pct: float = 0.02,
        pip_value: float = 10.0
    ) -> float:
        """
        ATR-based position sizing:
        size = (capital × risk%) / (ATR × pip_value)
        
        Args:
            capital: Account capital
            atr: Average True Range
            risk_pct: Risk percentage per trade (default 2%)
            pip_value: Value per pip (default $10 for standard lot)
        
        Returns:
            Position size in lots (0.01 to 10.0)
        """
        if atr <= 0:
            return 0.01
        risk_amount = capital * risk_pct
        size = risk_amount / (atr * pip_value)
        return max(0.01, min(size, 10.0))  # 0.01 to 10 lots

    @staticmethod
    def combined_size(
        capital: float,
        confidence: float,
        atr: float,
        win_rate: float = 0.55,
        avg_win: float = 1.5,
        avg_loss: float = 1.0,
        risk_pct: float = 0.02
    ) -> Dict:
        """
        Combined position sizing using Kelly + ATR.
        Returns sizing recommendation with explanation.
        
        Args:
            capital: Account capital
            confidence: Signal confidence (0.0 to 1.0)
            atr: Average True Range
            win_rate: Historical win rate (default 55%)
            avg_win: Average winning trade size (default 1.5%)
            avg_loss: Average losing trade size (default 1.0%)
            risk_pct: Base risk percentage (default 2%)
        
        Returns:
            Dict with lot_size, kelly_fraction, risk metrics, SL/TP
        """
        kelly_frac = PositionSizer.kelly_criterion(win_rate, avg_win, avg_loss)
        atr_size = PositionSizer.atr_based_size(capital, atr, risk_pct)

        # Blend: 60% ATR-based + 40% Kelly-adjusted
        kelly_size = kelly_frac * capital / (atr * 10.0) if atr > 0 else 0.01
        blended = 0.6 * atr_size + 0.4 * kelly_size

        # Adjust by confidence
        final_size = blended * confidence

        # Risk per trade
        risk_amount = final_size * atr * 10.0
        risk_pct_actual = risk_amount / capital * 100 if capital > 0 else 0

        return {
            'lot_size': round(max(0.01, min(final_size, 10.0)), 2),
            'kelly_fraction': round(kelly_frac, 4),
            'atr_size': round(atr_size, 2),
            'risk_amount': round(risk_amount, 2),
            'risk_pct': round(risk_pct_actual, 2),
            'stop_loss_pips': round(atr * 10000 * 1.5, 1),  # 1.5 × ATR
            'take_profit_pips': round(atr * 10000 * 2.5, 1),  # 2.5 × ATR (RR = 1:1.67)
        }

    @staticmethod
    def calculate_stop_loss(
        entry_price: float,
        atr: float,
        signal: int,
        atr_multiplier: float = 1.5
    ) -> float:
        """
        Calculate stop-loss price based on ATR.
        
        Args:
            entry_price: Entry price
            atr: Average True Range
            signal: 1 for BUY, -1 for SELL
            atr_multiplier: ATR multiplier (default 1.5)
        
        Returns:
            Stop-loss price
        """
        stop_distance = atr * atr_multiplier
        if signal == 1:  # BUY
            return entry_price - stop_distance
        elif signal == -1:  # SELL
            return entry_price + stop_distance
        return entry_price

    @staticmethod
    def calculate_take_profit(
        entry_price: float,
        atr: float,
        signal: int,
        atr_multiplier: float = 2.5
    ) -> float:
        """
        Calculate take-profit price based on ATR.
        
        Args:
            entry_price: Entry price
            atr: Average True Range
            signal: 1 for BUY, -1 for SELL
            atr_multiplier: ATR multiplier (default 2.5)
        
        Returns:
            Take-profit price
        """
        tp_distance = atr * atr_multiplier
        if signal == 1:  # BUY
            return entry_price + tp_distance
        elif signal == -1:  # SELL
            return entry_price - tp_distance
        return entry_price
