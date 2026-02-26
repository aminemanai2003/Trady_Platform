"""Feature engineering — Technical indicators for the Technical Agent."""
import math
from typing import List, Dict


def calculate_rsi(closes: List[float], period: int = 14) -> List[float]:
    """Relative Strength Index."""
    if len(closes) < period + 1:
        return [50.0] * len(closes)

    rsi_values = [50.0] * period
    gains, losses = [], []

    for i in range(1, period + 1):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    for i in range(period, len(closes)):
        change = closes[i] - closes[i - 1]
        gain = max(change, 0)
        loss = max(-change, 0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(round(100 - (100 / (1 + rs)), 2))

    return rsi_values


def calculate_macd(
    closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> Dict[str, List[float]]:
    """MACD: line, signal, histogram."""
    def ema(data, period):
        result = [data[0]]
        multiplier = 2 / (period + 1)
        for i in range(1, len(data)):
            result.append(data[i] * multiplier + result[-1] * (1 - multiplier))
        return result

    if len(closes) < slow:
        n = len(closes)
        return {"macd": [0.0] * n, "signal": [0.0] * n, "histogram": [0.0] * n}

    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line = [round(f - s, 6) for f, s in zip(ema_fast, ema_slow)]
    signal_line = ema(macd_line, signal)
    histogram = [round(m - s, 6) for m, s in zip(macd_line, signal_line)]

    return {
        "macd": [round(v, 6) for v in macd_line],
        "signal": [round(v, 6) for v in signal_line],
        "histogram": histogram,
    }


def calculate_bollinger(
    closes: List[float], period: int = 20, std_dev: float = 2.0
) -> Dict[str, List[float]]:
    """Bollinger Bands: upper, middle (SMA), lower."""
    upper, middle, lower = [], [], []

    for i in range(len(closes)):
        if i < period - 1:
            upper.append(closes[i])
            middle.append(closes[i])
            lower.append(closes[i])
        else:
            window = closes[i - period + 1 : i + 1]
            sma = sum(window) / period
            variance = sum((x - sma) ** 2 for x in window) / period
            std = math.sqrt(variance)
            middle.append(round(sma, 6))
            upper.append(round(sma + std_dev * std, 6))
            lower.append(round(sma - std_dev * std, 6))

    return {"upper": upper, "middle": middle, "lower": lower}


def calculate_sma(closes: List[float], period: int) -> List[float]:
    """Simple Moving Average."""
    result = []
    for i in range(len(closes)):
        if i < period - 1:
            result.append(closes[i])
        else:
            result.append(round(sum(closes[i - period + 1 : i + 1]) / period, 6))
    return result


def calculate_atr(
    highs: List[float], lows: List[float], closes: List[float], period: int = 14
) -> List[float]:
    """Average True Range."""
    if len(closes) < 2:
        return [0.0] * len(closes)

    tr = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        tr.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        ))

    atr = [tr[0]]
    for i in range(1, len(tr)):
        if i < period:
            atr.append(round(sum(tr[: i + 1]) / (i + 1), 6))
        else:
            atr.append(round((atr[-1] * (period - 1) + tr[i]) / period, 6))
    return atr


def generate_technical_analysis(
    prices: List[Dict],
) -> Dict:
    """Run full technical analysis on OHLCV data and return indicators + signal."""
    if not prices:
        return {"signal": "NEUTRAL", "confidence": 0.5, "indicators": {}}

    closes = [p["close"] for p in prices]
    highs = [p["high"] for p in prices]
    lows = [p["low"] for p in prices]

    rsi = calculate_rsi(closes)
    macd = calculate_macd(closes)
    bb = calculate_bollinger(closes)
    sma_50 = calculate_sma(closes, 50)
    sma_200 = calculate_sma(closes, 200)
    atr = calculate_atr(highs, lows, closes)

    # Latest values
    latest_rsi = rsi[-1]
    latest_macd = macd["histogram"][-1]
    latest_close = closes[-1]
    latest_bb_upper = bb["upper"][-1]
    latest_bb_lower = bb["lower"][-1]
    latest_sma_50 = sma_50[-1]
    latest_sma_200 = sma_200[-1]

    # Score-based signal generation
    score = 0
    reasons = []

    # RSI
    if latest_rsi < 30:
        score += 2
        reasons.append(f"RSI oversold ({latest_rsi:.1f})")
    elif latest_rsi > 70:
        score -= 2
        reasons.append(f"RSI overbought ({latest_rsi:.1f})")
    elif latest_rsi < 45:
        score += 1
        reasons.append(f"RSI low ({latest_rsi:.1f})")
    elif latest_rsi > 55:
        score -= 1
        reasons.append(f"RSI high ({latest_rsi:.1f})")

    # MACD
    if latest_macd > 0:
        score += 1
        reasons.append("MACD bullish")
    else:
        score -= 1
        reasons.append("MACD bearish")

    # Bollinger
    if latest_close < latest_bb_lower:
        score += 1
        reasons.append("Price below lower Bollinger")
    elif latest_close > latest_bb_upper:
        score -= 1
        reasons.append("Price above upper Bollinger")

    # SMA cross
    if latest_sma_50 > latest_sma_200:
        score += 1
        reasons.append("Golden cross (SMA50 > SMA200)")
    else:
        score -= 1
        reasons.append("Death cross (SMA50 < SMA200)")

    # Determine signal
    if score >= 2:
        signal = "BUY"
    elif score <= -2:
        signal = "SELL"
    else:
        signal = "NEUTRAL"

    confidence = min(0.95, max(0.3, 0.5 + abs(score) * 0.1))

    return {
        "signal": signal,
        "confidence": round(confidence, 2),
        "score": score,
        "reasoning": " | ".join(reasons),
        "indicators": {
            "rsi": latest_rsi,
            "macd": latest_macd,
            "macd_signal": macd["signal"][-1],
            "bb_upper": latest_bb_upper,
            "bb_lower": latest_bb_lower,
            "bb_middle": bb["middle"][-1],
            "sma_50": latest_sma_50,
            "sma_200": latest_sma_200,
            "atr": atr[-1],
            "close": latest_close,
        },
    }
