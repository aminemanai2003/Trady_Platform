"""Paper Trading API Views."""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from paper_trading.services import portfolio


class PositionsView(APIView):
    """GET open positions / POST manual open / DELETE all (dev only)."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(portfolio.get_open_positions())

    def post(self, request):
        """Manually open a paper position (for testing)."""
        pair = str(request.data.get("pair", "EURUSD")).upper()
        side = str(request.data.get("side", "BUY")).upper()
        size = float(request.data.get("size", 0.1))
        entry_price = float(request.data.get("entry_price", 1.0))
        stop_loss = request.data.get("stop_loss")
        take_profit = request.data.get("take_profit")

        pos = portfolio.open_position(
            pair=pair,
            side=side,
            size=size,
            entry_price=entry_price,
            stop_loss=float(stop_loss) if stop_loss else None,
            take_profit=float(take_profit) if take_profit else None,
        )
        from paper_trading.services.portfolio import _serialize_position
        return Response(_serialize_position(pos), status=status.HTTP_201_CREATED)


class PositionDetailView(APIView):
    """PATCH to update price / DELETE to close a position."""

    permission_classes = [AllowAny]

    def patch(self, request, pk):
        current_price = float(request.data.get("current_price", 0))
        result = portfolio.update_position(pk, current_price)
        if result is None:
            return Response({"error": "Position not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(result)

    def delete(self, request, pk):
        close_price = request.data.get("close_price")
        result = portfolio.close_position(pk, float(close_price) if close_price else None)
        if result is None:
            return Response({"error": "Position not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(result)


class TradeHistoryView(APIView):
    """GET list of closed paper trades."""

    permission_classes = [AllowAny]

    def get(self, request):
        limit = int(request.query_params.get("limit", 100))
        return Response(portfolio.get_trade_history(limit))


class PortfolioStatsView(APIView):
    """GET aggregated portfolio statistics."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(portfolio.get_portfolio_stats())
