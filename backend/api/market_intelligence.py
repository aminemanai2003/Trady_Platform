"""Truthful market data and decision support for the live intelligence screen."""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

import numpy as np
import pandas as pd
import requests
from django.conf import settings
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import balanced_accuracy_score

from data_layer.timeseries_loader import TimeSeriesLoader
from feature_layer.technical_features import TechnicalFeatureEngine
from signal_layer.coordinator_agent_v2 import CoordinatorAgentV2

logger = logging.getLogger(__name__)

SUPPORTED_PAIRS = {"EURUSD", "GBPUSD", "USDJPY", "USDCHF"}
SUPPORTED_TIMEFRAMES = {"1h", "4h", "1d"}
HORIZONS = {
    "1h": {"bars": 4, "label": "Next 4 hours"},
    "4h": {"bars": 4, "label": "Next 16 hours"},
    "1d": {"bars": 3, "label": "Next 3 trading days"},
}


def _finite(value: Any, digits: int = 6) -> float | None:
    try:
        number = float(value)
        return round(number, digits) if np.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def market_is_open(now: datetime | None = None) -> bool:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    weekday = current.weekday()
    if weekday == 5:
        return False
    if weekday == 6:
        return current.hour >= 22
    if weekday == 4 and current.hour >= 22:
        return False
    return True


@dataclass
class Quote:
    bid: float
    ask: float
    timestamp: datetime


class MT5QuoteProvider:
    """Read an actual MT5 terminal quote when a local terminal is connected."""

    def get_quote(self, symbol: str) -> Quote | None:
        try:
            import MetaTrader5 as mt5

            if not mt5.initialize():
                return None
            try:
                tick = mt5.symbol_info_tick(symbol)
                if tick is None or not tick.bid or not tick.ask:
                    return None
                return Quote(
                    bid=float(tick.bid),
                    ask=float(tick.ask),
                    timestamp=datetime.fromtimestamp(int(tick.time), tz=timezone.utc),
                )
            finally:
                mt5.shutdown()
        except Exception:
            return None


class MarketDataService:
    def __init__(self) -> None:
        self.loader = TimeSeriesLoader()
        self.quote_provider = MT5QuoteProvider()

    def load(self, pair: str, timeframe: str, limit: int = 500) -> dict[str, Any]:
        pair = pair.upper()
        timeframe = timeframe.lower()
        if pair not in SUPPORTED_PAIRS:
            raise ValueError("Unsupported currency pair")
        if timeframe not in SUPPORTED_TIMEFRAMES:
            raise ValueError("Unsupported timeframe")

        lookback = {"1h": 365, "4h": 730, "1d": 1600}[timeframe]
        frame = self.loader.load_ohlcv(
            pair,
            start_time=datetime.now() - timedelta(days=lookback),
            timeframe=timeframe,
        )
        if frame.empty:
            return self._unavailable(pair, timeframe)

        frame = frame.dropna(subset=["timestamp", "open", "high", "low", "close"])
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        frame = frame.sort_values("timestamp").drop_duplicates("timestamp").tail(max(50, min(limit, 2000)))

        latest = frame.iloc[-1]
        latest_time = latest["timestamp"].to_pydatetime()
        now = datetime.now(timezone.utc)
        age_seconds = max(0, int((now - latest_time).total_seconds()))
        is_open = market_is_open(now)
        expected_seconds = {"1h": 3600, "4h": 14400, "1d": 86400}[timeframe]
        quote = self.quote_provider.get_quote(pair)

        if quote and (now - quote.timestamp).total_seconds() <= 120:
            data_status = "live"
            data_source = "mt5 + stored_ohlcv"
        elif not is_open and age_seconds <= 72 * 3600:
            data_status = "market_closed"
            data_source = "stored_ohlcv"
        elif age_seconds <= expected_seconds * 3:
            data_status = "delayed"
            data_source = "stored_ohlcv"
        else:
            data_status = "stale"
            data_source = "stored_ohlcv"

        candles = [
            {
                "time": int(row.timestamp.timestamp()),
                "open": _finite(row.open),
                "high": _finite(row.high),
                "low": _finite(row.low),
                "close": _finite(row.close),
                "volume": _finite(row.volume, 2) or 0,
            }
            for row in frame.itertuples(index=False)
        ]
        return {
            "pair": pair,
            "timeframe": timeframe,
            "candles": candles,
            "latest_candle_at": latest_time.isoformat(),
            "latest_price": _finite(latest["close"]),
            "quote": (
                {
                    "bid": _finite(quote.bid),
                    "ask": _finite(quote.ask),
                    "spread": _finite(quote.ask - quote.bid),
                    "timestamp": quote.timestamp.isoformat(),
                }
                if quote
                else None
            ),
            "data_source": data_source,
            "data_status": data_status,
            "age_seconds": age_seconds,
            "market_open": is_open,
            "bar_count": len(candles),
        }

    @staticmethod
    def _unavailable(pair: str, timeframe: str) -> dict[str, Any]:
        return {
            "pair": pair,
            "timeframe": timeframe,
            "candles": [],
            "latest_candle_at": None,
            "latest_price": None,
            "quote": None,
            "data_source": None,
            "data_status": "unavailable",
            "age_seconds": None,
            "market_open": market_is_open(),
            "bar_count": 0,
        }


