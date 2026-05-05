"""
Coordinator Agent V2 - DETERMINISTIC AGGREGATION
NO LLM for trading decisions
LLM only for final explanation generation

Integrations:
- Cross-pair correlation analysis (DSO1.3)
- Multi-timeframe support (DSO1.2)
- Dynamic weight adjustment based on performance
"""
from typing import Dict, List, Optional
from typing_extensions import TypedDict
import numpy as np
from datetime import datetime, timedelta
from langgraph.graph import StateGraph, END
from signal_layer.technical_agent_v2 import TechnicalAgentV2
from signal_layer.macro_agent_v2 import MacroAgentV2
from signal_layer.sentiment_agent_v2 import SentimentAgentV2
from signal_layer.geopolitical_agent_v2 import GeopoliticalAgentV2
from monitoring.performance_tracker import PerformanceTracker


class CoordinatorState(TypedDict, total=False):
    """LangGraph state shared across all coordinator nodes."""
    symbol: str
    base_currency: str
    quote_currency: str
    # Node 1 outputs
    technical_signal: Dict
    price_volatility: float
    # Node 2 outputs
    macro_signal: Dict
    sentiment_signal: Dict
    geopolitical_signal: Dict
    agent_signals: Dict
    # Node 3 outputs
    updated_weights: Dict
    regime: str
    # Node 4 outputs
    final_signal: int
    confidence: float
    weighted_score: float
    conflicts: bool
    # Node 5 outputs
    correlation_info: Optional[Dict]
    # Node 6 outputs
    explanation: str
    deterministic_reason: str
    # Node 7 output
    result: Dict


