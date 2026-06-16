"""
Paper Trade Settlement Engine

Periodically checks open PaperPosition records against current prices,
closes positions when SL/TP is hit (or after 72h expiry), and records
per-agent outcomes in AgentOutcome so the PerformanceTracker has real data.

Run every 4h via the APScheduler in scheduling/__init__.py, or manually:
    python manage.py settle_paper_trades
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Positions older than this are force-closed at current market price
MAX_POSITION_AGE_HOURS = 72


def _get_current_price(pair: str) -> Optional[float]:
    """
    Get the latest price for a pair.
    Fallback chain: TimeSeriesLoader → yfinance.
    Returns None if both fail.
    """
    # Attempt 1: DB (InfluxDB → SQLite)
    try:
        from data_layer.timeseries_loader import TimeSeriesLoader
        loader = TimeSeriesLoader()
        df = loader.load_ohlcv(pair)
        if df is not None and not df.empty:
            return float(df['close'].iloc[-1])
    except Exception as exc:
        logger.debug(f"TimeSeriesLoader failed for {pair}: {exc}")

    # Attempt 2: yfinance direct
    try:
        import yfinance as yf
        _TICKER_MAP = {
            'EURUSD': 'EURUSD=X', 'USDJPY': 'USDJPY=X',
            'GBPUSD': 'GBPUSD=X', 'USDCHF': 'USDCHF=X',
        }
        ticker_str = _TICKER_MAP.get(pair, f'{pair}=X')
        hist = yf.Ticker(ticker_str).history(period='1d', interval='1h')
        if hist is not None and not hist.empty:
            return float(hist['Close'].iloc[-1])
    except Exception as exc:
        logger.debug(f"yfinance failed for {pair}: {exc}")

    return None


def _check_sl_tp_hit(pos, current_price: float) -> Optional[str]:
    """
    Check if stop-loss or take-profit has been hit.
    Returns 'SL', 'TP', or None.
    """
    if pos.side == "BUY":
        if pos.stop_loss and current_price <= pos.stop_loss:
            return "SL"
        if pos.take_profit and current_price >= pos.take_profit:
            return "TP"
    elif pos.side == "SELL":
        if pos.stop_loss and current_price >= pos.stop_loss:
            return "SL"
        if pos.take_profit and current_price <= pos.take_profit:
            return "TP"
    return None


def _record_agent_outcomes(pos, trade_won: bool):
    """
    Extract per-agent signals from pipeline_snapshot and write AgentOutcome records.
    """
    from monitoring.performance_tracker import PerformanceTracker

    snapshot = pos.pipeline_snapshot
    if not snapshot or not isinstance(snapshot, dict):
        logger.warning(f"Position #{pos.id} has no pipeline_snapshot — skipping agent outcomes")
        return

    # The XAI breakdown contains per-agent data
    xai = snapshot.get("xai", {})
    agent_breakdown = xai.get("agent_breakdown", {})

    if not agent_breakdown:
        # Try alternative path: some pipeline versions store at top level
        agent_breakdown = snapshot.get("agent_signals", {})

    tracker = PerformanceTracker()

    for agent_name, agent_data in agent_breakdown.items():
        if not isinstance(agent_data, dict):
            continue

        signal_dir = agent_data.get("signal", "NEUTRAL")
        confidence = agent_data.get("confidence", 0.0)
        weight = agent_data.get("weight", 0.0)

        # Determine if this agent's vote was correct:
        # Agent voted in the same direction as the trade AND trade won → correct
        # Agent voted opposite → check if trade lost (then agent was right to disagree)
        trade_side = pos.side  # BUY or SELL
        signal_map = {"BUY": 1, "SELL": -1, "NEUTRAL": 0}
        side_map = {"BUY": 1, "SELL": -1}

        agent_signal_int = signal_map.get(signal_dir, 0)
        trade_side_int = side_map.get(trade_side, 0)

        if agent_signal_int == 0:
            # Neutral agents: correct if trade lost, wrong if trade won
            agent_correct = not trade_won
        elif agent_signal_int == trade_side_int:
            # Agreed with trade direction
            agent_correct = trade_won
        else:
            # Disagreed with trade direction
            agent_correct = not trade_won

        # Attribute P&L proportionally by weight
        agent_pnl = pos.pnl * weight if weight > 0 else 0.0

        tracker.record_agent_outcome(
            agent_name=agent_name,
            pair=pos.pair,
            signal_direction=signal_dir,
            confidence=confidence,
            was_correct=agent_correct,
            pnl=agent_pnl,
            weight_used=weight,
            paper_position=pos,
        )


def settle_open_positions() -> dict:
    """
    Main settlement loop. Check all open positions and close those
    that hit SL/TP or exceeded the max age.

    Returns:
        Summary dict with counts.
    """
    from paper_trading.models import PaperPosition
    from paper_trading.services.portfolio import close_position, update_position

    open_positions = PaperPosition.objects.filter(status="OPEN")
    total = open_positions.count()

    if total == 0:
        logger.info("[Settler] No open positions to settle")
        return {"total": 0, "closed": 0, "updated": 0, "errors": 0}

    logger.info(f"[Settler] Checking {total} open positions")

    closed_count = 0
    updated_count = 0
    error_count = 0
    now = datetime.now()

    for pos in open_positions:
        try:
            current_price = _get_current_price(pos.pair)
            if current_price is None:
                logger.warning(f"[Settler] Cannot get price for {pos.pair} — skipping #{pos.id}")
                error_count += 1
                continue

            # Check SL/TP
            hit = _check_sl_tp_hit(pos, current_price)

            # Check age expiry
            age_hours = (now - pos.opened_at.replace(tzinfo=None)).total_seconds() / 3600
            expired = age_hours > MAX_POSITION_AGE_HOURS

            if hit or expired:
                # Close at the trigger price (SL/TP) or current price (expiry)
                if hit == "SL" and pos.stop_loss:
                    close_price = pos.stop_loss
                elif hit == "TP" and pos.take_profit:
                    close_price = pos.take_profit
                else:
                    close_price = current_price

                close_position(pos.id, close_price)

                # Refresh from DB to get final P&L
                pos.refresh_from_db()
                trade_won = pos.pnl > 0

                reason = f"SL hit" if hit == "SL" else f"TP hit" if hit == "TP" else f"expired ({age_hours:.0f}h)"
                logger.info(
                    f"[Settler] Closed #{pos.id} {pos.side} {pos.pair}: {reason}, "
                    f"PnL={pos.pnl:.2f}, won={trade_won}"
                )

                # Record per-agent outcomes
                _record_agent_outcomes(pos, trade_won)
                closed_count += 1
            else:
                # Just update mark-to-market
                update_position(pos.id, current_price)
                updated_count += 1

        except Exception as exc:
            logger.error(f"[Settler] Error processing position #{pos.id}: {exc}", exc_info=True)
            error_count += 1

    summary = {
        "total": total,
        "closed": closed_count,
        "updated": updated_count,
        "errors": error_count,
    }
    logger.info(f"[Settler] Done: {summary}")
    return summary
