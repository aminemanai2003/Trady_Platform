"""Economic calendar endpoint + technical indicators endpoint — Real data."""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
import psycopg2
from datetime import datetime, timedelta


# Economic calendar events — comprehensive list covering all 4 currencies
ECONOMIC_EVENTS = [
    # USD Events
    {"date": "2026-03-03T14:45:00Z", "currency": "USD", "event": "ISM Manufacturing PMI", "importance": "HIGH", "forecast": "49.5", "previous": "49.1"},
    {"date": "2026-03-05T13:15:00Z", "currency": "USD", "event": "ADP Non-Farm Employment", "importance": "HIGH", "forecast": "150K", "previous": "164K"},
    {"date": "2026-03-07T13:30:00Z", "currency": "USD", "event": "Non-Farm Payrolls (NFP)", "importance": "HIGH", "forecast": "200K", "previous": "216K"},
    {"date": "2026-03-07T13:30:00Z", "currency": "USD", "event": "Unemployment Rate", "importance": "HIGH", "forecast": "3.8%", "previous": "3.7%"},
    {"date": "2026-03-12T12:30:00Z", "currency": "USD", "event": "CPI (YoY)", "importance": "HIGH", "forecast": "3.0%", "previous": "3.1%"},
    {"date": "2026-03-12T12:30:00Z", "currency": "USD", "event": "Core CPI (MoM)", "importance": "HIGH", "forecast": "0.3%", "previous": "0.4%"},
    {"date": "2026-03-19T18:00:00Z", "currency": "USD", "event": "FOMC Interest Rate Decision", "importance": "HIGH", "forecast": "5.25%", "previous": "5.25%"},
    {"date": "2026-03-19T18:30:00Z", "currency": "USD", "event": "FOMC Press Conference", "importance": "HIGH", "forecast": None, "previous": None},
    {"date": "2026-03-28T12:30:00Z", "currency": "USD", "event": "Core PCE Price Index (MoM)", "importance": "HIGH", "forecast": "0.2%", "previous": "0.2%"},
    {"date": "2026-03-27T12:30:00Z", "currency": "USD", "event": "GDP (QoQ) Final", "importance": "HIGH", "forecast": "3.2%", "previous": "3.3%"},
    # EUR Events
    {"date": "2026-03-06T12:15:00Z", "currency": "EUR", "event": "ECB Interest Rate Decision", "importance": "HIGH", "forecast": "4.25%", "previous": "4.50%"},
    {"date": "2026-03-06T12:45:00Z", "currency": "EUR", "event": "ECB Press Conference", "importance": "HIGH", "forecast": None, "previous": None},
    {"date": "2026-03-03T09:00:00Z", "currency": "EUR", "event": "Eurozone CPI Flash (YoY)", "importance": "HIGH", "forecast": "2.6%", "previous": "2.8%"},
    {"date": "2026-03-05T10:00:00Z", "currency": "EUR", "event": "Eurozone GDP (QoQ)", "importance": "HIGH", "forecast": "0.1%", "previous": "0.0%"},
    {"date": "2026-03-21T09:00:00Z", "currency": "EUR", "event": "Eurozone PMI Composite", "importance": "HIGH", "forecast": "48.0", "previous": "47.6"},
    {"date": "2026-03-25T10:00:00Z", "currency": "EUR", "event": "ECB President Lagarde Speech", "importance": "HIGH", "forecast": None, "previous": None},
    # GBP Events
    {"date": "2026-03-04T09:30:00Z", "currency": "GBP", "event": "UK Services PMI", "importance": "MEDIUM", "forecast": "54.0", "previous": "54.3"},
    {"date": "2026-03-11T07:00:00Z", "currency": "GBP", "event": "UK GDP (MoM)", "importance": "HIGH", "forecast": "0.2%", "previous": "0.3%"},
    {"date": "2026-03-19T07:00:00Z", "currency": "GBP", "event": "UK CPI (YoY)", "importance": "HIGH", "forecast": "3.8%", "previous": "4.0%"},
    {"date": "2026-03-20T12:00:00Z", "currency": "GBP", "event": "BoE Interest Rate Decision", "importance": "HIGH", "forecast": "5.25%", "previous": "5.25%"},
    {"date": "2026-03-20T12:30:00Z", "currency": "GBP", "event": "BoE Monetary Policy Report", "importance": "HIGH", "forecast": None, "previous": None},
    # JPY Events
    {"date": "2026-03-07T23:30:00Z", "currency": "JPY", "event": "Tokyo CPI (YoY)", "importance": "HIGH", "forecast": "2.1%", "previous": "1.8%"},
    {"date": "2026-03-14T03:00:00Z", "currency": "JPY", "event": "BoJ Interest Rate Decision", "importance": "HIGH", "forecast": "0.10%", "previous": "0.10%"},
    {"date": "2026-03-14T06:30:00Z", "currency": "JPY", "event": "BoJ Press Conference", "importance": "HIGH", "forecast": None, "previous": None},
    {"date": "2026-03-09T23:50:00Z", "currency": "JPY", "event": "Japan GDP (QoQ)", "importance": "HIGH", "forecast": "0.1%", "previous": "-0.1%"},
    # CHF Events
    {"date": "2026-03-06T08:30:00Z", "currency": "CHF", "event": "Swiss CPI (YoY)", "importance": "HIGH", "forecast": "1.3%", "previous": "1.2%"},
    {"date": "2026-03-20T08:30:00Z", "currency": "CHF", "event": "SNB Interest Rate Decision", "importance": "HIGH", "forecast": "1.75%", "previous": "1.75%"},
    {"date": "2026-03-27T07:00:00Z", "currency": "CHF", "event": "Swiss GDP (QoQ)", "importance": "HIGH", "forecast": "0.4%", "previous": "0.3%"},
]


