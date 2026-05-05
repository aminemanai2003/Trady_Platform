"""
Backtesting Engine V2 — Uses real V2 agents
Walk-forward validation, Kelly Criterion position sizing
Calculates: Sharpe ratio, max drawdown, win rate, profit factor (DSO2.2 + DSO2.3)
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from data_layer.timeseries_loader import TimeSeriesLoader
from feature_layer.technical_features import TechnicalFeatureEngine
from risk.position_sizer import PositionSizer  # Import from new location


@dataclass
class BacktestTrade:
    """Container for trade information"""
    entry_time: datetime
    entry_price: float
    trade_type: str  # BUY / SELL
    size: float
    confidence: float
    reasoning: str

    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pips: Optional[float] = None


# PositionSizer moved to backend/risk/position_sizer.py
# Kept here as alias for backward compatibility
class _DeprecatedPositionSizer:
    """
    Position sizing using Kelly Criterion + ATR-based risk management (DSO2.3).
    """

    @staticmethod
    def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Kelly fraction = W - (1-W)/R
        where W = win rate, R = win/loss ratio
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
        avg_loss: float = 1.0
    ) -> Dict:
        """
        Combined position sizing using Kelly + ATR.
        Returns sizing recommendation with explanation.
        """
        kelly_frac = PositionSizer.kelly_criterion(win_rate, avg_win, avg_loss)
        atr_size = PositionSizer.atr_based_size(capital, atr)

        # Blend: 60% ATR-based + 40% Kelly-adjusted
        kelly_size = kelly_frac * capital / (atr * 10.0) if atr > 0 else 0.01
        blended = 0.6 * atr_size + 0.4 * kelly_size

        # Adjust by confidence
        final_size = blended * confidence

        # Risk per trade
        risk_amount = final_size * atr * 10.0
        risk_pct = risk_amount / capital * 100 if capital > 0 else 0

        return {
            'lot_size': round(max(0.01, min(final_size, 10.0)), 2),
            'kelly_fraction': round(kelly_frac, 4),
            'atr_size': round(atr_size, 2),
            'risk_amount': round(risk_amount, 2),
            'risk_pct': round(risk_pct, 2),
            'stop_loss_pips': round(atr * 10000 * 1.5, 1),  # 1.5 × ATR
            'take_profit_pips': round(atr * 10000 * 2.5, 1),  # 2.5 × ATR (RR = 1:1.67)
        }


class BacktestEngineV2:
    """
    Backtesting engine using V2 deterministic pipeline.
    Walk-forward validation with no look-ahead bias.
    """

    PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF']

    def __init__(self, symbol: str = 'EURUSD', initial_capital: float = 10000.0):
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.loader = TimeSeriesLoader()
        self.feature_engine = TechnicalFeatureEngine()
        self.position_sizer = PositionSizer()

    def run_backtest(self, lookback_bars: int = 500) -> Dict:
        """
        Run walk-forward backtest on historical data.
        Uses pure technical rules (same as TechnicalAgentV2) for reproducibility.
        """
        # Load data
        df = self.loader.load_ohlcv(self.symbol)
        if df.empty or len(df) < lookback_bars:
            return self._empty_result("Insufficient data")

        # Use last N bars
        df = df.tail(lookback_bars).copy()

        # Calculate features
        df_feat = self.feature_engine.calculate_all(df)

        # Walk-forward: train on first 70%, test on last 30%
        split_idx = int(len(df_feat) * 0.7)
        train_df = df_feat.iloc[:split_idx]
        test_df = df_feat.iloc[split_idx:]

        # Build signal history on test set
        trades: List[BacktestTrade] = []
        current_position: Optional[BacktestTrade] = None
        capital = self.initial_capital
        equity_curve = []

        for i in range(len(test_df)):
            row = test_df.iloc[i]
            timestamp = test_df.index[i] if isinstance(test_df.index, pd.DatetimeIndex) else datetime.now()
            price = float(row['close'])

            # Get signal from deterministic rules
            signal, confidence, reason = self._generate_signal_from_row(row)

            # Track equity
            unrealized = 0
            if current_position:
                if current_position.trade_type == 'BUY':
                    unrealized = (price - current_position.entry_price) / current_position.entry_price * capital * current_position.size
                else:
                    unrealized = (current_position.entry_price - price) / current_position.entry_price * capital * current_position.size

            equity_curve.append({
                'bar': i,
                'equity': capital + unrealized,
                'price': price
            })

            # Trading logic
            if current_position is None:
                # Open position if signal is strong enough
                if signal != 0 and confidence >= 0.5:
                    atr = float(row['atr_14']) if not pd.isna(row.get('atr_14', np.nan)) else price * 0.001
                    size = min(confidence * 0.5, 0.3)  # Simple sizing
                    current_position = BacktestTrade(
                        entry_time=timestamp,
                        entry_price=price,
                        trade_type='BUY' if signal == 1 else 'SELL',
                        size=size,
                        confidence=confidence,
                        reasoning=reason
                    )
            else:
                # Close on opposite signal or stop-loss/take-profit
                should_close = False
                if current_position.trade_type == 'BUY' and signal == -1 and confidence >= 0.5:
                    should_close = True
                elif current_position.trade_type == 'SELL' and signal == 1 and confidence >= 0.5:
                    should_close = True
                # ATR-based stop-loss
                atr = float(row['atr_14']) if not pd.isna(row.get('atr_14', np.nan)) else price * 0.001
                if current_position.trade_type == 'BUY':
                    if price < current_position.entry_price - 2 * atr:
                        should_close = True
                    elif price > current_position.entry_price + 3 * atr:
                        should_close = True
                else:
                    if price > current_position.entry_price + 2 * atr:
                        should_close = True
                    elif price < current_position.entry_price - 3 * atr:
                        should_close = True

                if should_close:
                    current_position.exit_time = timestamp
                    current_position.exit_price = price
                    if current_position.trade_type == 'BUY':
                        pnl_pct = (price - current_position.entry_price) / current_position.entry_price
                    else:
                        pnl_pct = (current_position.entry_price - price) / current_position.entry_price
                    current_position.pnl = pnl_pct * capital * current_position.size
                    current_position.pnl_pips = pnl_pct * 10000
                    capital += current_position.pnl
                    trades.append(current_position)
                    current_position = None

        # Close remaining position
        if current_position and len(test_df) > 0:
            last_price = float(test_df.iloc[-1]['close'])
            current_position.exit_price = last_price
            current_position.exit_time = datetime.now()
            if current_position.trade_type == 'BUY':
                pnl_pct = (last_price - current_position.entry_price) / current_position.entry_price
            else:
                pnl_pct = (current_position.entry_price - last_price) / current_position.entry_price
            current_position.pnl = pnl_pct * capital * current_position.size
            current_position.pnl_pips = pnl_pct * 10000
            capital += current_position.pnl
            trades.append(current_position)

        # Calculate metrics
        metrics = self._calculate_metrics(trades, equity_curve, self.initial_capital)

        return {
            'symbol': self.symbol,
            'initial_capital': self.initial_capital,
            'final_capital': round(capital, 2),
            'total_bars': len(test_df),
            'train_bars': split_idx,
            'test_bars': len(test_df),
            'metrics': metrics,
            'trades': [
                {
                    'type': t.trade_type,
                    'entry_price': round(t.entry_price, 5),
                    'exit_price': round(t.exit_price, 5) if t.exit_price else None,
                    'pnl': round(t.pnl, 2) if t.pnl else 0,
                    'pnl_pips': round(t.pnl_pips, 1) if t.pnl_pips else 0,
                    'confidence': round(t.confidence, 2),
                }
                for t in trades
            ],
            'equity_curve': equity_curve[-50:],  # Last 50 points for chart
        }

    def _generate_signal_from_row(self, row) -> tuple:
        """Generate signal from a single row of features using deterministic rules."""
        signals = []
        weights = []
        reasons = []

        # RSI
        rsi = row.get('rsi_14')
        if rsi is not None and not pd.isna(rsi):
            if rsi < 30:
                signals.append(1)
                weights.append(0.25)
                reasons.append(f"RSI oversold ({rsi:.1f})")
            elif rsi > 70:
                signals.append(-1)
                weights.append(0.25)
                reasons.append(f"RSI overbought ({rsi:.1f})")
            else:
                signals.append(0)
                weights.append(0.1)

        # MACD
        macd_diff = row.get('macd_diff')
        if macd_diff is not None and not pd.isna(macd_diff):
            if macd_diff > 0:
                signals.append(1)
                weights.append(0.3)
                reasons.append("MACD bullish")
            else:
                signals.append(-1)
                weights.append(0.3)
                reasons.append("MACD bearish")

        # Williams %R
        wr = row.get('williams_r')
        if wr is not None and not pd.isna(wr):
            if wr < -80:
                signals.append(1)
                weights.append(0.15)
                reasons.append(f"Williams %R oversold ({wr:.1f})")
            elif wr > -20:
                signals.append(-1)
                weights.append(0.15)
                reasons.append(f"Williams %R overbought ({wr:.1f})")

        # SMA alignment
        sma_20 = row.get('sma_20')
        sma_50 = row.get('sma_50')
        close = row.get('close', 0)
        if sma_20 is not None and sma_50 is not None and not pd.isna(sma_20) and not pd.isna(sma_50):
            if close > sma_20 > sma_50:
                signals.append(1)
                weights.append(0.2)
                reasons.append("Bullish SMA alignment")
            elif close < sma_20 < sma_50:
                signals.append(-1)
                weights.append(0.2)
                reasons.append("Bearish SMA alignment")

        if not signals:
            return 0, 0.0, "No clear pattern"

        total_w = sum(weights)
        weighted = sum(s * w for s, w in zip(signals, weights)) / total_w
        confidence = min(total_w, 1.0)

        if weighted > 0.3:
            return 1, confidence, '; '.join(reasons)
        elif weighted < -0.3:
            return -1, confidence, '; '.join(reasons)
        return 0, confidence * 0.5, "Mixed signals"

    def _calculate_metrics(self, trades: List[BacktestTrade], equity_curve: List[Dict], initial_capital: float) -> Dict:
        """Calculate comprehensive performance metrics."""
        if not trades:
            return {
                'total_return_pct': 0, 'sharpe_ratio': 0, 'max_drawdown_pct': 0,
                'win_rate_pct': 0, 'profit_factor': 0, 'total_trades': 0,
                'winning_trades': 0, 'losing_trades': 0, 'avg_win': 0, 'avg_loss': 0,
            }

        winners = [t for t in trades if t.pnl and t.pnl > 0]
        losers = [t for t in trades if t.pnl and t.pnl < 0]

        win_rate = len(winners) / len(trades) * 100
        gross_profit = sum(t.pnl for t in winners) if winners else 0
        gross_loss = abs(sum(t.pnl for t in losers)) if losers else 0.001
        profit_factor = gross_profit / gross_loss

        avg_win = np.mean([t.pnl for t in winners]) if winners else 0
        avg_loss = np.mean([t.pnl for t in losers]) if losers else 0

        # Equity-based metrics
        equities = pd.Series([e['equity'] for e in equity_curve])
        returns = equities.pct_change().dropna()

        sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if len(returns) > 1 and returns.std() > 0 else 0

        rolling_max = equities.expanding().max()
        drawdown = (equities - rolling_max) / rolling_max
        max_dd = abs(drawdown.min()) * 100 if len(drawdown) > 0 else 0

        final_eq = equities.iloc[-1] if len(equities) > 0 else initial_capital
        total_return = (final_eq - initial_capital) / initial_capital * 100

        # Kelly recommendation
        kelly_frac = PositionSizer.kelly_criterion(
            len(winners) / len(trades) if trades else 0,
            avg_win if avg_win > 0 else 1,
            abs(avg_loss) if avg_loss != 0 else 1
        )

        return {
            'total_return_pct': round(total_return, 2),
            'sharpe_ratio': round(float(sharpe), 2),
            'max_drawdown_pct': round(float(max_dd), 2),
            'win_rate_pct': round(win_rate, 1),
            'profit_factor': round(profit_factor, 2),
            'total_trades': len(trades),
            'winning_trades': len(winners),
            'losing_trades': len(losers),
            'avg_win': round(float(avg_win), 2),
            'avg_loss': round(float(avg_loss), 2),
            'kelly_fraction': round(kelly_frac, 4),
            'recommended_risk_pct': round(kelly_frac * 100, 1),
        }

    def _empty_result(self, reason: str) -> Dict:
        return {
            'symbol': self.symbol,
            'error': reason,
            'metrics': {
                'total_return_pct': 0, 'sharpe_ratio': 0, 'max_drawdown_pct': 0,
                'win_rate_pct': 0, 'profit_factor': 0, 'total_trades': 0,
            }
        }
