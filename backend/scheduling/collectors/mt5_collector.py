"""
MT5 → InfluxDB collector (callable wrapper).

Pulls fresh OHLC candles for the configured FX pairs and timeframes from a
locally-running MetaTrader 5 terminal and writes them into InfluxDB. Designed
to be triggered on demand from the UI's "Ingest Data" panel, so users can
heal stale data without touching the CLI.

Returns the same `{inserted, skipped, errors}` shape as the other collectors
so the front-end status poller can render a consistent result.

The legacy standalone script at `backend/acquisition/mt5_collector.py` remains
intact for one-off backfills from a shell.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

PAIRS = ("EURUSD", "GBPUSD", "USDJPY", "USDCHF")

# Map (frontend timeframe, MT5 constant name). We resolve the MT5 constant
# lazily because importing MetaTrader5 fails on non-Windows hosts.
TIMEFRAME_NAMES = {
    "1h": "TIMEFRAME_H1",
    "4h": "TIMEFRAME_H4",
    "1d": "TIMEFRAME_D1",
}

DEFAULT_DAYS_BACK = 90  # enough to heal a multi-week stale gap quickly


def _connect_mt5(mt5) -> tuple[bool, str | None]:
    """Initialise MT5 and (optionally) log in. Returns (ok, error)."""
    if not mt5.initialize():
        return False, f"MT5 initialize failed: {mt5.last_error()}"

    login_raw = os.getenv("MT5_LOGIN")
    password = os.getenv("MT5_PASSWORD")
    server = os.getenv("MT5_SERVER")

    if login_raw and password and server:
        try:
            login = int(login_raw)
        except ValueError:
            login = login_raw
        if not mt5.login(login, password, server):
            return False, f"MT5 login failed: {mt5.last_error()}"
    else:
        if mt5.account_info() is None:
            return False, "MT5 initialized but no account is authenticated"

    return True, None


def collect_mt5_ohlcv(
    pairs: tuple[str, ...] = PAIRS,
    timeframes: tuple[str, ...] = ("1h", "4h", "1d"),
    days_back: int = DEFAULT_DAYS_BACK,
) -> dict[str, Any]:
    """
    Fetch recent candles from MT5 and write them to InfluxDB.

    Args:
        pairs: FX symbols to fetch.
        timeframes: list of frontend timeframe keys (1h/4h/1d).
        days_back: how far back to pull candles per (pair, timeframe).

    Returns:
        {"inserted": int, "skipped": int, "errors": list[str]}
    """
    errors: list[str] = []
    inserted_total = 0
    skipped_total = 0

    # Resolve InfluxDB settings via Django (already configured for the project)
    try:
        from django.conf import settings as dj_settings
        influx_url = getattr(dj_settings, "INFLUX_URL", None) or os.getenv("INFLUXDB_URL")
        influx_token = getattr(dj_settings, "INFLUX_TOKEN", None) or os.getenv("INFLUXDB_TOKEN")
        influx_org = getattr(dj_settings, "INFLUX_ORG", None) or os.getenv("INFLUXDB_ORG")
        influx_bucket = getattr(dj_settings, "INFLUX_BUCKET", None) or os.getenv("INFLUXDB_BUCKET")
    except Exception as exc:
        return {"inserted": 0, "skipped": 0, "errors": [f"settings unavailable: {exc}"]}

    if not all([influx_url, influx_token, influx_org, influx_bucket]):
        return {
            "inserted": 0,
            "skipped": 0,
            "errors": ["InfluxDB is not configured (URL/TOKEN/ORG/BUCKET missing)"],
        }

    try:
        import MetaTrader5 as mt5  # type: ignore
    except ImportError:
        return {
            "inserted": 0,
            "skipped": 0,
            "errors": [
                "MetaTrader5 package not installed on this server. "
                "MT5 ingestion only works from the Windows host that runs the terminal."
            ],
        }

    try:
        from influxdb_client import InfluxDBClient, Point
        from influxdb_client.client.write_api import SYNCHRONOUS
    except ImportError:
        return {
            "inserted": 0,
            "skipped": 0,
            "errors": ["influxdb_client not installed"],
        }

    # Connect to MT5
    ok, err = _connect_mt5(mt5)
    if not ok:
        return {"inserted": 0, "skipped": 0, "errors": [err or "MT5 connection failed"]}

    # IngestionLog gives the Data Freshness panel a paper trail
    try:
        from scheduling.models import IngestionLog
        log = IngestionLog.objects.create(source="ohlcv", status="running")
    except Exception:
        log = None

    client = None
    try:
        client = InfluxDBClient(url=influx_url, token=influx_token, org=influx_org)
        write_api = client.write_api(write_options=SYNCHRONOUS)

        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=max(int(days_back), 1))

        for symbol in pairs:
            # Make sure the symbol is selected in MarketWatch, otherwise copy_rates returns None
            try:
                mt5.symbol_select(symbol, True)
            except Exception:
                pass

            for tf_key in timeframes:
                tf_const_name = TIMEFRAME_NAMES.get(tf_key.lower())
                if not tf_const_name:
                    errors.append(f"{symbol}/{tf_key}: unsupported timeframe")
                    continue
                tf_const = getattr(mt5, tf_const_name, None)
                if tf_const is None:
                    errors.append(f"{symbol}/{tf_key}: MT5 has no {tf_const_name}")
                    continue

                try:
                    rates = mt5.copy_rates_range(symbol, tf_const, start_dt, end_dt)
                except Exception as exc:
                    errors.append(f"{symbol}/{tf_key}: {exc}")
                    continue

                if rates is None or len(rates) == 0:
                    last_err = mt5.last_error() if hasattr(mt5, "last_error") else "no data"
                    errors.append(f"{symbol}/{tf_key}: no candles ({last_err})")
                    continue

                # InfluxDB ignores duplicates at the (measurement, tags, time) level
                # so we treat the whole batch as inserted; we can't cheaply tell which
                # were already present without an extra read, and matching the other
                # collectors' shape is more important than perfect accounting.
                # NOTE: MT5's copy_rates_range returns a numpy structured array; rows
                # are numpy.void objects, so we use rates.dtype.names and bracket
                # access — `.get()` would raise AttributeError.
                field_names = set(getattr(rates.dtype, "names", ()) or ())
                points = []
                for row in rates:
                    ts = datetime.fromtimestamp(int(row["time"]), tz=timezone.utc)
                    volume = 0
                    if "tick_volume" in field_names:
                        try:
                            volume = int(row["tick_volume"])
                        except (TypeError, ValueError):
                            volume = 0
                    elif "real_volume" in field_names:
                        try:
                            volume = int(row["real_volume"])
                        except (TypeError, ValueError):
                            volume = 0
                    point = (
                        Point("forex_prices")
                        .tag("symbol", symbol)
                        .tag("timeframe", tf_key.lower())
                        .field("open", float(row["open"]))
                        .field("high", float(row["high"]))
                        .field("low", float(row["low"]))
                        .field("close", float(row["close"]))
                        .field("volume", volume)
                        .time(ts)
                    )
                    points.append(point)

                try:
                    write_api.write(bucket=influx_bucket, org=influx_org, record=points)
                    inserted_total += len(points)
                    logger.info("[MT5] %s/%s wrote %d candles", symbol, tf_key, len(points))
                except Exception as exc:
                    errors.append(f"{symbol}/{tf_key} write: {exc}")

        if log is not None:
            log.records_inserted = inserted_total
            log.status = "success" if not errors else "partial"
            log.error_message = "; ".join(errors)[:1000]
            log.finished_at = datetime.now(tz=timezone.utc)
            log.save()

        return {"inserted": inserted_total, "skipped": skipped_total, "errors": errors}

    except Exception as exc:
        logger.exception("[MT5] fatal error during ingest")
        if log is not None:
            log.status = "error"
            log.error_message = str(exc)
            log.finished_at = datetime.now(tz=timezone.utc)
            log.save()
        return {"inserted": inserted_total, "skipped": skipped_total, "errors": errors + [str(exc)]}
    finally:
        try:
            if client is not None:
                client.close()
        except Exception:
            pass
        try:
            mt5.shutdown()
        except Exception:
            pass
