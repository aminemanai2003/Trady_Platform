"""
Trading Decision Pipeline
Orchestrates the complete decision flow:
Coordinator → Actuarial → Judge → Risk → XAI → Final Decision
"""
from typing import Dict, Optional
from datetime import datetime
import logging

from signal_layer.coordinator_agent_v2 import CoordinatorAgentV2
from decision_layer.actuarial_scorer import ActuarialScorer
from decision_layer.llm_judge import LLMJudge
from decision_layer.llm_tool_judge import LLMToolJudge
from decision_layer.xai_formatter import XAIFormatter
from risk.risk_manager import RiskManager
from data_layer.timeseries_loader import TimeSeriesLoader

logger = logging.getLogger(__name__)


class TradingDecisionPipeline:
    """
    Complete trading decision pipeline with all validation layers.
    
    Flow:
    1. CoordinatorAgentV2: Aggregate agent signals
    2. ActuarialScorer: Calculate EV, P(win), RR
    3. LLMJudge: Validate decision (APPROVE/REJECT/MODIFY)
    4. RiskManager: Final veto power (absolute authority)
    5. XAIFormatter: Generate human-readable explanation
    
    Returns: Approved trade with position sizing OR rejection with reason
    """
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        peak_equity: Optional[float] = None
    ):
        """
        Initialize trading decision pipeline.
        
        Args:
            initial_capital: Starting capital
            peak_equity: Peak equity for drawdown calculation (defaults to initial_capital)
        """
        self.coordinator = CoordinatorAgentV2()
        self.actuarial_scorer = ActuarialScorer()
        self.llm_tool_judge = LLMToolJudge()   # Stage 2.5 — advisory only
        self.llm_judge = LLMJudge()
        self.risk_manager = RiskManager()
        self.xai_formatter = XAIFormatter()
        self.loader = TimeSeriesLoader()
        
        self.capital = initial_capital
        self.current_equity = initial_capital
        self.peak_equity = peak_equity or initial_capital
        self.current_positions = 0
        
        logger.info(f"TradingDecisionPipeline initialized with capital: ${initial_capital}")
    
    def execute(
        self,
        symbol: str,
        base_currency: str,
        quote_currency: str,
        entry_price: Optional[float] = None,
        market_context: Optional[Dict] = None
    ) -> Dict:
        """
        Execute complete trading decision pipeline.
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            base_currency: Base currency (e.g., 'EUR')
            quote_currency: Quote currency (e.g., 'USD')
            entry_price: Optional entry price (auto-detected if not provided)
            market_context: Optional additional market context
        
        Returns:
            Dict with decision, position sizing, explanation, or rejection reason
        """
        logger.info(f"=== Starting decision pipeline for {symbol} ===")
        
        try:
            # Step 1: Get coordinator decision
            logger.info("Step 1: CoordinatorAgentV2 aggregation")
            coordinator_output = self.coordinator.generate_final_signal(
                symbol=symbol,
                base_currency=base_currency,
                quote_currency=quote_currency
            )
            coordinator_output['symbol'] = symbol  # Ensure symbol is set
            
            logger.info(
                f"Coordinator: {coordinator_output.get('final_signal')} signal, "
                f"confidence {coordinator_output.get('confidence', 0):.2f}, "
                f"conflicts: {coordinator_output.get('conflicts_detected', False)}"
            )
            
            # Get current price and ATR
            price_data = self._get_price_data(symbol)
            if entry_price is None:
                entry_price = price_data['current_price']
            atr = price_data['atr']
            
            # Step 2: Actuarial scoring
            logger.info("Step 2: ActuarialScorer analysis")
            historical_stats = self.actuarial_scorer.get_historical_stats(
                symbol=symbol,
                confidence_range=(0.4, 1.0),
                lookback_days=100
            )
            actuarial_scores = self.actuarial_scorer.score_trade(
                coordinator_output,
                historical_stats
            )

            logger.info(
                f"Actuarial: EV={actuarial_scores.get('expected_value_pips', 0):.2f} pips, "
                f"P(win)={actuarial_scores.get('probability_win', 0):.2%}, "
                f"RR={actuarial_scores.get('risk_reward_ratio', 0):.2f}"
            )

            # Step 2.5: LLM Tool Judge — advisory metadata (never blocks pipeline)
            logger.info("Step 2.5: LLMToolJudge advisory analysis")
            tool_judge_output = self.llm_tool_judge.analyze(
                coordinator_output,
                actuarial_scores,
                market_context
            )
            logger.info(
                f"ToolJudge: flags={tool_judge_output.get('risk_flags')} "
                f"adj={tool_judge_output.get('confidence_adjustment', 0):+.3f} "
                f"({tool_judge_output.get('latency_ms', 0)}ms)"
            )

            # Apply confidence adjustment from tool judge (clamped, advisory)
            conf_adj = tool_judge_output.get('confidence_adjustment', 0.0)
            if conf_adj != 0.0:
                old_conf = coordinator_output.get('confidence', 0.5)
                coordinator_output['confidence'] = max(0.0, min(1.0, old_conf + conf_adj))
                logger.info(
                    f"ToolJudge adjusted confidence: {old_conf:.3f} → {coordinator_output['confidence']:.3f}"
                )
            
            # Early rejection check
            if actuarial_scores.get('expected_value_pips', 0) < 0:
                logger.warning("Early rejection: Negative expected value")
                return self._build_rejection_response(
                    coordinator_output,
                    actuarial_scores,
                    {
                        'verdict': 'REJECT',
                        'reasoning': 'Negative expected value - trade has negative expectancy',
                        'latency_ms': 0,
                        'rejection_criteria': ['negative_ev'],
                        'from_cache': False
                    },
                    {
                        'approved': False,
                        'reason': 'Skipped due to early rejection',
                        'violations': ['negative_ev']
                    },
                    market_context,
                    tool_judge_output
                )
            
            # Step 3: LLM Judge validation
            logger.info("Step 3: LLM Judge validation")
            judge_decision = self.llm_judge.evaluate(
                coordinator_output,
                actuarial_scores,
                market_context
            )
            
            logger.info(
                f"Judge: {judge_decision['verdict']} "
                f"({judge_decision.get('latency_ms', 0)}ms) - {judge_decision['reasoning']}"
            )
            
            # If Judge rejects, skip risk validation
            if judge_decision['verdict'] == 'REJECT':
                logger.warning("Trade rejected by LLM Judge")
                return self._build_rejection_response(
                    coordinator_output,
                    actuarial_scores,
                    judge_decision,
                    {
                        'approved': False,
                        'reason': 'Skipped due to Judge rejection',
                        'violations': judge_decision.get('rejection_criteria', [])
                    },
                    market_context,
                    tool_judge_output
                )
            
            # Adjust confidence if Judge modified
            if judge_decision['verdict'] == 'MODIFY':
                adjusted_conf = judge_decision.get('confidence_adjusted')
                if adjusted_conf:
                    logger.info(f"Judge modified confidence: {coordinator_output['confidence']:.2f} → {adjusted_conf:.2f}")
                    coordinator_output['confidence'] = adjusted_conf
            
            # Step 4: Risk Manager validation (ABSOLUTE VETO POWER)
            logger.info("Step 4: RiskManager validation (absolute veto)")
            risk_validation = self.risk_manager.validate_trade(
                signal=coordinator_output.get('final_signal', 0),
                confidence=coordinator_output.get('confidence', 0.5),
                symbol=symbol,
                entry_price=entry_price,
                atr=atr,
                capital=self.capital,
                current_equity=self.current_equity,
                peak_equity=self.peak_equity,
                current_positions=self.current_positions,
                expected_value_pips=actuarial_scores.get('expected_value_pips', 0),
                win_rate=historical_stats.get('win_rate', 0.55),
                avg_win=historical_stats.get('avg_win_pips', 42),
                avg_loss=historical_stats.get('avg_loss_pips', 35)
            )
            
            logger.info(
                f"Risk: {'APPROVED' if risk_validation['approved'] else 'REJECTED'} - "
                f"{risk_validation['reason']}"
            )
            
            # If Risk Manager rejects, final decision is REJECT
            if not risk_validation['approved']:
                logger.warning("Trade rejected by RiskManager (absolute veto)")
                return self._build_rejection_response(
                    coordinator_output,
                    actuarial_scores,
                    judge_decision,
                    risk_validation,
                    market_context,
                    tool_judge_output
                )
            
            # Step 5: Build XAI explanation
            logger.info("Step 5: XAI formatting")
            xai_output = self.xai_formatter.format(
                coordinator_output,
                actuarial_scores,
                judge_decision,
                risk_validation,
                market_context
            )
            
            # Build final response
            logger.info(f"=== TRADE APPROVED: {symbol} ===")
            
            return {
                'status': 'success',
                'decision': xai_output['decision'],
                'signal': coordinator_output.get('final_signal', 0),
                'signal_name': self._signal_name(coordinator_output.get('final_signal', 0)),
                'confidence': coordinator_output.get('confidence', 0.5),
                'symbol': symbol,
                'entry_price': entry_price,
                'position_size': risk_validation['position_size'],
                'stop_loss': risk_validation['stop_loss'],
                'take_profit': risk_validation['take_profit'],
                'stop_loss_pips': risk_validation['stop_loss_pips'],
                'take_profit_pips': risk_validation['take_profit_pips'],
                'risk_pct': risk_validation['risk_pct'],
                'expected_value_pips': actuarial_scores['expected_value_pips'],
                'probability_win': actuarial_scores['probability_win'],
                'tool_judge': tool_judge_output,
                'xai': xai_output,
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Pipeline error for {symbol}: {e}", exc_info=True)
            return {
                'status': 'error',
                'decision': 'ERROR',
                'symbol': symbol,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _build_rejection_response(
        self,
        coordinator_output: Dict,
        actuarial_scores: Dict,
        judge_decision: Dict,
        risk_validation: Dict,
        market_context: Optional[Dict],
        tool_judge_output: Optional[Dict] = None,
    ) -> Dict:
        """
        Build rejection response with XAI.

        Args:
            coordinator_output:  Coordinator output
            actuarial_scores:    Actuarial scores
            judge_decision:      Judge decision
            risk_validation:     Risk validation
            market_context:      Market context
            tool_judge_output:   Advisory LLMToolJudge metadata (optional)

        Returns:
            Rejection response dict
        """
        xai_output = self.xai_formatter.format(
            coordinator_output,
            actuarial_scores,
            judge_decision,
            risk_validation,
            market_context
        )

        return {
            'status': 'rejected',
            'decision': xai_output['decision'],
            'symbol': coordinator_output.get('symbol', 'UNKNOWN'),
            'signal': coordinator_output.get('final_signal', 0),
            'signal_name': self._signal_name(coordinator_output.get('final_signal', 0)),
            'confidence': coordinator_output.get('confidence', 0.5),
            'rejection_stage': xai_output.get('rejection_stage'),
            'rejection_reason': xai_output.get('rejection_reason'),
            'tool_judge': tool_judge_output,
            'xai': xai_output,
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_price_data(self, symbol: str) -> Dict:
        """
        Get current price and ATR for symbol.

        Fallback chain:
          1. InfluxDB / SQLite via TimeSeriesLoader
          2. yfinance direct call (free, no API key)
          3. Raise — never return a fake price

        Args:
            symbol: Trading symbol

        Returns:
            Dict with current_price and atr

        Raises:
            RuntimeError: if no real price data can be obtained
        """
        # --- Attempt 1: TimeSeriesLoader (InfluxDB → SQLite) ---
        try:
            df = self.loader.load_ohlcv(symbol)
            if not df.empty:
                current_price = float(df['close'].iloc[-1])
                if 'atr' in df.columns:
                    atr = float(df['atr'].iloc[-1])
                else:
                    atr = float((df['high'] - df['low']).tail(14).mean())
                logger.info(f"Price data for {symbol}: price={current_price}, atr={atr}")
                return {'current_price': current_price, 'atr': atr}
            logger.warning(f"TimeSeriesLoader returned empty df for {symbol}")
        except Exception as e:
            logger.warning(f"TimeSeriesLoader failed for {symbol}: {e}")

        # --- Attempt 2: yfinance direct call ---
        try:
            import yfinance as yf
            _TICKER_MAP = {
                'EURUSD': 'EURUSD=X', 'USDJPY': 'USDJPY=X',
                'GBPUSD': 'GBPUSD=X', 'USDCHF': 'USDCHF=X',
            }
            ticker_str = _TICKER_MAP.get(symbol, f'{symbol}=X')
            hist = yf.Ticker(ticker_str).history(period='5d', interval='1h')
            if hist is not None and not hist.empty:
                current_price = float(hist['Close'].iloc[-1])
                atr = float((hist['High'] - hist['Low']).tail(14).mean())
                logger.info(f"yfinance fallback for {symbol}: price={current_price}, atr={atr}")
                return {'current_price': current_price, 'atr': atr}
            logger.warning(f"yfinance returned empty history for {symbol}")
        except Exception as e:
            logger.warning(f"yfinance fallback failed for {symbol}: {e}")

        # --- No real price available — abort rather than using a fake price ---
        raise RuntimeError(
            f"Cannot obtain real price data for {symbol}. "
            f"Both TimeSeriesLoader and yfinance failed. "
            f"Pipeline cannot proceed with a fake entry price."
        )
    
    def _signal_name(self, signal: int) -> str:
        """Convert signal integer to name"""
        return {-1: 'SELL', 0: 'NEUTRAL', 1: 'BUY'}.get(signal, 'UNKNOWN')
    
    def update_equity(
        self,
        current_equity: float,
        current_positions: int = 0
    ):
        """
        Update equity tracking for risk calculations.
        
        Args:
            current_equity: Current account equity
            current_positions: Number of open positions
        """
        self.current_equity = current_equity
        self.current_positions = current_positions
        
        # Update peak equity if new high
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
            logger.info(f"New peak equity: ${current_equity:.2f}")
        
        # Calculate drawdown
        drawdown_pct = ((current_equity - self.peak_equity) / self.peak_equity) * 100
        if drawdown_pct < -10:
            logger.warning(f"Significant drawdown: {drawdown_pct:.2f}%")
    
    def check_emergency_stop(self) -> Dict:
        """
        Check if emergency stop should be triggered.
        
        Returns:
            Dict with emergency_stop status
        """
        return self.risk_manager.check_emergency_stop(
            self.current_equity,
            self.peak_equity
        )
    
    def get_risk_status(self) -> Dict:
        """
        Get current risk status.
        
        Returns:
            Dict with available risk capacity
        """
        return self.risk_manager.get_available_risk(
            self.capital,
            self.current_equity,
            self.peak_equity,
            self.current_positions
        )
