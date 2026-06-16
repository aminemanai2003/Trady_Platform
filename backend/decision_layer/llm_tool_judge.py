"""
LLM Tool Judge â€” Deterministic Ollama Tool Wrapper
Advisory-only metadata enrichment stage (Stage 2.5) in the trading pipeline.

Contract:
- NEVER emits APPROVE or REJECT â€” only COMMENT_ONLY
- Cannot block the pipeline under any circumstances
- Fail-safe guaranteed: returns default output on any failure
- Uses direct HTTP to the local Ollama instance (no RAG, no vector context)
"""
from typing import Any, Dict, List, Optional
import hashlib
import json
import logging
import os
import time

import requests
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

_OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
_OLLAMA_URL = f"{_OLLAMA_BASE_URL}/api/generate"
_DEFAULT_MODEL = "llama3.2:3b"
_TIMEOUT_MS = 10000
_FAIL_SAFE_RESPONSE: Dict = {
    "verdict": "COMMENT_ONLY",
    "confidence_adjustment": 0.0,
    "risk_flags": ["ADVISORY_REVIEW_UNAVAILABLE"],
    "inconsistencies": [],
    "reasoning": "Optional advisory review unavailable; deterministic checks continued.",
}


class AdvisoryReview(BaseModel):
    confidence_adjustment: float = Field(ge=-0.15, le=0.10)
    risk_flags: List[str]
    inconsistencies: List[str]
    reasoning: str

    @field_validator("confidence_adjustment", mode="before")
    @classmethod
    def normalise_adjustment(cls, value: Any) -> float:
        return 0.0 if value is None else float(value)

    @field_validator("risk_flags", "inconsistencies", mode="before")
    @classmethod
    def normalise_string_lists(cls, value: Any) -> List[str]:
        if not isinstance(value, list):
            return []

        normalised: List[str] = []
        for item in value:
            if isinstance(item, dict):
                title = str(item.get("title", "")).strip()
                description = str(item.get("description", "")).strip()
                text = ": ".join(part for part in (title, description) if part)
                if text:
                    normalised.append(text)
            elif item is not None:
                normalised.append(str(item))
        return normalised


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
        self._parser = PydanticOutputParser(pydantic_object=AdvisoryReview)
        self._chain = (
            ChatPromptTemplate.from_messages([
                (
                    "system",
                    "You are a conservative FX evidence reviewer. Never approve, "
                    "reject, or change a trade. Opposing non-zero signal directions "
                    "are conflicts; different confidence values for the same direction "
                    "are not conflicts. Do not claim that ordinary probability, expected "
                    "value, or risk-reward differences are mathematically inconsistent. "
                    "Return only the requested structure.",
                ),
                (
                    "human",
                    "Review this deterministic pipeline output:\n{tool_input}\n\n"
                    "Identify only explicit contradictions and missing-evidence risks. "
                    "Do not infer facts that are absent. The confidence adjustment is "
                    "advisory metadata only.\n{format_instructions}",
                ),
            ])
            | RunnableLambda(self._invoke_ollama)
            | self._parser
        )

        # Rechecked on demand so a late-starting local service recovers cleanly.
        self.ollama_available = self._check_available()

        if self.ollama_available:
            logger.info(f"LLMToolJudge initialised â€” model={model}")
        else:
            logger.warning("LLMToolJudge: Ollama unreachable â€” advisory step will be skipped")

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Public API
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
            self.ollama_available = self._check_available()

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

        try:
            review = self._chain.invoke({
                "tool_input": json.dumps(tool_input, indent=2),
                "format_instructions": self._parser.get_format_instructions(),
            })
        except Exception as exc:
            logger.warning(f"LangChain advisory review failed: {exc}")
            return {**_FAIL_SAFE_RESPONSE, "latency_ms": int((time.perf_counter() - start) * 1000), "from_cache": False}

        latency_ms = int((time.perf_counter() - start) * 1000)
        parsed = {"verdict": "COMMENT_ONLY", **review.model_dump()}
        parsed = self._enforce_objective_checks(parsed, tool_input)
        parsed["latency_ms"] = latency_ms
        parsed["from_cache"] = False

        # Enforce advisory-only contract
        parsed["verdict"] = "COMMENT_ONLY"

        self._cache[cache_key] = parsed
        logger.info(f"LLMToolJudge advisory done in {latency_ms}ms â€” flags={parsed.get('risk_flags')}")
        return parsed

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Internal helpers
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _check_available(self) -> bool:
        try:
            response = requests.get(f"{_OLLAMA_BASE_URL}/api/tags", timeout=2)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def _invoke_ollama(self, prompt_value) -> str:
        """LangChain runnable backed by the configured local model service."""
        response = requests.post(
            _OLLAMA_URL,
            json={
                "model": self.model,
                "prompt": prompt_value.to_string(),
                "stream": False,
                "format": "json",
                "options": {"temperature": 0, "num_predict": 220},
            },
            timeout=self.timeout_ms / 1000,
        )
        response.raise_for_status()
        return response.json().get("response", "")

    def _enforce_objective_checks(self, review: Dict, tool_input: Dict) -> Dict:
        agents = tool_input.get("agents", {})
        signals = [
            int(agent.get("signal", 0))
            for agent in agents.values()
            if int(agent.get("signal", 0)) != 0
        ]
        has_directional_conflict = any(signal > 0 for signal in signals) and any(
            signal < 0 for signal in signals
        )

        flags = {str(flag) for flag in review.get("risk_flags", [])}
        if tool_input.get("coordinator_confidence", 0.0) < 0.55:
            flags.add("LOW_CONFIDENCE")
        if tool_input.get("actuarial", {}).get("expected_value_pips", 0.0) < 0:
            flags.add("NEGATIVE_EV")
        if tool_input.get("evidence", {}).get("coverage", 0.0) < 0.75:
            flags.add("LOW_EVIDENCE")
        if has_directional_conflict:
            flags.add("AGENT_DIVERGENCE")

        inconsistencies = [str(item) for item in review.get("inconsistencies", [])]
        if not has_directional_conflict:
            conflict_terms = ("conflict", "opposing", "signal direction")
            inconsistencies = [
                item for item in inconsistencies
                if not any(term in item.lower() for term in conflict_terms)
            ]
            if any(term in str(review.get("reasoning", "")).lower() for term in conflict_terms):
                review["reasoning"] = "Objective evidence checks completed; no directional agent conflict was found."
        elif not any("direction" in item.lower() or "conflict" in item.lower() for item in inconsistencies):
            inconsistencies.append("At least one agent supports BUY while another supports SELL.")

        review["risk_flags"] = sorted(flags)
        review["inconsistencies"] = inconsistencies
        return review

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
            "evidence": {
                "coverage": round(
                    coordinator_output.get("weight_metadata", {}).get("evidence_coverage", 0.0),
                    3,
                ),
                "quality_by_agent": coordinator_output.get("weight_metadata", {}).get("data_quality", {}),
                "historical_samples": actuarial_scores.get("historical_sample_size", 0),
                "probability_basis": actuarial_scores.get("probability_basis", "unknown"),
            },
        }

    def _build_prompt(self, tool_input: Dict) -> str:
        """Build a structured prompt that asks for strict JSON output."""
        input_json = json.dumps(tool_input, indent=2)
        return f"""You are an FX trading signal reviewer. Analyse the following trade signal and return ONLY a single valid JSON object â€” no extra text, no markdown, no explanation outside the JSON.

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
            logger.warning(f"LLMToolJudge parse error: {exc} â€” raw: {text[:200]}")
            return dict(_FAIL_SAFE_RESPONSE)

    def _cache_key(self, tool_input: Dict) -> str:
        serialised = json.dumps(tool_input, sort_keys=True)
        return hashlib.md5(serialised.encode()).hexdigest()

    def clear_cache(self) -> None:
        self._cache.clear()
        logger.info("LLMToolJudge cache cleared")