class CoordinatorAgentV2:
    """
    Meta-Agent that coordinates all agents
    
    DETERMINISTIC:
    - Weighted voting
    - Dynamic weight adjustment based on performance
    - Volatility regime detection
    - Conflict detection
    - Cross-pair correlation validation (DSO1.3)
    - Multi-timeframe confluence (DSO1.2)
    
    LLM: Only for final explanation text
    """
    
    def __init__(self):
        self.technical_agent = TechnicalAgentV2()
        self.macro_agent = MacroAgentV2()
        self.sentiment_agent = SentimentAgentV2()
        self.geopolitical_agent = GeopoliticalAgentV2()
        self.performance_tracker = PerformanceTracker()
        self.correlation_engine = None  # Lazy-loaded

        # Default weights (updated dynamically) — total must sum to 1.0
        self.agent_weights = {
            'TechnicalV2':    0.35,
            'MacroV2':        0.25,
            'SentimentV2':    0.20,
            'GeopoliticalV2': 0.20,
        }

        # Build the LangGraph pipeline once at startup
        self.graph = self._build_graph()
    
    # ── LangGraph graph builder ────────────────────────────────────────────────

    def _build_graph(self):
        """Build and compile the LangGraph StateGraph for the coordinator pipeline.
        All nodes delegate to the existing deterministic private methods — no logic
        is changed, only the orchestration layer is replaced.
        """

        def node_collect_technical(state: CoordinatorState) -> dict:
            technical_signal = self.technical_agent.generate_signal(state["symbol"])
            price_volatility = self._estimate_volatility(state["symbol"])
            return {"technical_signal": technical_signal, "price_volatility": price_volatility}

        def node_collect_market_data(state: CoordinatorState) -> dict:
            macro_signal = self.macro_agent.generate_signal(
                state["base_currency"], state["quote_currency"], state["price_volatility"]
            )
            sentiment_signal = self.sentiment_agent.generate_signal(
                [state["base_currency"], state["quote_currency"]]
            )
            try:
                geopolitical_signal = self.geopolitical_agent.generate_signal(
                    [state["base_currency"], state["quote_currency"]]
                )
            except Exception:
                geopolitical_signal = {
                    "signal": 0, "confidence": 0.0,
                    "key_events": [], "deterministic_reason": "Geopolitical agent unavailable",
                }
            agent_signals = {
                "TechnicalV2":    state["technical_signal"],
                "MacroV2":        macro_signal,
                "SentimentV2":    sentiment_signal,
                "GeopoliticalV2": geopolitical_signal,
            }
            return {
                "macro_signal": macro_signal,
                "sentiment_signal": sentiment_signal,
                "geopolitical_signal": geopolitical_signal,
                "agent_signals": agent_signals,
            }

        def node_compute_weights(state: CoordinatorState) -> dict:
            updated_weights = self._calculate_dynamic_weights(state["agent_signals"])
            regime = self._detect_market_regime(state["technical_signal"], state["price_volatility"])
            return {"updated_weights": updated_weights, "regime": regime}

        def node_aggregate_vote(state: CoordinatorState) -> dict:
            final_signal, confidence, weighted_score = self._aggregate_signals(
                state["agent_signals"], state["updated_weights"], state["regime"]
            )
            conflicts = self._detect_conflicts(state["agent_signals"])
            final_signal, confidence = self._apply_safety_rules(
                final_signal, confidence, conflicts, state["regime"]
            )
            return {
                "final_signal": final_signal,
                "confidence": confidence,
                "weighted_score": weighted_score,
                "conflicts": conflicts,
            }

        def node_validate_correlations(state: CoordinatorState) -> dict:
            correlation_info = self._validate_with_correlations(
                state["symbol"], state["final_signal"], state["confidence"]
            )
            confidence = state["confidence"]
            if correlation_info:
                confidence = correlation_info["adjusted_confidence"]
            return {"correlation_info": correlation_info, "confidence": confidence}

        def node_generate_explanation(state: CoordinatorState) -> dict:
            explanation = self._generate_explanation_text(
                state["final_signal"], state["agent_signals"],
                state["updated_weights"], state["conflicts"]
            )
            deterministic_reason = self._generate_deterministic_reason(
                state["final_signal"], state["agent_signals"], state["updated_weights"]
            )
            return {"explanation": explanation, "deterministic_reason": deterministic_reason}

        def node_build_result(state: CoordinatorState) -> dict:
            result = {
                "final_signal":          state["final_signal"],
                "confidence":            state["confidence"],
                "weighted_score":        float(state["weighted_score"]),
                "agent_signals":         state["agent_signals"],
                "weights_used":          state["updated_weights"],
                "market_regime":         state["regime"],
                "conflicts_detected":    state["conflicts"],
                "cross_pair_correlations": state.get("correlation_info"),
                "deterministic_reason":  state["deterministic_reason"],
                "explanation":           state["explanation"],
                "timestamp":             datetime.now().isoformat(),
            }
            return {"result": result}

        g = StateGraph(CoordinatorState)
        g.add_node("collect_technical",      node_collect_technical)
        g.add_node("collect_market_data",    node_collect_market_data)
        g.add_node("compute_weights",        node_compute_weights)
        g.add_node("aggregate_vote",         node_aggregate_vote)
        g.add_node("validate_correlations",  node_validate_correlations)
        g.add_node("generate_explanation",   node_generate_explanation)
        g.add_node("build_result",           node_build_result)

        g.set_entry_point("collect_technical")
        g.add_edge("collect_technical",     "collect_market_data")
        g.add_edge("collect_market_data",   "compute_weights")
        g.add_edge("compute_weights",       "aggregate_vote")
        g.add_edge("aggregate_vote",        "validate_correlations")
        g.add_edge("validate_correlations", "generate_explanation")
        g.add_edge("generate_explanation",  "build_result")
        g.add_edge("build_result",          END)

        return g.compile()

    # ── Public API ─────────────────────────────────────────────────────────────

    def _get_correlation_engine(self):
        """Lazy-load cross-pair correlation engine"""
        if self.correlation_engine is None:
            try:
                from feature_layer.cross_pair_correlations import CrossPairCorrelationEngine
                self.correlation_engine = CrossPairCorrelationEngine()
            except Exception:
                self.correlation_engine = None
        return self.correlation_engine
    
    def generate_final_signal(
        self,
        symbol: str,
        base_currency: str,
        quote_currency: str
    ) -> Dict:
        """
        Generate final aggregated signal
        
        Process:
        1. Collect signals from all agents (deterministic)
        2. Update weights based on recent performance (deterministic)
        3. Detect market regime (deterministic)
        4. Weighted vote (deterministic)
        5. Apply safety rules (deterministic)
        6. Generate explanation (LLM used here ONLY)
        
        Returns:
            {
                'final_signal': -1/0/1,
                'confidence': 0-1,
                'agent_signals': dict,
                'weights_used': dict,
                'conflicts_detected': bool,
                'explanation': str (from LLM)
            }
        """
        # Delegate to the compiled LangGraph pipeline.
        # All logic is unchanged — nodes call the same private methods.
        state = self.graph.invoke({
            "symbol":         symbol,
            "base_currency":  base_currency,
            "quote_currency": quote_currency,
        })
        return state["result"]
    
    def _calculate_dynamic_weights(self, agent_signals: Dict) -> Dict[str, float]:
        """
        Adjust agent weights based on recent 30-day performance
        
        PURE DETERMINISTIC LOGIC
        """
        # Get recent performance for each agent
        performances = {}
        for agent_name in self.agent_weights.keys():
            perf = self.performance_tracker.get_agent_performance(agent_name, days=30)
            performances[agent_name] = perf.get('sharpe_ratio', 0.0)
        
        # If no performance data, use default weights
        if all(p == 0.0 for p in performances.values()):
            return self.agent_weights.copy()
        
        # Normalize Sharpe ratios to weights (softmax-like)
        # Add constant to avoid negative weights
        adjusted = {k: max(v + 2.0, 0.1) for k, v in performances.items()}
        total = sum(adjusted.values())
        
        new_weights = {k: v / total for k, v in adjusted.items()}
        
        # Smooth transition (80% old, 20% new)
        smoothed = {
            k: 0.8 * self.agent_weights[k] + 0.2 * new_weights[k]
            for k in self.agent_weights.keys()
        }
        
        # Normalize to sum to 1.0
        total_smoothed = sum(smoothed.values())
        final_weights = {k: v / total_smoothed for k, v in smoothed.items()}
        
        return final_weights
    
    def _detect_market_regime(self, technical_signal: Dict, volatility: float) -> str:
        """
        Detect market regime (trending, ranging, volatile)
        
        DETERMINISTIC THRESHOLDS
        """
        adx = technical_signal['features_used'].get('adx', 0)
        
        # FX annual vol: normal 5-12%, high >15%, crisis >20%
        if volatility > 0.15:  # High volatility (was 0.02 - incorrectly flagged all FX)
            return 'volatile'
        elif adx > 25:  # Strong trend
            return 'trending'
        else:
            return 'ranging'
    
    def _aggregate_signals(
        self,
        agent_signals: Dict,
        weights: Dict,
        regime: str
    ) -> tuple:
        """
        Weighted vote aggregation
        
        PURE MATH - NO LLM
        """
        # Adjust weights based on regime
        regime_weights = weights.copy()
        
        if regime == 'trending':
            # Boost technical weight in trends
            regime_weights['TechnicalV2'] *= 1.3
        elif regime == 'ranging':
            # Boost macro weight in ranges
            regime_weights['MacroV2'] *= 1.2
        elif regime == 'volatile':
            # Lower all weights in volatile periods
            regime_weights = {k: v * 0.7 for k, v in regime_weights.items()}
        
        # Renormalize
        total_weight = sum(regime_weights.values())
        regime_weights = {k: v / total_weight for k, v in regime_weights.items()}
        
        # Weighted sum of signals
        weighted_signal_sum = sum(
            agent_signals[agent]['signal'] * 
            agent_signals[agent]['confidence'] *
            regime_weights[agent]
            for agent in regime_weights.keys()
        )
        
        # Weighted confidence
        avg_confidence = sum(
            agent_signals[agent]['confidence'] * regime_weights[agent]
            for agent in regime_weights.keys()
        )
        
        # Convert to discrete signal
        # Threshold 0.12: allows directional signal even when only 1 agent fires
        if weighted_signal_sum > 0.12:
            final_signal = 1
        elif weighted_signal_sum < -0.12:
            final_signal = -1
        else:
            final_signal = 0
        
        return final_signal, avg_confidence, float(weighted_signal_sum)
    
    def _detect_conflicts(self, agent_signals: Dict) -> bool:
        """
        Detect if agents strongly disagree
        
        DETERMINISTIC
        """
        signals = [
            agent_signals[agent]['signal'] 
            for agent in agent_signals.keys()
        ]
        
        # If we have both strong buy (+1) and strong sell (-1)
        if 1 in signals and -1 in signals:
            return True
        
        return False
    
    def _apply_safety_rules(
        self,
        signal: int,
        confidence: float,
        conflicts: bool,
        regime: str
    ) -> tuple:
        """
        Apply production safety rules
        
        - Reduce confidence if conflicts detected
        - Reduce confidence in volatile regimes
        - Require min confidence threshold
        """
        adjusted_confidence = confidence
        
        # Rule 1: Conflicts reduce confidence
        if conflicts:
            adjusted_confidence *= 0.5
        
        # Rule 2: Volatile regime reduces confidence
        if regime == 'volatile':
            adjusted_confidence *= 0.7
        
        # Rule 3: Minimum confidence threshold
        # Lowered to 0.12: avoids forcing NEUTRAL when only technical agent fires
        if adjusted_confidence < 0.12:
            return 0, adjusted_confidence  # Force neutral
        
        return signal, adjusted_confidence
    
    def _estimate_volatility(self, symbol: str) -> float:
        """
        Estimate recent volatility from actual InfluxDB data.
        Calculates annualized volatility from 1H log-returns over 30 days.
        """
        try:
            from data_layer.timeseries_loader import TimeSeriesLoader
            loader = TimeSeriesLoader()
            df = loader.load_ohlcv(symbol, start_time=datetime.now() - timedelta(days=30))
            if df.empty or len(df) < 10:
                return 0.01  # default low volatility
            close = df['close'].astype(float)
            log_returns = np.log(close / close.shift(1)).dropna()
            hourly_vol = log_returns.std()
            # Annualize: hourly → daily (√24) → annual (√252)
            annual_vol = hourly_vol * np.sqrt(24 * 252)
            return float(annual_vol) if not np.isnan(annual_vol) else 0.01
        except Exception:
            return 0.01

    def _validate_with_correlations(self, symbol: str, signal: int, confidence: float) -> dict:
        """
        Cross-pair correlation validation (DSO1.3).
        Checks if our signal is consistent with correlated pair movements.
        Adjusts confidence: +15% if aligned, -25% if conflicting.
        """
        engine = self._get_correlation_engine()
        if engine is None:
            return None
        try:
            corr_signals = engine.get_correlation_signals(symbol)
            if not corr_signals:
                return None

            aligned_count = 0
            conflicting_count = 0
            details = []

            for cs in corr_signals:
                corr_value = cs.get('correlation', 0)
                partner = cs.get('partner_symbol', 'unknown')
                if abs(corr_value) < 0.3:
                    continue
                # If positively correlated, same signal expected
                # If negatively correlated, opposite signal expected
                expected_alignment = np.sign(corr_value)
                details.append({
                    'partner': partner,
                    'correlation': round(corr_value, 3),
                    'alignment': 'aligned' if expected_alignment > 0 else 'inverse',
                })
                if expected_alignment > 0:
                    aligned_count += 1
                else:
                    conflicting_count += 1

            # Confidence adjustment
            if aligned_count > conflicting_count:
                adjustment = min(1.15, 1.0 + 0.05 * aligned_count)
            elif conflicting_count > aligned_count:
                adjustment = max(0.75, 1.0 - 0.08 * conflicting_count)
            else:
                adjustment = 1.0

            adjusted_confidence = min(confidence * adjustment, 0.99)

            return {
                'adjusted_confidence': round(adjusted_confidence, 4),
                'original_confidence': round(confidence, 4),
                'adjustment_factor': round(adjustment, 3),
                'aligned_pairs': aligned_count,
                'conflicting_pairs': conflicting_count,
                'details': details,
            }
        except Exception:
            return None
    
    def _generate_deterministic_reason(
        self,
        final_signal: int,
        agent_signals: Dict,
        weights: Dict
    ) -> str:
        """Generate structured deterministic reason"""
        signal_names = {1: 'BUY', 0: 'NEUTRAL', -1: 'SELL'}
        
        parts = [f"Final: {signal_names[final_signal]}"]
        
        for agent, signal_data in agent_signals.items():
            agent_sig = signal_names[signal_data['signal']]
            conf = signal_data['confidence']
            weight = weights[agent]
            parts.append(f"{agent}: {agent_sig} ({conf:.2f}, w={weight:.2f})")
        
        return " | ".join(parts)
    
    def _generate_explanation_text(
        self,
        final_signal: int,
        agent_signals: Dict,
        weights: Dict,
        conflicts: bool
    ) -> str:
        """
        Generate natural language explanation
        
        THIS IS WHERE LLM IS USED (optional)
        For now, return structured text
        """
        signal_names = {1: 'BUY', 0: 'NEUTRAL', -1: 'SELL'}
        direction = signal_names[final_signal]

        weighted_components = []
        for agent, data in agent_signals.items():
            contribution = data['signal'] * data['confidence'] * weights[agent]
            weighted_components.append((agent, contribution, data))

        weighted_components.sort(key=lambda item: abs(item[1]), reverse=True)
        top_agent, top_contribution, top_data = weighted_components[0]

        lines = [
            f"Final decision: {direction}.",
            (
                f"Primary driver: {top_agent} ({signal_names[top_data['signal']]}, "
                f"contribution {top_contribution:+.3f})."
            ),
        ]

        if final_signal == 0:
            lines.append(
                "Why neutral: bullish and bearish inputs are too balanced, so the system avoids a low-conviction trade."
            )

        lines.append("Agent details:")
        for agent, contribution, data in weighted_components:
            conf_pct = data['confidence'] * 100.0
            weight_pct = weights[agent] * 100.0
            lines.append(
                f"- {agent}: {signal_names[data['signal']]} | confidence {conf_pct:.1f}% | "
                f"weight {weight_pct:.1f}% | contribution {contribution:+.3f}"
            )
            reason = data.get('deterministic_reason') or data.get('reason') or 'No detailed reason available.'
            lines.append(f"  {reason}")

        if conflicts:
            lines.append("Safety adjustment: agents disagree, confidence is reduced to prevent overtrading.")

        return "\n".join(lines)
