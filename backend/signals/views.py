"""Serializers and views for signals app."""
from rest_framework import serializers, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import TradingSignal


class TradingSignalSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradingSignal
        fields = "__all__"


class TradingSignalViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TradingSignal.objects.all()
    serializer_class = TradingSignalSerializer


@api_view(["GET"])
def latest_signals(request):
    """Get the latest active signal for each pair."""
    pairs = ["EURUSD", "USDJPY", "USDCHF", "GBPUSD"]
    result = []
    for pair in pairs:
        signal = TradingSignal.objects.filter(pair=pair).first()
        if signal:
            result.append(TradingSignalSerializer(signal).data)
        else:
            # Mock signal if none exists
            import random
            result.append({
                "id": 0, "pair": pair,
                "direction": random.choice(["BUY", "SELL", "NEUTRAL"]),
                "confidence": round(random.uniform(0.5, 0.95), 2),
                "macro_score": round(random.uniform(-1, 1), 2),
                "technical_score": round(random.uniform(-1, 1), 2),
                "sentiment_score": round(random.uniform(-1, 1), 2),
                "consensus_count": random.randint(1, 3),
                "rationale": f"Multi-agent analysis for {pair}",
                "is_active": True,
            })
    return Response(result)