class MarketForecastService:
    """Walk-forward evaluated local model; unavailable is an acceptable result."""

    FEATURES = [
        "rsi_14", "macd_diff", "bb_pctb", "adx", "atr_pct",
        "roc_5", "roc_10", "price_sma50_dist", "volatility_20", "volume_ratio",
    ]

    @lru_cache(maxsize=24)
    def forecast(self, pair: str, timeframe: str, latest_timestamp: str) -> dict[str, Any]:
        del latest_timestamp
        data = MarketDataService().load(pair, timeframe, limit=2000)
        minimum_samples = 240 if timeframe == "1d" else 600
        if len(data["candles"]) < minimum_samples:
            return self._unavailable(f"At least {minimum_samples} historical bars are required")

        raw = pd.DataFrame(data["candles"])
        raw["timestamp"] = pd.to_datetime(raw["time"], unit="s", utc=True)
        featured = TechnicalFeatureEngine.calculate_all(raw.set_index("timestamp"))
        horizon = HORIZONS[timeframe]["bars"]
        future_return = featured["close"].shift(-horizon) / featured["close"] - 1
        atr_return = featured["atr_14"] / featured["close"]
        threshold = atr_return * 0.35
        labels = np.where(future_return > threshold, 1, np.where(future_return < -threshold, -1, 0))

        dataset = featured[self.FEATURES].copy()
        if dataset["volume_ratio"].notna().sum() < len(dataset) * 0.5:
            dataset["volume_ratio"] = 1.0
        dataset["label"] = labels
        dataset = dataset.replace([np.inf, -np.inf], np.nan).dropna()
        dataset = dataset.iloc[:-horizon] if len(dataset) > horizon else dataset.iloc[0:0]
        if len(dataset) < minimum_samples or dataset["label"].nunique() < 3:
            return self._unavailable("Historical outcomes are insufficiently diverse")

        split = int(len(dataset) * 0.8)
        train, test = dataset.iloc[:split], dataset.iloc[split:]
        minimum_validation = 45 if timeframe == "1d" else 100
        if len(test) < minimum_validation:
            return self._unavailable("The chronological validation sample is too small")

        model = HistGradientBoostingClassifier(
            max_iter=180,
            max_depth=5,
            learning_rate=0.055,
            l2_regularization=0.8,
            random_state=42,
        )
        model.fit(train[self.FEATURES], train["label"])
        predictions = model.predict(test[self.FEATURES])
        balanced = float(balanced_accuracy_score(test["label"], predictions))
        majority = float(test["label"].value_counts(normalize=True).max())
        validated = balanced >= max(0.40, majority + 0.03)

        latest = dataset[self.FEATURES].iloc[[-1]]
        probabilities = model.predict_proba(latest)[0]
        by_class = {int(label): float(prob) for label, prob in zip(model.classes_, probabilities)}
        predicted = int(model.predict(latest)[0])
        return {
            "available": True,
            "validated": validated,
            "direction": {-1: "SELL", 0: "HOLD", 1: "BUY"}[predicted],
            "model_probability": round(by_class.get(predicted, 0.0), 4),
            "probabilities": {
                "SELL": round(by_class.get(-1, 0.0), 4),
                "HOLD": round(by_class.get(0, 0.0), 4),
                "BUY": round(by_class.get(1, 0.0), 4),
            },
            "balanced_accuracy": round(balanced, 4),
            "majority_baseline": round(majority, 4),
            "training_samples": len(train),
            "validation_samples": len(test),
            "probability_note": "Model probability is not a guarantee and is not claimed to be calibrated.",
        }

    @staticmethod
    def _unavailable(reason: str) -> dict[str, Any]:
        return {"available": False, "validated": False, "reason": reason}


