"""
Alpha Vantage FX collector — fetches OHLCV candles for forex pairs and stores in SQLite.
Requires ALPHA_VANTAGE_KEY in environment or .env file.
Free tier: 25 req/day.

Free endpoints used:
  - FX_DAILY   → stored as timeframe="1d"
  - FX_WEEKLY  → stored as timeframe="1w"

Note: FX_INTRADAY (hourly) is a premium-only endpoint on Alpha Vantage.
      Hourly candles are derived by resampling daily data in the signal layer.
"""
import os
import logging
import time
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

AV_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")
AV_BASE = "https://www.alphavantage.co/query"

# Pairs expressed as (from_symbol, to_symbol, pair_name)
PAIRS = [
    ("EUR", "USD", "EURUSD"),
    ("USD", "JPY", "USDJPY"),
    ("GBP", "USD", "GBPUSD"),
    ("USD", "CHF", "USDCHF"),
]


def _fetch_daily(from_sym: str, to_sym: str) -> list[dict]:
    """Fetch daily OHLCV from FX_DAILY (free tier)."""
    params = {
        "function": "FX_DAILY",
        "from_symbol": from_sym,
        "to_symbol": to_sym,
        "outputsize": "compact",   # last 100 trading days
        "apikey": AV_KEY,
    }
    resp = requests.get(AV_BASE, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    ts_key = "Time Series FX (Daily)"
    if ts_key not in data:
        error_msg = data.get("Information") or data.get("Note") or "Unknown AV error"
        raise ValueError(error_msg)

    candles = []
    for date_str, ohlcv in data[ts_key].items():
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(
            hour=0, minute=0, second=0, tzinfo=timezone.utc
        )
        candles.append({
            "timestamp": dt,
            "open": float(ohlcv["1. open"]),
            "high": float(ohlcv["2. high"]),
            "low": float(ohlcv["3. low"]),
            "close": float(ohlcv["4. close"]),
            "volume": 0,
            "timeframe": "1d",
        })
    return candles


def _fetch_weekly(from_sym: str, to_sym: str) -> list[dict]:
    """Fetch weekly OHLCV from FX_WEEKLY (free tier)."""
    params = {
        "function": "FX_WEEKLY",
        "from_symbol": from_sym,
        "to_symbol": to_sym,
        "apikey": AV_KEY,
    }
    resp = requests.get(AV_BASE, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    ts_key = "Time Series FX (Weekly)"
    if ts_key not in data:
        error_msg = data.get("Information") or data.get("Note") or "Unknown AV error"
        raise ValueError(error_msg)

    candles = []
    for date_str, ohlcv in data[ts_key].items():
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(
            hour=0, minute=0, second=0, tzinfo=timezone.utc
        )
        candles.append({
            "timestamp": dt,
            "open": float(ohlcv["1. open"]),
            "high": float(ohlcv["2. high"]),
            "low": float(ohlcv["3. low"]),
            "close": float(ohlcv["4. close"]),
            "volume": 0,
            "timeframe": "1w",
        })
    return candles


def collect_alpha_vantage_ohlcv() -> dict:
    """
    Fetch OHLCV for all pairs (daily + weekly) from Alpha Vantage and store in SQLite.
    Respects the free-tier rate limit: max 25 req/day, 5 req/min → 13s sleep between calls.
    Returns {'inserted': int, 'skipped': int, 'errors': list}
    """
    if not AV_KEY:
        logger.warning("ALPHA_VANTAGE_KEY not set — skipping OHLCV collection")
        return {"inserted": 0, "skipped": 0, "errors": ["ALPHA_VANTAGE_KEY missing"]}

    from scheduling.models import OHLCVCandle, IngestionLog

    log = IngestionLog.objects.create(source="ohlcv")
    total_inserted = 0
    total_skipped = 0
    errors = []

    try:
        for from_sym, to_sym, pair_name in PAIRS:
            for fetch_fn, timeframe in [(_fetch_daily, "1d"), (_fetch_weekly, "1w")]:
                try:
                    candles = fetch_fn(from_sym, to_sym)
                    inserted = 0
                    skipped = 0
                    for c in candles:
                        _, created = OHLCVCandle.objects.get_or_create(
                            symbol=pair_name,
                            timeframe=timeframe,
                            timestamp=c["timestamp"],
                            defaults={
                                "open": c["open"],
                                "high": c["high"],
                                "low": c["low"],
                                "close": c["close"],
                                "volume": c["volume"],
                            },
                        )
                        if created:
                            inserted += 1
                        else:
                            skipped += 1

                    total_inserted += inserted
                    total_skipped += skipped
                    logger.info(
                        f"[AV] {pair_name}/{timeframe}: inserted={inserted} skipped={skipped}"
                    )
                except Exception as exc:
                    msg = f"{pair_name}/{timeframe}: {exc}"
                    errors.append(msg)
                    logger.warning(f"[AV] {msg}")

                # Respect free tier: max 5 req/min
                time.sleep(13)

        log.records_inserted = total_inserted
        log.status = "success" if not errors else "partial"
        log.error_message = "; ".join(errors)
        log.finished_at = datetime.now(tz=timezone.utc)
        log.save()

        return {"inserted": total_inserted, "skipped": total_skipped, "errors": errors}

    except Exception as exc:
        log.status = "error"
        log.error_message = str(exc)
        log.finished_at = datetime.now(tz=timezone.utc)
        log.save()
        logger.error(f"[AV] fatal error: {exc}", exc_info=True)
        return {"inserted": 0, "skipped": 0, "errors": [str(exc)]}

