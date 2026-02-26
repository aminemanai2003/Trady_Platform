"""Economic calendar endpoint + feature engineering endpoint."""
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def economic_calendar(request):
    """Get upcoming economic events."""
    events = [
        {"date": "2026-02-24T13:30:00Z", "currency": "USD", "event": "Core Durable Goods Orders", "importance": "MEDIUM", "forecast": "0.2%", "previous": "-0.3%"},
        {"date": "2026-02-25T10:00:00Z", "currency": "EUR", "event": "ECB President Lagarde Speech", "importance": "HIGH", "forecast": None, "previous": None},
        {"date": "2026-02-25T15:00:00Z", "currency": "USD", "event": "CB Consumer Confidence", "importance": "HIGH", "forecast": "102.5", "previous": "104.1"},
        {"date": "2026-02-26T13:30:00Z", "currency": "USD", "event": "GDP (QoQ)", "importance": "HIGH", "forecast": "3.3%", "previous": "4.9%"},
        {"date": "2026-02-27T07:00:00Z", "currency": "GBP", "event": "BoE Gov Bailey Speech", "importance": "HIGH", "forecast": None, "previous": None},
        {"date": "2026-02-27T13:30:00Z", "currency": "USD", "event": "Core PCE Price Index (MoM)", "importance": "HIGH", "forecast": "0.2%", "previous": "0.2%"},
        {"date": "2026-02-27T13:30:00Z", "currency": "USD", "event": "Initial Jobless Claims", "importance": "MEDIUM", "forecast": "210K", "previous": "201K"},
        {"date": "2026-02-28T00:30:00Z", "currency": "JPY", "event": "Tokyo CPI (YoY)", "importance": "HIGH", "forecast": "2.0%", "previous": "1.8%"},
        {"date": "2026-02-28T10:00:00Z", "currency": "EUR", "event": "CPI Flash Estimate (YoY)", "importance": "HIGH", "forecast": "2.7%", "previous": "2.8%"},
        {"date": "2026-02-28T08:00:00Z", "currency": "CHF", "event": "GDP (QoQ)", "importance": "HIGH", "forecast": "0.4%", "previous": "0.3%"},
        {"date": "2026-03-03T14:45:00Z", "currency": "USD", "event": "ISM Manufacturing PMI", "importance": "HIGH", "forecast": "49.5", "previous": "49.1"},
        {"date": "2026-03-05T13:15:00Z", "currency": "USD", "event": "ADP Non-Farm Employment", "importance": "HIGH", "forecast": "150K", "previous": "164K"},
        {"date": "2026-03-06T10:15:00Z", "currency": "EUR", "event": "ECB Interest Rate Decision", "importance": "HIGH", "forecast": "4.25%", "previous": "4.50%"},
        {"date": "2026-03-07T13:30:00Z", "currency": "USD", "event": "Non-Farm Payrolls", "importance": "HIGH", "forecast": "200K", "previous": "216K"},
        {"date": "2026-03-07T13:30:00Z", "currency": "USD", "event": "Unemployment Rate", "importance": "HIGH", "forecast": "3.8%", "previous": "3.7%"},
    ]
    return Response(events)


@api_view(["GET"])
def technical_indicators(request, pair):
    """Get technical indicators for a currency pair."""
    from agents.services.indicators import generate_technical_analysis
    from data.views import _mock_prices

    pair_map = {
        "eurusd": "EURUSD", "usdjpy": "USDJPY",
        "usdchf": "USDCHF", "gbpusd": "GBPUSD",
    }
    symbol = pair_map.get(pair.lower(), pair.upper())

    # Try InfluxDB first, fallback to mock
    try:
        from django.conf import settings
        from influxdb_client import InfluxDBClient
        client = InfluxDBClient(
            url=settings.INFLUXDB_URL,
            token=settings.INFLUXDB_TOKEN,
            org=settings.INFLUXDB_ORG,
        )
        query_api = client.query_api()
        query = f'''
            from(bucket: "{settings.INFLUXDB_BUCKET}")
            |> range(start: -365d)
            |> filter(fn: (r) => r["symbol"] == "{symbol}")
            |> filter(fn: (r) => r["timeframe"] == "1D")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            |> sort(columns: ["_time"])
            |> limit(n: 250)
        '''
        tables = query_api.query(query)
        prices = []
        for table in tables:
            for record in table.records:
                prices.append({
                    "open": record.values.get("open", 0),
                    "high": record.values.get("high", 0),
                    "low": record.values.get("low", 0),
                    "close": record.values.get("close", 0),
                    "volume": record.values.get("volume", 0),
                })
        client.close()
    except Exception:
        prices = _mock_prices(symbol, 250)

    analysis = generate_technical_analysis(prices)
    analysis["pair"] = symbol
    return Response(analysis)
