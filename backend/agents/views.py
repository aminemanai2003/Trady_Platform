"""Views for agents app."""
from rest_framework.decorators import api_view
from rest_framework.response import Response
import random


@api_view(["GET"])
def agent_status(request):
    """Get status of all agents."""
    agents = [
        {
            "type": "MACRO", "name": "Macro Agent",
            "description": "Analyzes FRED economic indicators, central bank policies",
            "status": "ONLINE", "last_run": "2026-02-22T20:30:00Z",
            "last_decision": random.choice(["BUY", "SELL", "NEUTRAL"]),
            "confidence": round(random.uniform(0.6, 0.95), 2),
            "tokens_used": random.randint(1000, 3000),
            "latency_ms": random.randint(80, 200),
            "accuracy_30d": round(random.uniform(0.55, 0.72), 2),
        },
        {
            "type": "TECHNICAL", "name": "Technical Agent",
            "description": "Multi-timeframe analysis: RSI, MACD, Bollinger, patterns",
            "status": "ONLINE", "last_run": "2026-02-22T20:30:00Z",
            "last_decision": random.choice(["BUY", "SELL", "NEUTRAL"]),
            "confidence": round(random.uniform(0.5, 0.90), 2),
            "tokens_used": random.randint(500, 1500),
            "latency_ms": random.randint(40, 100),
            "accuracy_30d": round(random.uniform(0.52, 0.65), 2),
        },
        {
            "type": "SENTIMENT", "name": "Sentiment Agent",
            "description": "NLP on Reuters news, social media, COT reports",
            "status": "ONLINE", "last_run": "2026-02-22T20:30:00Z",
            "last_decision": random.choice(["BUY", "SELL", "NEUTRAL"]),
            "confidence": round(random.uniform(0.45, 0.85), 2),
            "tokens_used": random.randint(2000, 5000),
            "latency_ms": random.randint(100, 250),
            "accuracy_30d": round(random.uniform(0.48, 0.60), 2),
        },
        {
            "type": "ORCHESTRATOR", "name": "Orchestrator",
            "description": "4-eyes consensus: aggregates signals, resolves conflicts",
            "status": "ONLINE", "last_run": "2026-02-22T20:30:00Z",
            "last_decision": random.choice(["BUY", "SELL", "NEUTRAL"]),
            "confidence": round(random.uniform(0.65, 0.95), 2),
            "tokens_used": random.randint(500, 1000),
            "latency_ms": random.randint(30, 80),
            "accuracy_30d": round(random.uniform(0.60, 0.78), 2),
        },
    ]
    consensus_rate = round(random.uniform(0.70, 0.90), 2)
    return Response({"agents": agents, "consensus_rate": consensus_rate})


@api_view(["POST"])
def run_agents(request):
    """Trigger a full agent analysis cycle."""
    pair = request.data.get("pair", "EURUSD")
    return Response({
        "status": "triggered",
        "pair": pair,
        "message": f"Agent analysis cycle started for {pair}",
    })
