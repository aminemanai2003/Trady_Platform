from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional
from urllib import error as urllib_error
from urllib import request as urllib_request
import json

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle
from rest_framework.views import APIView

from . import storage

VALID_SYMBOLS = {"EURUSD", "USDJPY", "GBPUSD", "USDCHF"}
VALID_TIMEFRAMES = {"LIVE", "1S", "1H", "4H", "1D"}
VALID_SIDES = {"BUY", "SELL"}


def _fallback_coach_message(action: str, symbol: str, confidence: float, detail: str, mode: str) -> str:
    action = (action or "HOLD").upper()
    mode = (mode or "beginner").lower()
    short = mode == "advanced"
    if action == "CLOSE_NOW":
        return "Risk control first. Close this trade now to protect capital and wait for a cleaner setup."
    if action == "TAKE_PARTIAL":
        return "Momentum is in your favor. Take partial profits and trail your stop to defend gains."
    if action == "PREPARE":
        return "Stay alert. If momentum fades, tighten the stop or scale out to reduce giveback risk."
    if short:
        return "No high-priority trigger yet. Hold and follow your plan."
    return "No urgent trigger yet. Keep following your stop and target plan with patience."


def _maybe_llm_coach_message(action: str, symbol: str, confidence: float, priority: int, detail: str, mode: str) -> Optional[str]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "8"))
    action = (action or "HOLD").upper()
    tone = "very concise professional trader tone" if (mode or "beginner").lower() == "advanced" else "friendly coaching tone for a beginner"

    prompt = (
        "You are a trading coach assistant. "
        "Write ONE short actionable message (max 28 words). "
        "Do not promise profit. Mention uncertainty naturally. "
        f"Action={action}; Symbol={symbol}; Confidence={confidence:.2f}; Priority={priority}; "
        f"CurrentDetail={detail}; Tone={tone}."
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return plain text only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 80,
    }

    req = urllib_request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        return content[:280] if content else None
    except (urllib_error.URLError, urllib_error.HTTPError, TimeoutError, ValueError, KeyError):
        return None


class TestingTradesView(APIView):
    permission_classes = [AllowAny]
    throttle_classes: list = []

    def get(self, request):
        session_id = request.query_params.get("session_id")
        status = request.query_params.get("status")
        if status and status.upper() not in {"OPEN", "CLOSED"}:
            return Response({"detail": "status must be OPEN or CLOSED"}, status=400)
        trades = storage.list_trades(session_id=session_id, status=status)
        return Response({"trades": trades, "count": len(trades)})

    def post(self, request):
        body = request.data or {}
        symbol = str(body.get("symbol", "")).upper()
        side = str(body.get("side", "")).upper()
        timeframe = str(body.get("timeframe", "1H")).upper()

        if symbol not in VALID_SYMBOLS:
            return Response({"detail": f"Unsupported symbol: {symbol}"}, status=400)
        if side not in VALID_SIDES:
            return Response({"detail": f"Unsupported side: {side}"}, status=400)
        if timeframe not in VALID_TIMEFRAMES:
            return Response({"detail": f"Unsupported timeframe: {timeframe}"}, status=400)

        trade = storage.create_trade(
            {
                "session_id": str(body.get("session_id") or "default"),
                "symbol": symbol,
                "side": side,
                "timeframe": timeframe,
                "size": float(body.get("size") or 0.0),
                "entry_price": float(body.get("entry_price") or 0.0),
                "note": str(body.get("note") or ""),
                "agent_snapshot": body.get("agent_snapshot") or {},
            }
        )
        return Response(trade, status=201)


class TestingCloseTradeView(APIView):
    permission_classes = [AllowAny]
    throttle_classes: list = []

    def patch(self, request, trade_id: str):
        body = request.data or {}
        close_price = float(body.get("close_price") or 0.0)
        if close_price <= 0:
            return Response({"detail": "close_price must be > 0"}, status=400)
        try:
            trade = storage.close_trade(trade_id, close_price)
            return Response(trade)
        except KeyError:
            return Response({"detail": "Trade not found"}, status=404)


class TestingSummaryView(APIView):
    permission_classes = [AllowAny]
    throttle_classes: list = []

    def get(self, request):
        session_id = request.query_params.get("session_id")
        return Response(storage.summary(session_id=session_id))


class TestingResetView(APIView):
    permission_classes = [AllowAny]
    throttle_classes: list = []

    def post(self, request):
        body = request.data or {}
        session_id = str(body.get("session_id") or "default")
        result = storage.reset_session(session_id)
        return Response({"ok": True, **result})