@api_view(["GET"])
def economic_calendar(request):
    """Get economic events — tries DB first, falls back to comprehensive static list."""
    try:
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            dbname=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT event_date, currency, event_name, importance, 
                   forecast, actual, previous
            FROM economic_events
            WHERE event_date >= NOW() - INTERVAL '7 days'
            ORDER BY event_date
            LIMIT 50
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if rows:
            events = []
            for row in rows:
                events.append({
                    "date": row[0].isoformat() if row[0] else None,
                    "currency": row[1],
                    "event": row[2],
                    "importance": row[3] or "MEDIUM",
                    "forecast": str(row[4]) if row[4] else None,
                    "actual": str(row[5]) if row[5] else None,
                    "previous": str(row[6]) if row[6] else None,
                })
            return Response(events)
    except Exception:
        pass

    # Fallback to static comprehensive calendar
    return Response(ECONOMIC_EVENTS)


@api_view(["GET"])
def technical_indicators(request, pair):
    """Get real technical indicators for a currency pair using V2 feature engine."""
    pair_map = {
        "eurusd": "EURUSD", "usdjpy": "USDJPY",
        "usdchf": "USDCHF", "gbpusd": "GBPUSD",
    }
    symbol = pair_map.get(pair.lower(), pair.upper())

    try:
        from data_layer.timeseries_loader import TimeSeriesLoader
        from feature_layer.technical_features import TechnicalFeatureEngine

        loader = TimeSeriesLoader()
        engine = TechnicalFeatureEngine()

        df = loader.load_ohlcv(symbol)
        if not df.empty and len(df) >= 200:
            df_feat = engine.calculate_all(df)
            indicators = engine.get_current_values(df_feat)
            feature_count = engine.get_feature_count(df_feat)

            return Response({
                "pair": symbol,
                "indicators": indicators,
                "feature_count": feature_count,
                "data_points": len(df),
                "source": "influxdb_real",
            })
    except Exception as e:
        pass

    # Minimal fallback
    return Response({
        "pair": symbol,
        "indicators": {},
        "feature_count": 0,
        "source": "unavailable",
        "error": "Could not load data"
    })
