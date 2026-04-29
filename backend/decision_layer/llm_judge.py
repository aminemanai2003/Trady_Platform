"""
LLM Judge Module
Local Ollama-based validation gate for trading decisions
Approves, rejects, or modifies trades based on comprehensive analysis
"""
from typing import Dict, Optional
import logging
import time
import hashlib
import json

import requests

logger = logging.getLogger(__name__)


class LLMJudge:
    """
    LLM-based decision validator using local Ollama.
    Acts as final gate before risk management.
    Can APPROVE, REJECT, or MODIFY trades.
    """
    
    # Rejection criteria thresholds
    # With 3/4 agents neutral (no macro/sentiment/geo data), max aggregated
    # confidence is ~0.35 from technical alone. Lower threshold accordingly.
    MIN_CONFIDENCE = 0.20
    MIN_EV_PIPS = 0.0
    # HTTP read timeout for Ollama (local CPU inference can take several seconds)
    OLLAMA_HTTP_TIMEOUT_MS = 30000  # 30 s
    # Performance warning threshold (log if slower than this)
    PERF_WARN_MS = 5000  # 5 s
    # Keep TIMEOUT_MS alias for back-compat (used by perf warning log)
    TIMEOUT_MS = PERF_WARN_MS
    
    def __init__(self, model: str = "llama3.2:3b"):
        """
        Initialize LLM Judge.
        
        Args:
            model: Ollama model name (default: llama3.2:3b)
        """
        self.model = model
        self.timeout_ms = self.PERF_WARN_MS
        self._cache = {}  # Simple in-memory cache
        
        # Eagerly check Ollama — but availability is also re-checked per call
        self.ollama_available = self._check_ollama_available()

    def _check_ollama_available(self) -> bool:
        """Probe Ollama. Returns True if reachable."""
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=2)
            available = resp.status_code == 200
            if available:
                logger.info(f"LLM Judge: Ollama reachable (model={self.model})")
            else:
                logger.warning("LLM Judge: Ollama returned non-200 — will use fail-safe APPROVE")
            return available
        except Exception:
            logger.warning("LLM Judge: Ollama not reachable — will use fail-safe APPROVE")
            return False
    
    def evaluate(
        self,
        coordinator_output: Dict,
        actuarial_scores: Dict,
        market_context: Optional[Dict] = None
    ) -> Dict:
        """
        Evaluate trade using LLM reasoning.
        
        Args:
            coordinator_output: Output from CoordinatorAgentV2
            actuarial_scores: Scores from ActuarialScorer
            market_context: Optional additional market context
        
        Returns:
            Dict with 'verdict', 'reasoning', 'latency_ms', 'confidence_adjusted'
        """
        start_time = time.perf_counter()
        
        # Re-check Ollama availability each call so we recover if it starts
        # after Django (lightweight probe via tags endpoint).
        if not self.ollama_available:
            self.ollama_available = self._check_ollama_available()
        if not self.ollama_available:
            return self._fallback_decision(coordinator_output, actuarial_scores)
        
        # Check cache
        cache_key = self._generate_cache_key(coordinator_output, actuarial_scores)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            logger.info(f"Cache hit for Judge decision: {cached['verdict']}")
            cached['from_cache'] = True
            return cached
        
        # Quick rejection checks (before LLM call)
        quick_reject = self._quick_rejection_check(coordinator_output, actuarial_scores)
        if quick_reject:
            result = {
                'verdict': 'REJECT',
                'reasoning': quick_reject,
                'latency_ms': int((time.perf_counter() - start_time) * 1000),
                'confidence_adjusted': coordinator_output.get('confidence', 0.5),
                'rejection_criteria': ['pre_llm_check'],
                'from_cache': False
            }
            self._cache[cache_key] = result
            return result
        
        # Build prompt
        prompt = self._build_prompt(coordinator_output, actuarial_scores, market_context)
        
        # Call LLM via direct HTTP
        try:
            http_timeout_sec = self.OLLAMA_HTTP_TIMEOUT_MS / 1000  # 30 s
            raw = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 200}
                },
                timeout=http_timeout_sec
            )
            llm_response = raw.json().get("response", "")
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            
            # Perf warning (not an error — local CPU inference is slower than cloud)
            if latency_ms > self.PERF_WARN_MS:
                logger.warning(f"LLM Judge slow: {latency_ms}ms > {self.PERF_WARN_MS}ms (CPU inference)")
            
            # Parse LLM response
            parsed = self._parse_llm_response(llm_response)
            
            result = {
                'verdict': parsed['verdict'],
                'reasoning': parsed['reasoning'],
                'latency_ms': latency_ms,
                'confidence_adjusted': parsed.get('confidence_adjusted', coordinator_output.get('confidence', 0.5)),
                'rejection_criteria': parsed.get('rejection_criteria', []),
                'raw_response': llm_response,
                'from_cache': False
            }
            
            # Cache result
            self._cache[cache_key] = result
            
            logger.info(f"LLM Judge verdict: {result['verdict']} ({latency_ms}ms)")
            
            return result
        
        except Exception as e:
            logger.error(f"LLM Judge error: {e}")
            # Fail-safe: pass to RiskManager rather than reject
            return {
                'verdict': 'APPROVE',
                'reasoning': f"LLM Judge error (fail-safe pass-through): {str(e)}",
                'latency_ms': int((time.perf_counter() - start_time) * 1000),
                'confidence_adjusted': coordinator_output.get('confidence', 0.5),
                'rejection_criteria': ['llm_error'],
                'from_cache': False
            }
    
    def _quick_rejection_check(
        self,
        coordinator_output: Dict,
        actuarial_scores: Dict
    ) -> Optional[str]:
        """
        Quick rejection checks before calling LLM.
        
        Args:
            coordinator_output: Coordinator output
            actuarial_scores: Actuarial scores
        
        Returns:
            Rejection reason string if should reject, None otherwise
        """
        confidence = coordinator_output.get('confidence', 0.5)
        conflicts = coordinator_output.get('conflicts_detected', False)
        ev_pips = actuarial_scores.get('expected_value_pips', 0.0)
        final_signal = coordinator_output.get('final_signal', 0)
        
        # NEUTRAL signal
        if final_signal == 0:
            return "NEUTRAL signal - no directional bias"
        
        # Low confidence
        if confidence < self.MIN_CONFIDENCE:
            return f"Confidence {confidence:.2f} below threshold {self.MIN_CONFIDENCE}"
        
        # Negative expected value
        if ev_pips < self.MIN_EV_PIPS:
            return f"Negative expected value: {ev_pips:.2f} pips"
        
        # Conflicting signals with very low confidence
        if conflicts and confidence < 0.55:
            return f"Conflicting agent signals with low confidence ({confidence:.2f})"
        
        return None
    
    def _build_prompt(
        self,
        coordinator_output: Dict,
        actuarial_scores: Dict,
        market_context: Optional[Dict] = None
    ) -> str:
        """
        Build structured prompt for LLM Judge.
        
        Args:
            coordinator_output: Coordinator output
            actuarial_scores: Actuarial scores
            market_context: Optional market context
        
        Returns:
            Prompt string
        """
        agent_signals = coordinator_output.get('agent_signals', {})
        
        # Extract agent details
        tech_signal = agent_signals.get('TechnicalV2', {}).get('signal', 0)
        tech_conf = agent_signals.get('TechnicalV2', {}).get('confidence', 0.5)
        macro_signal = agent_signals.get('MacroV2', {}).get('signal', 0)
        macro_conf = agent_signals.get('MacroV2', {}).get('confidence', 0.5)
        sent_signal = agent_signals.get('SentimentV2', {}).get('signal', 0)
        sent_conf = agent_signals.get('SentimentV2', {}).get('confidence', 0.5)
        
        signal_map = {-1: "SELL", 0: "NEUTRAL", 1: "BUY"}
        
        prompt = f"""You are a risk-averse trading validator reviewing a proposed FX trade.

PROPOSED TRADE:
- Final Signal: {signal_map.get(coordinator_output.get('final_signal', 0), 'UNKNOWN')}
- Confidence: {coordinator_output.get('confidence', 0.5):.2f}
- Symbol: {coordinator_output.get('symbol', 'UNKNOWN')}

AGENT CONSENSUS:
- Technical Agent: {signal_map.get(tech_signal, 'UNKNOWN')} (confidence: {tech_conf:.2f})
- Macro Agent: {signal_map.get(macro_signal, 'UNKNOWN')} (confidence: {macro_conf:.2f})
- Sentiment Agent: {signal_map.get(sent_signal, 'UNKNOWN')} (confidence: {sent_conf:.2f})

CONFLICTS DETECTED: {'YES' if coordinator_output.get('conflicts_detected', False) else 'NO'}

ACTUARIAL ANALYSIS:
- Expected Value: {actuarial_scores.get('expected_value_pips', 0):.2f} pips
- Probability of Win: {actuarial_scores.get('probability_win', 0.5):.2%}
- Risk/Reward Ratio: {actuarial_scores.get('risk_reward_ratio', 1.0):.2f}

MARKET REGIME: {coordinator_output.get('market_regime', 'unknown')}

DECISION RULES:
- REJECT if: confidence < 0.50, conflicting signals, negative EV, incoherent setup
- APPROVE if: confidence > 0.70, agent consensus, positive EV, clear directional bias
- MODIFY if: marginal setup that can be improved (adjust confidence/position size)

Based on this analysis, should this trade be APPROVED, REJECTED, or MODIFIED?

Respond in this EXACT format:
VERDICT: [APPROVE/REJECT/MODIFY]
REASON: [One concise sentence explaining your decision]
CONFIDENCE: [Adjusted confidence 0.0-1.0 if MODIFY, otherwise same]
"""
        
        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict:
        """
        Parse structured LLM response.
        
        Args:
            response: Raw LLM response string
        
        Returns:
            Dict with verdict, reasoning, confidence_adjusted
        """
        lines = response.strip().split('\n')
        
        verdict = 'APPROVE'  # Fail-safe default — Risk Manager is the final veto
        reasoning = 'LLM response parsed (fail-safe APPROVE on parse error)'
        confidence_adjusted = None
        rejection_criteria = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('VERDICT:'):
                verdict_text = line.split(':', 1)[1].strip().upper()
                if 'APPROVE' in verdict_text:
                    verdict = 'APPROVE'
                elif 'REJECT' in verdict_text:
                    verdict = 'REJECT'
                elif 'MODIFY' in verdict_text:
                    verdict = 'MODIFY'
            
            elif line.startswith('REASON:'):
                reasoning = line.split(':', 1)[1].strip()
                
                # Extract rejection criteria from reasoning
                reasoning_lower = reasoning.lower()
                if 'conflict' in reasoning_lower:
                    rejection_criteria.append('conflicting_signals')
                if 'confidence' in reasoning_lower and 'low' in reasoning_lower:
                    rejection_criteria.append('low_confidence')
                if 'negative' in reasoning_lower or 'ev' in reasoning_lower:
                    rejection_criteria.append('negative_ev')
                if 'ranging' in reasoning_lower or 'volatile' in reasoning_lower:
                    rejection_criteria.append('unfavorable_regime')
            
            elif line.startswith('CONFIDENCE:'):
                try:
                    conf_text = line.split(':', 1)[1].strip()
                    confidence_adjusted = float(conf_text)
                except:
                    pass
        
        return {
            'verdict': verdict,
            'reasoning': reasoning,
            'confidence_adjusted': confidence_adjusted,
            'rejection_criteria': rejection_criteria
        }
    
    def _fallback_decision(
        self,
        coordinator_output: Dict,
        actuarial_scores: Dict
    ) -> Dict:
        """
        Fallback decision when Ollama is not available.
        Uses deterministic rules.
        
        Args:
            coordinator_output: Coordinator output
            actuarial_scores: Actuarial scores
        
        Returns:
            Dict with verdict and reasoning
        """
        confidence = coordinator_output.get('confidence', 0.5)

        # Fail-safe: Ollama unavailable → pass unconditionally to RiskManager
        return {
            'verdict': 'APPROVE',
            'reasoning': 'Ollama unavailable - passing to RiskManager (fail-safe)',
            'latency_ms': 0,
            'confidence_adjusted': confidence,
            'rejection_criteria': ['ollama_unavailable'],
            'from_cache': False,
            'fallback': True
        }
    
    def _generate_cache_key(
        self,
        coordinator_output: Dict,
        actuarial_scores: Dict
    ) -> str:
        """
        Generate cache key for decision.
        
        Args:
            coordinator_output: Coordinator output
            actuarial_scores: Actuarial scores
        
        Returns:
            Cache key string
        """
        # Create hash of relevant decision inputs
        key_data = {
            'signal': coordinator_output.get('final_signal', 0),
            'confidence': round(coordinator_output.get('confidence', 0.5), 2),
            'conflicts': coordinator_output.get('conflicts_detected', False),
            'regime': coordinator_output.get('market_regime', 'unknown'),
            'ev': round(actuarial_scores.get('expected_value_pips', 0.0), 1),
            'p_win': round(actuarial_scores.get('probability_win', 0.5), 2)
        }
        
        key_json = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_json.encode()).hexdigest()
    
    def clear_cache(self):
        """Clear decision cache"""
        self._cache = {}
        logger.info("LLM Judge cache cleared")
