"""
LLM Tool Judge — Deterministic Ollama Tool Wrapper
Advisory-only metadata enrichment stage (Stage 2.5) in the trading pipeline.

Contract:
- NEVER emits APPROVE or REJECT — only COMMENT_ONLY
- Cannot block the pipeline under any circumstances
- Fail-safe guaranteed: returns default output on any failure
- Uses direct HTTP to the local Ollama instance (no RAG, no vector context)
"""
from typing import Dict, List, Optional
import hashlib
import json
import logging
import time

import requests

logger = logging.getLogger(__name__)

_OLLAMA_URL = "http://localhost:11434/api/generate"
_DEFAULT_MODEL = "llama3.2:3b"
_TIMEOUT_MS = 800
_FAIL_SAFE_RESPONSE: Dict = {
    "verdict": "COMMENT_ONLY",
    "confidence_adjustment": 0.0,
    "risk_flags": ["LLM_UNAVAILABLE"],
    "inconsistencies": [],
    "reasoning": "Ollama unavailable — advisory step skipped",
}


class LLMToolJudge:
    """
    Advisory LLM tool that analyses the coordinator + actuarial output and
    returns structured metadata.

    Output is ALWAYS verdict="COMMENT_ONLY".  The pipeline stores this as
    enrichment data for logging/XAI, never as a decision gate.
    """

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        timeout_ms: int = _TIMEOUT_MS,
    ) -> None:
        self.model = model
        self.timeout_ms = timeout_ms
        self._cache: Dict[str, Dict] = {}

        # Connectivity check at startup (non-blocking)
        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=2)
            self.ollama_available = r.status_code == 200
        except Exception:
            self.ollama_available = False

        if self.ollama_available:
            logger.info(f"LLMToolJudge initialised — model={model}")
        else:
            logger.warning("LLMToolJudge: Ollama unreachable — advisory step will be skipped")

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def analyze(
        self,
        coordinator_output: Dict,
        actuarial_scores: Dict,
        market_context: Optional[Dict] = None,
    ) -> Dict:
        """
        Analyse the trade setup and return advisory metadata.

        Args:
            coordinator_output: Output from CoordinatorAgentV2
            actuarial_scores:   Output from ActuarialScorer
            market_context:     Optional extra context (ignored in LLM call, kept for logging)

        Returns:
            Dict with keys: verdict, confidence_adjustment, risk_flags,
                            inconsistencies, reasoning, latency_ms, from_cache
        """
        start = time.perf_counter()

        if not self.ollama_available:
            return {**_FAIL_SAFE_RESPONSE, "latency_ms": 0, "from_cache": False}

        # Build structured input
        tool_input = self._build_input(coordinator_output, actuarial_scores)

        # Cache lookup
        cache_key = self._cache_key(tool_input)
        if cache_key in self._cache:
            cached = dict(self._cache[cache_key])
            cached["from_cache"] = True
            return cached

        # Build prompt & call Ollama
        prompt = self._build_prompt(tool_input)
        try:
            timeout_sec = self.timeout_ms / 1000
            resp = requests.post(
                _OLLAMA_URL,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0, "num_predict": 200},
                },
                timeout=timeout_sec,
            )
            raw_text = resp.json().get("response", "")
        except Exception as exc:
            logger.warning(f"LLMToolJudge request failed: {exc}")
            return {**_FAIL_SAFE_RESPONSE, "latency_ms": int((time.perf_counter() - start) * 1000), "from_cache": False}

        latency_ms = int((time.perf_counter() - start) * 1000)
        parsed = self._parse_response(raw_text)
        parsed["latency_ms"] = latency_ms
        parsed["from_cache"] = False

        # Enforce advisory-only contract
        parsed["verdict"] = "COMMENT_ONLY"

        self._cache[cache_key] = parsed
        logger.info(f"LLMToolJudge advisory done in {latency_ms}ms — flags={parsed.get('risk_flags')}")
        return parsed

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _build_input(self, coordinator_output: Dict, actuarial_scores: Dict) -> Dict:
        """Build a compact, deterministic JSON input for the LLM prompt."""
        agent_signals = coordinator_output.get("agent_signals", {})

        def _agent(key: str) -> Dict:
            a = agent_signals.get(key, {})
            return {"signal": a.get("signal", 0), "confidence": round(a.get("confidence", 0.5), 2)}

        return {
            "pair": coordinator_output.get("symbol", "UNKNOWN"),
            "coordinator_signal": coordinator_output.get("final_signal", 0),
            "coordinator_confidence": round(coordinator_output.get("confidence", 0.5), 3),
            "agents": {
                "TechnicalV2": _agent("TechnicalV2"),
                "MacroV2": _agent("MacroV2"),
                "SentimentV2": _agent("SentimentV2"),
                "GeopoliticalV2": _agent("GeopoliticalV2"),
            },
            "actuarial": {
                "expected_value_pips": round(actuarial_scores.get("expected_value_pips", 0.0), 2),
                "probability_win": round(actuarial_scores.get("probability_win", 0.5), 3),
                "risk_reward": round(actuarial_scores.get("risk_reward_ratio", 1.0), 2),
            },
            "conflicts_detected": bool(coordinator_output.get("conflicts_detected", False)),
            "market_regime": coordinator_output.get("market_regime", "unknown"),
        }

    def _build_prompt(self, tool_input: Dict) -> str:
        """Build a structured prompt that asks for strict JSON output."""
        input_json = json.dumps(tool_input, indent=2)
        return f"""You are an FX trading signal reviewer. Analyse the following trade signal and return ONLY a single valid JSON object — no extra text, no markdown, no explanation outside the JSON.

INPUT:
{input_json}

Your task:
1. Identify any inconsistencies between agents (e.g. TechnicalV2 says BUY but MacroV2 says SELL).
2. Check if expected_value_pips and probability_win are consistent.
3. Raise risk_flags for: LOW_CONFIDENCE (confidence<0.55), REGIME_MISMATCH, AGENT_DIVERGENCE, NEGATIVE_EV, HIGH_CONFLICT.
4. Suggest a confidence_adjustment between -0.15 and +0.10 (0.0 if no change needed).

Respond with this EXACT JSON schema (no other text):
{{
  "confidence_adjustment": <float>,
  "risk_flags": [<string>, ...],
  "inconsistencies": [<string>, ...],
  "reasoning": "<one sentence>"
}}"""

    def _parse_response(self, text: str) -> Dict:
        """Parse the JSON response from the LLM. Returns fail-safe on any error."""
        text = text.strip()

        # Extract JSON block if wrapped in markdown code fences
        if "```" in text:
            start = text.find("{", text.find("```"))
            end = text.rfind("}") + 1
            text = text[start:end] if start != -1 and end > start else text

        try:
            data = json.loads(text)
            adj = float(data.get("confidence_adjustment", 0.0))
            adj = max(-0.15, min(0.10, adj))  # clamp to safe range

            flags: List[str] = [str(f) for f in data.get("risk_flags", [])]
            inconsistencies: List[str] = [str(i) for i in data.get("inconsistencies", [])]
            reasoning: str = str(data.get("reasoning", ""))[:300]  # cap length

            return {
                "verdict": "COMMENT_ONLY",
                "confidence_adjustment": adj,
                "risk_flags": flags,
                "inconsistencies": inconsistencies,
                "reasoning": reasoning,
            }
        except Exception as exc:
            logger.warning(f"LLMToolJudge parse error: {exc} — raw: {text[:200]}")
            return dict(_FAIL_SAFE_RESPONSE)

    def _cache_key(self, tool_input: Dict) -> str:
        serialised = json.dumps(tool_input, sort_keys=True)
        return hashlib.md5(serialised.encode()).hexdigest()

    def clear_cache(self) -> None:
        self._cache.clear()
        logger.info("LLMToolJudge cache cleared")