class MarketIntelligenceService:
    def __init__(self) -> None:
        self.data = MarketDataService()
        self.forecaster = MarketForecastService()
        self.coordinator = CoordinatorAgentV2()

    def analyze(self, pair: str, timeframe: str, screenshot: str | None = None) -> dict[str, Any]:
        market = self.data.load(pair, timeframe, limit=2000)
        if market["data_status"] == "unavailable":
            raise ValueError("No real market data is available for this selection")

        raw = pd.DataFrame(market["candles"])
        raw["timestamp"] = pd.to_datetime(raw["time"], unit="s", utc=True)
        featured = TechnicalFeatureEngine.calculate_all(raw.set_index("timestamp"))
        indicators = TechnicalFeatureEngine.get_current_values(featured)
        latest = featured.iloc[-1]

        coordinator = self.coordinator.generate_final_signal(pair, pair[:3], pair[3:])
        forecast = self.forecaster.forecast(pair, timeframe, market["latest_candle_at"])
        agent_direction = {-1: "SELL", 0: "HOLD", 1: "BUY"}.get(
            int(coordinator.get("final_signal", 0)), "HOLD"
        )
        metadata = coordinator.get("weight_metadata") or {}
        evidence = float(metadata.get("evidence_coverage", 0))
        conflicts = bool(coordinator.get("conflicts_detected", False))

        action = agent_direction
        blockers: list[str] = []
        if market["data_status"] == "stale":
            blockers.append("Stored market data is stale")
        if evidence < 0.65:
            blockers.append("Agent evidence coverage is below 65%")
        if conflicts:
            blockers.append("Specialized agents materially disagree")
        if forecast.get("validated") and forecast.get("direction") not in {agent_direction, "HOLD"}:
            blockers.append("Validated historical model disagrees with the agent direction")
        if blockers:
            action = "HOLD"

        price = float(market["quote"]["bid"] if market["quote"] else market["latest_price"])
        atr = float(latest.get("atr_14", 0) or 0)
        recent = featured.tail(40)
        levels = {
            "support": _finite(recent["low"].min()),
            "resistance": _finite(recent["high"].max()),
            "suggested_stop": _finite(price - atr * 1.5 if action == "BUY" else price + atr * 1.5),
            "suggested_target": _finite(price + atr * 2.5 if action == "BUY" else price - atr * 2.5),
        }
        if action == "HOLD":
            levels["suggested_stop"] = None
            levels["suggested_target"] = None

        result = {
            "pair": pair,
            "timeframe": timeframe,
            "horizon": HORIZONS[timeframe]["label"],
            "action": action,
            "approved_for_paper_trade": (
                action in {"BUY", "SELL"} and not blockers and market["market_open"]
            ),
            "market_timestamp": market["latest_candle_at"],
            "latest_price": price,
            "data_status": market["data_status"],
            "data_source": market["data_source"],
            "market_open": market["market_open"],
            "indicators": {
                "rsi_14": _finite(indicators.get("rsi_14"), 2),
                "macd_diff": _finite(indicators.get("macd_diff")),
                "adx": _finite(indicators.get("adx"), 2),
                "atr_14": _finite(latest.get("atr_14")),
                "ema_21": _finite(latest.get("ema_21")),
                "ema_55": _finite(latest.get("ema_55")),
            },
            "levels": levels,
            "forecast": forecast,
            "agent_consensus": {
                "direction": agent_direction,
                "confidence": _finite(coordinator.get("confidence"), 4),
                "weighted_score": _finite(coordinator.get("weighted_score"), 4),
                "market_regime": coordinator.get("market_regime", "unknown"),
                "evidence_coverage": round(evidence, 4),
                "conflicts_detected": conflicts,
                "weights": coordinator.get("effective_weights", {}),
                "agents": coordinator.get("agent_signals", {}),
            },
            "blockers": blockers,
            "warnings": (
                ["The FX market is closed; guidance uses the latest completed session."]
                if not market["market_open"]
                else []
            ),
            "visual_observations": self._inspect_capture(screenshot) if screenshot else None,
        }
        result["explanation"] = self._explain(result)
        return result

    @staticmethod
    def _inspect_capture(screenshot: str) -> str | None:
        """Extract advisory chart observations; pixels never affect the trade action."""
        try:
            encoded = screenshot.split(",", 1)[1] if "," in screenshot else screenshot
            base64.b64decode(encoded, validate=True)
            base_url = getattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
            response = requests.post(
                f"{base_url}/api/generate",
                json={
                    "model": getattr(settings, "OLLAMA_VISION_MODEL", "moondream"),
                    "stream": False,
                    "prompt": (
                        "Describe only visible chart structure: trend, consolidation, obvious support "
                        "or resistance, and uncertainty. Do not give a BUY or SELL instruction."
                    ),
                    "images": [encoded],
                    "options": {"temperature": 0.1, "num_predict": 120},
                },
                timeout=60,
            )
            response.raise_for_status()
            return str(response.json().get("response", "")).strip() or None
        except Exception:
            return None

    def _explain(self, result: dict[str, Any]) -> str:
        return self._deterministic_explanation(result)

    @staticmethod
    def _deterministic_explanation(result: dict[str, Any]) -> str:
        consensus = result["agent_consensus"]
        forecast = result["forecast"]
        explanation = (
            f"The current evidence supports {result['action']} for {result['horizon'].lower()}. "
            f"Agent evidence coverage is {consensus['evidence_coverage']:.0%}"
        )
        if forecast.get("validated"):
            explanation += (
                f", while the historical model points to {forecast['direction']} "
                f"with {forecast['balanced_accuracy']:.0%} held-out balanced accuracy"
            )
        elif forecast.get("available"):
            explanation += ", and the historical model was excluded because it did not beat its validation baseline"
        return explanation + ". This is decision support for paper trading, not a profit guarantee."
