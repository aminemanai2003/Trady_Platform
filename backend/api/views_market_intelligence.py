from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .market_intelligence import MarketDataService, MarketIntelligenceService


@api_view(["GET"])
def market_candles(request):
    pair = str(request.query_params.get("pair", "EURUSD")).upper()
    timeframe = str(request.query_params.get("timeframe", "1h")).lower()
    try:
        limit = max(50, min(int(request.query_params.get("limit", 500)), 2000))
        result = MarketDataService().load(pair, timeframe, limit)
        response_status = (
            status.HTTP_200_OK
            if result["data_status"] != "unavailable"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(result, status=response_status)
    except (TypeError, ValueError) as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def market_analyze(request):
    pair = str(request.data.get("pair", "EURUSD")).upper()
    timeframe = str(request.data.get("timeframe", "1h")).lower()
    try:
        screenshot = request.data.get("screenshot")
        if screenshot is not None and not isinstance(screenshot, str):
            return Response({"error": "Invalid screenshot"}, status=status.HTTP_400_BAD_REQUEST)
        if screenshot and len(screenshot) > 7_000_000:
            return Response({"error": "Chart capture is too large"}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        return Response(MarketIntelligenceService().analyze(pair, timeframe, screenshot))
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:
        return Response(
            {"error": "Market analysis failed", "detail": str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
