"""
Paper Trading Portfolio Service
Manages simulated positions: open, update, close, and statistics.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


def open_position(
    pair: str,
    side: str,
    size: float,
    entry_price: float,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
    pipeline_snapshot: Optional[Dict] = None,
):
    """
    Open a new paper position.

    Args:
        pair:              e.g. 'EURUSD'
        side:              'BUY' or 'SELL'
        size:              lot size (e.g. 0.1)
        entry_price:       entry price
        stop_loss:         optional SL price
        take_profit:       optional TP price
        pipeline_snapshot: full pipeline result dict stored for audit trail
    """
    from paper_trading.models import PaperPosition

    pos = PaperPosition.objects.create(
        pair=pair.upper(),
        side=side.upper(),
        size=size,
        entry_price=entry_price,
        current_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        pnl=0.0,
        pnl_pct=0.0,
        pipeline_snapshot=pipeline_snapshot,
    )
    logger.info(f"PaperPosition opened: #{pos.id} {pos.side} {pos.pair} @ {entry_price}")
    return pos


def update_position(position_id: int, current_price: float) -> Optional[Dict]:
    """Update a position's current price and unrealised P&L."""
    from paper_trading.models import PaperPosition

    try:
        pos = PaperPosition.objects.get(id=position_id, status="OPEN")
        pos.current_price = current_price
        pos.pnl = pos.calculate_pnl()
        if pos.entry_price > 0:
            pos.pnl_pct = round((pos.pnl / (pos.entry_price * pos.size * 100000)) * 100, 4)
        pos.save(update_fields=["current_price", "pnl", "pnl_pct"])
        return _serialize_position(pos)
    except PaperPosition.DoesNotExist:
        return None


def close_position(position_id: int, close_price: Optional[float] = None) -> Optional[Dict]:
    """Close an open paper position."""
    from paper_trading.models import PaperPosition

    try:
        pos = PaperPosition.objects.get(id=position_id, status="OPEN")
        if close_price:
            pos.current_price = close_price
        pos.pnl = pos.calculate_pnl()
        if pos.entry_price > 0:
            pos.pnl_pct = round((pos.pnl / (pos.entry_price * pos.size * 100000)) * 100, 4)
        pos.status = "CLOSED"
        pos.closed_at = datetime.now()
        pos.save()
        logger.info(f"PaperPosition closed: #{pos.id} PnL={pos.pnl}")
        return _serialize_position(pos)
    except PaperPosition.DoesNotExist:
        return None


def get_open_positions() -> List[Dict]:
    """Return all currently open positions."""
    from paper_trading.models import PaperPosition

    positions = PaperPosition.objects.filter(status="OPEN").order_by("-opened_at")
    return [_serialize_position(p) for p in positions]


def get_trade_history(limit: int = 100) -> List[Dict]:
    """Return closed position history."""
    from paper_trading.models import PaperPosition

    positions = PaperPosition.objects.filter(status="CLOSED").order_by("-closed_at")[:limit]
    return [_serialize_position(p) for p in positions]


def get_portfolio_stats() -> Dict:
    """
    Compute portfolio-level performance statistics.

    Returns:
        total_pnl, total_trades, win_rate, max_drawdown, open_positions, total_exposure
    """
    from paper_trading.models import PaperPosition

    closed = list(PaperPosition.objects.filter(status="CLOSED").values("pnl"))
    open_pos = list(PaperPosition.objects.filter(status="OPEN").values("current_price", "entry_price", "size"))

    total_trades = len(closed)
    wins = sum(1 for t in closed if t["pnl"] > 0)
    win_rate = (wins / total_trades) if total_trades > 0 else 0.0
    total_pnl = sum(t["pnl"] for t in closed)

    # Max drawdown (simplified peak-to-trough on cumulative PnL)
    max_drawdown = 0.0
    if closed:
        cumulative = 0.0
        peak = 0.0
        for t in closed:
            cumulative += t["pnl"]
            if cumulative > peak:
                peak = cumulative
            dd = (peak - cumulative) / (abs(peak) + 1e-9)
            if dd > max_drawdown:
                max_drawdown = dd

    # Sharpe ratio (simplified — annualised, assuming daily trades)
    import math
    pnls = [t["pnl"] for t in closed]
    if len(pnls) >= 2:
        import statistics
        mean_pnl = statistics.mean(pnls)
        std_pnl = statistics.stdev(pnls)
        sharpe = (mean_pnl / (std_pnl + 1e-9)) * math.sqrt(252)
    else:
        sharpe = 0.0

    total_exposure = sum(p["current_price"] * p["size"] for p in open_pos)

    return {
        "total_pnl": round(total_pnl, 2),
        "total_trades": total_trades,
        "win_rate": round(win_rate, 4),
        "sharpe_ratio": round(sharpe, 4),
        "max_drawdown": round(max_drawdown, 4),
        "open_positions": len(open_pos),
        "total_exposure": round(total_exposure, 2),
    }


def _serialize_position(pos) -> Dict:
    return {
        "id": pos.id,
        "pair": pos.pair,
        "side": pos.side,
        "size": pos.size,
        "entry_price": pos.entry_price,
        "current_price": pos.current_price,
        "stop_loss": pos.stop_loss,
        "take_profit": pos.take_profit,
        "pnl": pos.pnl,
        "pnl_pct": pos.pnl_pct,
        "status": pos.status,
        "opened_at": pos.opened_at.isoformat() if pos.opened_at else None,
        "closed_at": pos.closed_at.isoformat() if pos.closed_at else None,
    }
