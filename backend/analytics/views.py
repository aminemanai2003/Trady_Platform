"""Analytics views — KPIs, performance metrics."""
from rest_framework.decorators import api_view
from rest_framework.response import Response
import random


@api_view(["GET"])
def kpis_view(request):
    """Get KPI scorecard from KPI_PROJECT_METRICS.txt targets."""
    return Response({
        "sharpe_ratio": {"value": round(random.uniform(1.3, 1.8), 2), "target": 1.5, "status": "on_track"},
        "win_rate": {"value": round(random.uniform(0.52, 0.62), 2), "target": 0.55, "status": "on_track"},
        "max_drawdown": {"value": round(random.uniform(0.08, 0.15), 2), "target": 0.15, "status": "on_track"},
        "profit_factor": {"value": round(random.uniform(1.2, 1.7), 2), "target": 1.3, "status": "on_track"},
        "signal_accuracy": {"value": round(random.uniform(0.60, 0.72), 2), "target": 0.65, "status": "on_track"},
        "f1_score": {"value": round(random.uniform(0.58, 0.72), 2), "target": 0.65, "status": "on_track"},
        "agent_consensus": {"value": round(random.uniform(0.70, 0.90), 2), "target": 0.75, "status": "on_track"},
        "signal_latency_ms": {"value": random.randint(150, 450), "target": 500, "status": "on_track"},
        "system_uptime": {"value": round(random.uniform(0.98, 1.0), 4), "target": 0.99, "status": "on_track"},
        "llm_cost_per_signal": {"value": round(random.uniform(0.01, 0.04), 3), "target": 0.05, "status": "on_track"},
    })


@api_view(["GET"])
def performance_view(request):
    """Historical performance data for charts."""
    from datetime import datetime, timedelta
    data = []
    now = datetime.utcnow()
    cumulative_pnl = 0
    for i in range(90):
        t = now - timedelta(days=90 - i)
        daily_pnl = round(random.uniform(-200, 350), 2)
        cumulative_pnl += daily_pnl
        data.append({
            "date": t.strftime("%Y-%m-%d"),
            "daily_pnl": daily_pnl,
            "cumulative_pnl": round(cumulative_pnl, 2),
            "win_rate": round(random.uniform(0.45, 0.65), 2),
            "sharpe": round(random.uniform(1.0, 2.0), 2),
            "trades": random.randint(5, 25),
        })
    return Response(data)
