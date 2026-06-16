"""Views for data app — prices from InfluxDB, indicators and news from PostgreSQL."""
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from .models import EconomicIndicator, NewsArticle, EconomicEvent
from .serializers import (
    EconomicIndicatorSerializer,
    NewsArticleSerializer,
    EconomicEventSerializer,
)


class EconomicIndicatorViewSet(viewsets.ReadOnlyModelViewSet):
    """FRED economic indicators."""
    queryset = EconomicIndicator.objects.all()
    serializer_class = EconomicIndicatorSerializer
    filterset_fields = ["series_id"]

    def get_queryset(self):
        qs = super().get_queryset()
        series_id = self.request.query_params.get("series_id")
        if series_id:
            qs = qs.filter(series_id=series_id)
        return qs[:500]


class NewsArticleViewSet(viewsets.ReadOnlyModelViewSet):
    """Reuters news articles."""
    queryset = NewsArticle.objects.all()
    serializer_class = NewsArticleSerializer

    def get_queryset(self):
        return super().get_queryset()[:50]


class EconomicEventViewSet(viewsets.ReadOnlyModelViewSet):
    """Economic calendar events."""
    queryset = EconomicEvent.objects.all()
    serializer_class = EconomicEventSerializer


@api_view(["GET"])
def prices_view(request, pair):
    """Get OHLCV price data from InfluxDB for a given currency pair."""
    timeframe = request.query_params.get("timeframe", "1D")
    limit = int(request.query_params.get("limit", 200))

    # Map pair names to symbols
    pair_map = {
        "eurusd": "EURUSD", "usdjpy": "USDJPY",
        "usdchf": "USDCHF", "gbpusd": "GBPUSD",
    }
    symbol = pair_map.get(pair.lower(), pair.upper())

    try:
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
            |> filter(fn: (r) => r["timeframe"] == "{timeframe}")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            |> sort(columns: ["_time"], desc: true)
            |> limit(n: {limit})
        '''
        tables = query_api.query(query)
        data = []
        for table in tables:
            for record in table.records:
                data.append({
                    "time": record.get_time().isoformat(),
                    "open": record.values.get("open", 0),
                    "high": record.values.get("high", 0),
                    "low": record.values.get("low", 0),
                    "close": record.values.get("close", 0),
                    "volume": record.values.get("volume", 0),
                    "symbol": symbol,
                    "timeframe": timeframe,
                })
        client.close()
        return Response(data)
    except Exception:
        return Response(
            {
                "error": "Real market data is currently unavailable",
                "symbol": symbol,
                "timeframe": timeframe,
                "source": None,
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
