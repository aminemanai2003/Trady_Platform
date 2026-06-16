"""
Price Broadcaster — APScheduler job that pushes live price ticks to
WebSocket groups every 5 seconds.

Start from Django management command or Celery beat.
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

PAIRS = ["EURUSD", "USDJPY", "GBPUSD", "USDCHF"]


def broadcast_prices():
    """
    Fetch latest prices from InfluxDB and broadcast to each pair's WS group.
    Safe to call from any context (async_to_sync wrapper used internally).
    """
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        from data_layer.timeseries_loader import TimeSeriesLoader

        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        loader = TimeSeriesLoader()

        for pair in PAIRS:
            try:
                df = loader.load_ohlcv(pair, limit=1)
                if df is None or df.empty:
                    continue

                row = df.iloc[-1]
                price = float(row.get("close", 0))
                spread = price * 0.00015  # approximate 1.5 pip spread

                tick = {
                    "pair": pair,
                    "price": round(price, 5),
                    "bid": round(price - spread / 2, 5),
                    "ask": round(price + spread / 2, 5),
                    "timestamp": datetime.now().isoformat(),
                }

                async_to_sync(channel_layer.group_send)(
                    f"prices_{pair}",
                    {"type": "price.tick", "data": tick},
                )
            except Exception as exc:
                logger.debug(f"Price broadcast failed for {pair}: {exc}")

    except Exception as exc:
        logger.warning(f"Price broadcaster error: {exc}")
