"""
yfinance OHLCV collector — fetches hourly FX candles for free.

Source: Yahoo Finance via yfinance library (no API key required).
Stores results in SQLite OHLCVCandle model, timeframe="1h".

Limits:
  - 1h data available for up to 730 days (yfinance limitation)
  - FX tickers on Yahoo Finance: EURUSD=X, GBPUSD=X, USDJPY=X, USDCHF=X

Schedule recommendation: every 1-4 hours (staggered after AV).
"""
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Yahoo Finance FX tickers → internal pair name
PAIRS = {
    "EURUSD=X": "EURUSD",
    "GBPUSD=X": "GBPUSD",
    "USDJPY=X": "USDJPY",
    "USDCHF=X": "USDCHF",
}

LOOKBACK_DAYS = 365   # fetch up to 1 year of hourly data on first run


def collect_yfinance_ohlcv(lookback_days: int = LOOKBACK_DAYS) -> dict:
    """
    Fetch hourly OHLCV from Yahoo Finance and store in SQLite.

    Args:
        lookback_days: How far back to fetch on first run (default 365 days).
                       Subsequent runs only fetch missing candles.

    Returns:
        {"inserted": int, "skipped": int, "errors": list[str]}
    """
    try:
        import yfinance as yf
    except ImportError:
        return {"inserted": 0, "skipped": 0, "errors": ["yfinance not installed — run: pip install yfinance"]}

    from scheduling.models import OHLCVCandle, IngestionLog

    log = IngestionLog.objects.create(source="ohlcv", status="running")

    total_inserted = 0
    total_skipped = 0
    errors: list[str] = []

    try:
        end_dt = datetime.now(tz=timezone.utc)

        for ticker, pair_name in PAIRS.items():
            try:
                # Determine start date: fetch only new candles after the latest stored one
                latest = (
                    OHLCVCandle.objects
                    .filter(symbol=pair_name, timeframe="1h")
                    .order_by("-timestamp")
                    .values_list("timestamp", flat=True)
                    .first()
                )
                if latest is not None:
                    # Fetch from last stored candle with 2h overlap to avoid gaps
                    latest_aware = latest if latest.tzinfo else latest.replace(tzinfo=timezone.utc)
                    start_dt = latest_aware - timedelta(hours=2)
                else:
                    start_dt = end_dt - timedelta(days=lookback_days)

                logger.info(f"[YF] {pair_name}: fetching 1h from {start_dt.date()} → {end_dt.date()}")

                ticker_obj = yf.Ticker(ticker)
                df = ticker_obj.history(
                    start=start_dt.strftime("%Y-%m-%d"),
                    end=end_dt.strftime("%Y-%m-%d"),
                    interval="1h",
                    auto_adjust=True,
                    back_adjust=False,
                )

                if df.empty:
                    logger.warning(f"[YF] {pair_name}: no data returned")
                    errors.append(f"{pair_name}: no data returned")
                    continue

                inserted = 0
                skipped = 0

                for ts, row in df.iterrows():
                    # Standardise timezone
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    else:
                        ts = ts.tz_convert("UTC").replace(tzinfo=timezone.utc)

                    _, created = OHLCVCandle.objects.get_or_create(
                        symbol=pair_name,
                        timeframe="1h",
                        timestamp=ts,
                        defaults={
                            "open":   float(row["Open"]),
                            "high":   float(row["High"]),
                            "low":    float(row["Low"]),
                            "close":  float(row["Close"]),
                            "volume": float(row.get("Volume", 0) or 0),
                        },
                    )
                    if created:
                        inserted += 1
                    else:
                        skipped += 1

                total_inserted += inserted
                total_skipped += skipped
                logger.info(f"[YF] {pair_name}/1h: inserted={inserted} skipped={skipped}")

            except Exception as exc:
                msg = f"{pair_name}: {exc}"
                errors.append(msg)
                logger.warning(f"[YF] {msg}", exc_info=True)

        log.records_inserted = total_inserted
        log.status = "success" if not errors else "partial"
        log.error_message = "; ".join(errors) if errors else ""
        log.finished_at = datetime.now(tz=timezone.utc)
        log.save()

        return {"inserted": total_inserted, "skipped": total_skipped, "errors": errors}

    except Exception as exc:
        log.status = "error"
        log.error_message = str(exc)
        log.finished_at = datetime.now(tz=timezone.utc)
        log.save()
        logger.error(f"[YF] fatal error: {exc}", exc_info=True)
        return {"inserted": 0, "skipped": 0, "errors": [str(exc)]}
