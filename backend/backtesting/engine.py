"""
PHASE 5: Backtesting Engine
Walk-forward validation with no look-ahead bias
Calculates performance metrics: Sharpe, MDD, win rate, profit factor
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from core.database import TimeSeriesQuery
from agents.coordinator import CoordinatorAgent
from backtesting.models import BacktestRun, BacktestTrade


@dataclass
class Trade:
    """Container for trade information"""
    entry_time: datetime
    entry_price: float
    trade_type: str  # BUY/SELL
    size: float
    confidence: float
    risk_level: str
    reasoning: str
    
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None


class BacktestEngine:
    """
    Backtesting engine with walk-forward validation
    No look-ahead bias
    """
    
    def __init__(self, symbol: str, start_date: datetime, end_date: datetime,
                 initial_capital: float = 10000.0):
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        
        self.coordinator = CoordinatorAgent()
        
        # State
        self.current_position = None  # Current open trade
        self.trades: List[Trade] = []
        self.equity_curve = []
        self.current_capital = initial_capital
    
    def run(self, name: str = "Backtest") -> Dict:
        """
        Run backtest using walk-forward validation
        Returns performance metrics
        """
        
        # Create backtest run record
        backtest_run = BacktestRun.objects.create(
            name=name,
            symbol=self.symbol,
            start_date=self.start_date,
            end_date=self.end_date,
            strategy_config={'agent': 'coordinator'},
            status=BacktestRun.Status.RUNNING
        )
        
        try:
            # Fetch price data
            price_data = self._fetch_price_data()
            
            # Walk forward through time
            current_date = self.start_date
            
            while current_date <= self.end_date:
                # Get coordinator decision at this point in time
                try:
                    decision_result = self.coordinator.make_decision(self.symbol, current_date)
                    
                    # Execute trading logic
                    self._process_decision(decision_result, current_date, price_data)
                    
                except Exception as e:
                    print(f"Error at {current_date}: {e}")
                
                # Move forward (e.g., daily)
                current_date += timedelta(days=1)
                
                # Track equity
                equity = self._calculate_current_equity(current_date, price_data)
                self.equity_curve.append({
                    'date': current_date,
                    'equity': equity
                })
            
            # Close any remaining position
            if self.current_position:
                self._close_position(self.end_date, price_data)
            
            # Calculate performance metrics
            metrics = self._calculate_metrics()
            
            # Update backtest run
            backtest_run.status = BacktestRun.Status.COMPLETED
            backtest_run.completed_at = datetime.now()
            backtest_run.total_return = metrics['total_return']
            backtest_run.sharpe_ratio = metrics['sharpe_ratio']
            backtest_run.max_drawdown = metrics['max_drawdown']
            backtest_run.win_rate = metrics['win_rate']
            backtest_run.profit_factor = metrics['profit_factor']
            backtest_run.total_trades = len(self.trades)
            backtest_run.winning_trades = len([t for t in self.trades if t.pnl and t.pnl > 0])
            backtest_run.losing_trades = len([t for t in self.trades if t.pnl and t.pnl < 0])
            backtest_run.metrics = metrics
            backtest_run.save()
            
            # Save all trades
            self._save_trades(backtest_run)
            
            return {
                'backtest_id': backtest_run.id,
                'metrics': metrics,
                'trades': len(self.trades),
                'equity_curve': self.equity_curve
            }
        
        except Exception as e:
            backtest_run.status = BacktestRun.Status.FAILED
            backtest_run.save()
            raise e
    
    def _fetch_price_data(self) -> pd.DataFrame:
        """Fetch OHLCV price data for backtest period"""
        
        result = TimeSeriesQuery.query_ohlcv(
            self.symbol,
            self.start_date.isoformat(),
            self.end_date.isoformat()
        )
        
        records = []
        for table in result:
            for record in table.records:
                records.append({
                    'time': record.get_time(),
                    'open': record.values.get('open'),
                    'high': record.values.get('high'),
                    'low': record.values.get('low'),
                    'close': record.values.get('close'),
                    'volume': record.values.get('volume', 0)
                })
        
        df = pd.DataFrame(records)
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time').reset_index(drop=True)
        df = df.set_index('time')
        
        return df
    
    def _process_decision(self, decision: Dict, timestamp: datetime, 
                         price_data: pd.DataFrame):
        """Process coordinator decision and execute trades"""
        
        decision_signal = decision['decision']
        confidence = decision['confidence']
        risk_level = decision['risk_level']
        reasoning = decision['reasoning']
        
        # Get current price
        current_price = self._get_price_at_time(timestamp, price_data)
        
        if current_price is None:
            return
        
        # Decision logic
        if self.current_position is None:
            # No position - consider opening
            if decision_signal == 'BUY' and confidence >= 0.5:
                self._open_position('BUY', timestamp, current_price, 
                                   confidence, risk_level, reasoning)
            elif decision_signal == 'SELL' and confidence >= 0.5:
                self._open_position('SELL', timestamp, current_price, 
                                   confidence, risk_level, reasoning)
        
        else:
            # Have position - consider closing
            position_type = self.current_position.trade_type
            
            # Close on opposite signal or low confidence
            if position_type == 'BUY' and decision_signal == 'SELL' and confidence >= 0.5:
                self._close_position(timestamp, price_data)
            elif position_type == 'SELL' and decision_signal == 'BUY' and confidence >= 0.5:
                self._close_position(timestamp, price_data)
            elif decision_signal == 'NEUTRAL' and confidence >= 0.6:
                # Strong neutral signal - close position
                self._close_position(timestamp, price_data)
    
    def _open_position(self, trade_type: str, timestamp: datetime, 
                      price: float, confidence: float, risk_level: str, 
                      reasoning: str):
        """Open a new position"""
        
        # Calculate position size based on risk
        size = self._calculate_position_size(confidence, risk_level)
        
        trade = Trade(
            entry_time=timestamp,
            entry_price=price,
            trade_type=trade_type,
            size=size,
            confidence=confidence,
            risk_level=risk_level,
            reasoning=reasoning
        )
        
        self.current_position = trade
        print(f"Opened {trade_type} position at {price} (size: {size}, confidence: {confidence:.2f})")
    
    def _close_position(self, timestamp: datetime, price_data: pd.DataFrame):
        """Close current position"""
        
        if self.current_position is None:
            return
        
        exit_price = self._get_price_at_time(timestamp, price_data)
        
        if exit_price is None:
            return
        
        self.current_position.exit_time = timestamp
        self.current_position.exit_price = exit_price
        
        # Calculate P&L
        if self.current_position.trade_type == 'BUY':
            pnl_percent = (exit_price - self.current_position.entry_price) / self.current_position.entry_price
        else:  # SELL
            pnl_percent = (self.current_position.entry_price - exit_price) / self.current_position.entry_price
        
        pnl = pnl_percent * self.current_capital * self.current_position.size
        
        self.current_position.pnl = pnl
        self.current_position.pnl_percent = pnl_percent * 100
        
        # Update capital
        self.current_capital += pnl
        
        # Save trade
        self.trades.append(self.current_position)
        
        print(f"Closed position at {exit_price} - P&L: {pnl:.2f} ({pnl_percent*100:.2f}%)")
        
        self.current_position = None
    
    def _calculate_position_size(self, confidence: float, risk_level: str) -> float:
        """
        Calculate position size based on confidence and risk
        Returns fraction of capital to risk (0 to 1)
        """
        
        base_size = confidence  # Use confidence as base
        
        # Adjust for risk level
        risk_multipliers = {
            'LOW': 1.2,
            'MEDIUM': 1.0,
            'HIGH': 0.6
        }
        
        multiplier = risk_multipliers.get(risk_level, 1.0)
        
        # Calculate final size
        size = base_size * multiplier
        
        # Cap at reasonable limits
        return min(max(size, 0.1), 1.0)
    
    def _get_price_at_time(self, timestamp: datetime, 
                          price_data: pd.DataFrame) -> Optional[float]:
        """Get price at specific timestamp (using close price)"""
        
        # Find closest timestamp
        try:
            closest_idx = price_data.index.get_indexer([timestamp], method='nearest')[0]
            return price_data.iloc[closest_idx]['close']
        except:
            return None
    
    def _calculate_current_equity(self, timestamp: datetime, 
                                  price_data: pd.DataFrame) -> float:
        """Calculate current equity including unrealized P&L"""
        
        equity = self.current_capital
        
        # Add unrealized P&L if position open
        if self.current_position:
            current_price = self._get_price_at_time(timestamp, price_data)
            if current_price:
                if self.current_position.trade_type == 'BUY':
                    unrealized_pnl = (current_price - self.current_position.entry_price) / self.current_position.entry_price
                else:
                    unrealized_pnl = (self.current_position.entry_price - current_price) / self.current_position.entry_price
                
                equity += unrealized_pnl * self.current_capital * self.current_position.size
        
        return equity
    
    def _calculate_metrics(self) -> Dict:
        """Calculate comprehensive performance metrics"""
        
        if len(self.trades) == 0:
            return {
                'total_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'win_rate': 0,
                'profit_factor': 0
            }
        
        # Total return
        final_equity = self.equity_curve[-1]['equity'] if self.equity_curve else self.initial_capital
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        # Trade statistics
        winning_trades = [t for t in self.trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl and t.pnl < 0]
        
        win_rate = len(winning_trades) / len(self.trades) if self.trades else 0
        
        # Profit factor
        gross_profit = sum([t.pnl for t in winning_trades]) if winning_trades else 0
        gross_loss = abs(sum([t.pnl for t in losing_trades])) if losing_trades else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Sharpe ratio
        if len(self.equity_curve) > 1:
            equity_series = pd.Series([e['equity'] for e in self.equity_curve])
            returns = equity_series.pct_change().dropna()
            
            if len(returns) > 0 and returns.std() > 0:
                sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)  # Annualized
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        # Maximum drawdown
        equity_series = pd.Series([e['equity'] for e in self.equity_curve])
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0
        
        return {
            'total_return': float(total_return),
            'total_return_pct': float(total_return * 100),
            'sharpe_ratio': float(sharpe_ratio),
            'max_drawdown': float(max_drawdown),
            'max_drawdown_pct': float(max_drawdown * 100),
            'win_rate': float(win_rate),
            'win_rate_pct': float(win_rate * 100),
            'profit_factor': float(profit_factor),
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'avg_win': float(np.mean([t.pnl for t in winning_trades])) if winning_trades else 0,
            'avg_loss': float(np.mean([t.pnl for t in losing_trades])) if losing_trades else 0,
            'final_equity': float(final_equity)
        }
    
    def _save_trades(self, backtest_run: BacktestRun):
        """Save all trades to database"""
        
        trades_to_create = []
        
        for trade in self.trades:
            trades_to_create.append(
                BacktestTrade(
                    backtest=backtest_run,
                    trade_type=trade.trade_type,
                    entry_time=trade.entry_time,
                    exit_time=trade.exit_time,
                    entry_price=trade.entry_price,
                    exit_price=trade.exit_price,
                    size=trade.size,
                    pnl=trade.pnl,
                    pnl_percent=trade.pnl_percent,
                    decision_confidence=trade.confidence,
                    risk_level=trade.risk_level,
                    entry_reasoning=trade.reasoning
                )
            )
        
        BacktestTrade.objects.bulk_create(trades_to_create, batch_size=1000)
