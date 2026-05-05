"""
Master Signal View — Unified AI Trading Pipeline
Single authoritative endpoint: POST /api/v2/master/generate/

Replaces all previous signal endpoints (v1 + v2 variants).
Orchestrates full pipeline: Coordinator (Technical + Macro + Sentiment + Geopolitical)
→ ActuarialScorer → LLMJudge → RiskManager → XAIFormatter
"""
import logging
from datetime import datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from decision_layer.pipeline import TradingDecisionPipeline
from monitoring.safety_monitor import SafetyMonitor

logger = logging.getLogger(__name__)

# Module-level singleton — equity state is updated per request
_pipeline = TradingDecisionPipeline(initial_capital=10000.0)
_safety_monitor = SafetyMonitor()


class MasterSignalView(APIView):
    """
    Master unified trading signal endpoint.

    POST body (JSON):
        pair              str    — e.g. "EURUSD"           (required)
        capital           float  — account capital          (default 10 000)
        current_equity    float  — current equity            (defaults to capital)
        peak_equity       float  — highest equity seen       (defaults to capital)
        current_positions int    — open positions count      (default 0)
        entry_price       float  — override entry price      (optional, auto-detected)
        auto_paper_trade  bool   — open PaperPosition if approved (default true)

    Returns the full pipeline result: signal + XAI breakdown + Judge + Actuarial + Risk.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        # ── Parse input ───────────────────────────────────────────────────────
        pair = str(request.data.get("pair", "EURUSD")).upper().strip()
        capital = float(request.data.get("capital", 10_000.0))
        current_equity = float(request.data.get("current_equity", capital))
        peak_equity = float(request.data.get("peak_equity", capital))
        current_positions = int(request.data.get("current_positions", 0))
        entry_price = request.data.get("entry_price")
        auto_paper_trade = bool(request.data.get("auto_paper_trade", True))

        if len(pair) != 6 or not pair.isalpha():
            return Response(
                {"success": False, "error": "Invalid pair. Expected 6-letter symbol like EURUSD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        base = pair[:3]
        quote = pair[3:6]

        # ── Safety pre-check ──────────────────────────────────────────────────
        try:
            safety = _safety_monitor.should_allow_signal(pair)
        except Exception:
            safety = {"allowed": True}

        if not safety.get("allowed", True):
            return Response(
                {
                    "success": False,
                    "decision": "BLOCKED",
                    "pair": pair,
                    "reason": safety.get("reason", "Safety monitor blocked signal"),
                    "safety_checks": safety,
                    "timestamp": datetime.now().isoformat(),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # ── Update pipeline equity state ──────────────────────────────────────
        _pipeline.capital = capital
        _pipeline.update_equity(current_equity, current_positions)
        if peak_equity > _pipeline.peak_equity:
            _pipeline.peak_equity = peak_equity

        # ── Execute full pipeline ─────────────────────────────────────────────
        try:
            recent_news_count = 0
            try:
                from data_layer.news_loader import NewsLoader
                _news_loader = NewsLoader()
                news = _news_loader.load_recent_news(pair, hours=4) or []
                recent_news_count = len(news)
            except Exception:
                pass

            result = _pipeline.execute(
                symbol=pair,
                base_currency=base,
                quote_currency=quote,
                entry_price=entry_price,
                market_context={
                    "latest_news_count": recent_news_count,
                    "request_time": datetime.now().isoformat(),
                },
            )

            if result.get("status") == "error":
                return Response(
                    {"success": False, "error": result.get("error"), "timestamp": result.get("timestamp")},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            response_data = self._format_response(result, pair)

            # ── Auto paper trade ──────────────────────────────────────────────
            if auto_paper_trade and response_data.get("decision") == "APPROVED":
                self._open_paper_trade(response_data, pair)

            # ── Broadcast via WebSocket (best-effort) ─────────────────────────
            self._broadcast_signal(pair, response_data)

            return Response(response_data)

        except Exception as exc:
            import traceback
            logger.exception(f"Pipeline error for {pair}: {exc}")
            return Response(
                {
                    "success": False,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                    "timestamp": datetime.now().isoformat(),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ── Response formatting ───────────────────────────────────────────────────

    def _format_response(self, result: dict, pair: str) -> dict:
        """Normalize pipeline result into the unified API contract."""
        xai = result.get("xai") or {}
        coord = xai.get("coordinator_analysis") or {}
        judge_eval = xai.get("judge_evaluation") or {}
        actuarial = xai.get("actuarial_metrics") or {}
        agent_breakdown = xai.get("agent_breakdown") or {}

        # Extract geopolitical events from agent breakdown
        geo_info = agent_breakdown.get("GeopoliticalV2") or {}
        geopolitical_events = geo_info.get("key_events", [])

        base: dict = {
            "success": True,
            "decision": result.get("decision", "REJECTED"),
            "pair": pair,
            "signal": {
                "direction": result.get("signal_name", "NEUTRAL"),
                "signal_value": result.get("signal", 0),
                "confidence": round(result.get("confidence", 0.0), 4),
            },
            "coordinator": {
                "weighted_score": coord.get("weighted_score", 0.0),
                "market_regime": coord.get("market_regime", "unknown"),
                "conflicts_detected": coord.get("conflicts_detected", False),
                "conflict_description": coord.get("conflict_description", ""),
            },
            "judge": {
                "verdict": judge_eval.get("verdict", "REJECT"),
                "reasoning": judge_eval.get("reasoning", ""),
                "latency_ms": judge_eval.get("latency_ms", 0),
                "from_cache": judge_eval.get("from_cache", False),
            },
            "actuarial": {
                "expected_value_pips": actuarial.get("expected_value_pips", 0.0),
                "probability_win": actuarial.get("probability_win", 0.0),
                "probability_loss": actuarial.get("probability_loss", 0.0),
                "risk_reward_ratio": actuarial.get("risk_reward_ratio", 0.0),
                "kelly_fraction": actuarial.get("kelly_fraction", 0.0),
                "verdict": actuarial.get("verdict", "UNKNOWN"),
            },
            "xai": {
                "agent_breakdown": agent_breakdown,
                "human_explanation": xai.get("human_explanation", {}),
                "rejection_stage": xai.get("rejection_stage"),
                "rejection_reason": xai.get("rejection_reason"),
            },
            "tool_judge": result.get("tool_judge"),
            "geopolitical_events": geopolitical_events,
            "timestamp": result.get("timestamp", datetime.now().isoformat()),
        }

        if result.get("status") == "success":
            base["execution_plan"] = {
                "entry_price": result.get("entry_price"),
                "position_size": result.get("position_size"),
                "stop_loss": result.get("stop_loss"),
                "take_profit": result.get("take_profit"),
                "stop_loss_pips": result.get("stop_loss_pips"),
                "take_profit_pips": result.get("take_profit_pips"),
                "risk_pct": result.get("risk_pct"),
            }
        else:
            base["rejection"] = {
                "stage": result.get("rejection_stage"),
                "reason": result.get("rejection_reason"),
            }

        return base

    # ── Side effects ──────────────────────────────────────────────────────────

    def _open_paper_trade(self, response_data: dict, pair: str):
        """Auto-open a PaperPosition when pipeline approves a trade."""
        try:
            from paper_trading.services.portfolio import open_position
            exec_plan = response_data.get("execution_plan") or {}
            open_position(
                pair=pair,
                side=response_data["signal"]["direction"],
                size=exec_plan.get("position_size") or 0.1,
                entry_price=exec_plan.get("entry_price") or 0.0,
                stop_loss=exec_plan.get("stop_loss"),
                take_profit=exec_plan.get("take_profit"),
                pipeline_snapshot=response_data,
            )
        except Exception as exc:
            logger.debug(f"Paper trade open skipped (migrations may be pending): {exc}")

    def _broadcast_signal(self, pair: str, data: dict):
        """Broadcast approved/rejected signal over WebSocket channel group (non-blocking)."""
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"signals_{pair}",
                    {"type": "signal.update", "data": data},
                )
        except Exception:
            pass  # WebSocket layer not configured — silently skip