class TestingCoachView(APIView):
    permission_classes = [AllowAny]
    throttle_classes: list = []

    def post(self, request):
        body = request.data or {}
        session_id = str(body.get("session_id") or "default")
        mode = str(body.get("mode") or "beginner")
        signals = body.get("signals") or []

        if not isinstance(signals, list):
            return Response({"detail": "signals must be a list"}, status=400)

        cleaned: List[Dict[str, Any]] = []
        for row in signals[:8]:
            if not isinstance(row, dict):
                continue
            cleaned.append(
                {
                    "trade_id": str(row.get("trade_id") or row.get("tradeId") or ""),
                    "symbol": str(row.get("symbol") or "").upper(),
                    "action": str(row.get("action") or "HOLD").upper(),
                    "confidence": float(row.get("confidence") or 0.6),
                    "priority": int(row.get("priority") or 1),
                    "detail": str(row.get("detail") or ""),
                }
            )

        cleaned.sort(key=lambda s: s["priority"], reverse=True)
        cleaned = cleaned[:4]

        advice: List[Dict[str, Any]] = []
        for signal in cleaned:
            msg = _maybe_llm_coach_message(
                action=signal["action"],
                symbol=signal["symbol"],
                confidence=float(signal["confidence"]),
                priority=int(signal["priority"]),
                detail=signal["detail"],
                mode=mode,
            )
            llm_used = bool(msg)
            if not msg:
                msg = _fallback_coach_message(
                    action=signal["action"],
                    symbol=signal["symbol"],
                    confidence=float(signal["confidence"]),
                    detail=signal["detail"],
                    mode=mode,
                )

            advice.append(
                {
                    "trade_id": signal["trade_id"],
                    "symbol": signal["symbol"],
                    "action": signal["action"],
                    "confidence": round(float(signal["confidence"]), 4),
                    "priority": int(signal["priority"]),
                    "message": msg,
                    "llm_used": llm_used,
                }
            )

        return Response({"session_id": session_id, "mode": mode, "advice": advice})


# Module-level price cache to avoid hammering yfinance on every request
_TICKS_CACHE: Dict[str, float] = {}  # pair → price
_TICKS_CACHE_TS: float = 0.0        # last fetch timestamp
_TICKS_CACHE_TTL = 30               # seconds


class TicksView(APIView):
    permission_classes = [AllowAny]
    throttle_classes: list = []       # no rate-limiting — called every 15s by the UI

    # Yahoo Finance FX tickers that map to our pair names
    _YF_TICKERS: Dict[str, str] = {
        "EURUSD": "EURUSD=X",
        "USDJPY": "USDJPY=X",
        "GBPUSD": "GBPUSD=X",
        "USDCHF": "USDCHF=X",
    }

    def _yfinance_price(self, pair: str) -> Optional[float]:
        """Fetch the latest price from Yahoo Finance (no API key needed)."""
        ticker_sym = self._YF_TICKERS.get(pair)
        if not ticker_sym:
            return None
        try:
            import yfinance as yf
            info = yf.Ticker(ticker_sym).fast_info
            price = float(getattr(info, "last_price", None) or 0)
            return price if price > 0 else None
        except Exception:
            return None

    def _sqlite_price(self, pair: str) -> Optional[float]:
        """Fallback: read the most recent close from OHLCVCandle (SQLite)."""
        try:
            from scheduling.models import OHLCVCandle
            row = (
                OHLCVCandle.objects
                .filter(symbol=pair)
                .order_by("-timestamp")
                .values("close")
                .first()
            )
            if row:
                price = float(row["close"] or 0)
                return price if price > 0 else None
        except Exception:
            pass
        return None

    def get(self, request):
        global _TICKS_CACHE, _TICKS_CACHE_TS
        # Return the shape expected by the Next.js testing simulation page:
        # { "EURUSD": { bid, ask }, "USDJPY": { bid, ask }, ... }
        now = time.monotonic()

        # Refresh price cache if stale
        if now - _TICKS_CACHE_TS > _TICKS_CACHE_TTL:
            fresh: Dict[str, float] = {}
            for pair in VALID_SYMBOLS:
                price = self._yfinance_price(pair)
                if price is None:
                    price = self._sqlite_price(pair)
                if price and price > 0:
                    fresh[pair] = price
            if fresh:  # only replace if we got something
                _TICKS_CACHE = fresh
                _TICKS_CACHE_TS = now
            elif not _TICKS_CACHE:  # first run and empty — try SQLite only
                for pair in VALID_SYMBOLS:
                    p = self._sqlite_price(pair)
                    if p and p > 0:
                        _TICKS_CACHE[pair] = p
                _TICKS_CACHE_TS = now

        out: Dict[str, Dict[str, float]] = {}
        for pair in sorted(VALID_SYMBOLS):
            price = _TICKS_CACHE.get(pair)
            if not price or price <= 0:
                continue
            pip = 0.01 if "JPY" in pair else 0.0001
            spread = pip * 1.5
            bid = round(price - spread / 2, 5)
            ask = round(price + spread / 2, 5)
            out[pair] = {"bid": bid, "ask": ask}

        return Response(out)

