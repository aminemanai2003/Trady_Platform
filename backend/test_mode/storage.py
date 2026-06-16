import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

DATA_DIR = Path(__file__).resolve().parent / "data"
TRADES_FILE = DATA_DIR / "trades.json"
_lock = threading.Lock()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not TRADES_FILE.exists():
        TRADES_FILE.write_text("[]", encoding="utf-8")


def _read_all_unlocked() -> List[Dict]:
    _ensure_storage()
    try:
        raw = TRADES_FILE.read_text(encoding="utf-8").strip()
        if not raw:
            return []
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _write_all_unlocked(trades: List[Dict]) -> None:
    _ensure_storage()
    TRADES_FILE.write_text(json.dumps(trades, indent=2), encoding="utf-8")


def list_trades(session_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict]:
    with _lock:
        trades = _read_all_unlocked()

    if session_id:
        trades = [t for t in trades if t.get("session_id") == session_id]
    if status:
        status = status.upper()
        trades = [t for t in trades if t.get("status") == status]
    trades.sort(key=lambda t: t.get("opened_at", ""), reverse=True)
    return trades


def create_trade(payload: Dict) -> Dict:
    trade = {
        "id": str(uuid.uuid4()),
        "session_id": payload.get("session_id") or "default",
        "symbol": (payload.get("symbol") or "").upper(),
        "side": (payload.get("side") or "").upper(),
        "timeframe": (payload.get("timeframe") or "1H").upper(),
        "size": float(payload.get("size") or 0.0),
        "entry_price": float(payload.get("entry_price") or 0.0),
        "opened_at": _utc_now_iso(),
        "status": "OPEN",
        "closed_at": None,
        "close_price": None,
        "pnl": None,
        "pnl_pct": None,
        "note": (payload.get("note") or "").strip(),
        "agent_snapshot": payload.get("agent_snapshot") or {},
    }

    with _lock:
        trades = _read_all_unlocked()
        trades.append(trade)
        _write_all_unlocked(trades)

    return trade


def _compute_pnl(side: str, entry_price: float, close_price: float, size: float) -> Dict:
    direction = 1.0 if side == "BUY" else -1.0
    delta = (close_price - entry_price) * direction
    pnl = delta * size
    pnl_pct = (delta / entry_price * 100.0) if entry_price > 0 else 0.0
    return {"pnl": pnl, "pnl_pct": pnl_pct}


def close_trade(trade_id: str, close_price: float) -> Dict:
    with _lock:
        trades = _read_all_unlocked()
        idx = next((i for i, t in enumerate(trades) if t.get("id") == trade_id), -1)
        if idx < 0:
            raise KeyError("trade_not_found")

        trade = trades[idx]
        if trade.get("status") == "CLOSED":
            return trade

        entry_price = float(trade.get("entry_price") or 0.0)
        size = float(trade.get("size") or 0.0)
        side = (trade.get("side") or "BUY").upper()
        metrics = _compute_pnl(side, entry_price, close_price, size)

        trade["status"] = "CLOSED"
        trade["closed_at"] = _utc_now_iso()
        trade["close_price"] = float(close_price)
        trade["pnl"] = round(metrics["pnl"], 8)
        trade["pnl_pct"] = round(metrics["pnl_pct"], 6)

        trades[idx] = trade
        _write_all_unlocked(trades)

    return trade


def summary(session_id: Optional[str] = None) -> Dict:
    trades = list_trades(session_id=session_id)
    open_trades = [t for t in trades if t.get("status") == "OPEN"]
    closed_trades = [t for t in trades if t.get("status") == "CLOSED"]
    wins = [t for t in closed_trades if (t.get("pnl") or 0.0) > 0]
    losses = [t for t in closed_trades if (t.get("pnl") or 0.0) < 0]

    total_pnl = float(sum(float(t.get("pnl") or 0.0) for t in closed_trades))
    avg_pnl_pct = float(sum(float(t.get("pnl_pct") or 0.0) for t in closed_trades) / len(closed_trades)) if closed_trades else 0.0

    return {
        "total_trades": len(trades),
        "open_trades": len(open_trades),
        "closed_trades": len(closed_trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round((len(wins) / len(closed_trades) * 100.0), 2) if closed_trades else 0.0,
        "total_pnl": round(total_pnl, 8),
        "avg_pnl_pct": round(avg_pnl_pct, 6),
    }


def reset_session(session_id: str) -> Dict:
    target = (session_id or "").strip() or "default"
    with _lock:
        trades = _read_all_unlocked()
        kept = [t for t in trades if t.get("session_id") != target]
        deleted_count = len(trades) - len(kept)
        _write_all_unlocked(kept)
    return {
        "session_id": target,
        "deleted_trades": deleted_count,
    }

