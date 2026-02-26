# V2 Architecture - Production-Grade FX Trading System

## 🎯 Architecture Overview

Complete redesign separating **deterministic logic** from **LLM usage**.

### Key Principles

1. **LLM NEVER used for**:
   - Indicator calculations
   - Signal threshold decisions
   - Weighted aggregation
   - Trading logic

2. **LLM ONLY used for**:
   - Sentiment classification
   - Natural language explanations
   - Text summarization

3. **Everything else is deterministic Python**

## 📁 Layer Architecture

```
backend/
├── data_layer/              # Pure data retrieval
│   ├── timeseries_loader.py    # OHLCV from InfluxDB
│   ├── macro_loader.py          # Economic data from PostgreSQL
│   └── news_loader.py           # News articles
│
├── feature_layer/           # Pure mathematical calculations
│   ├── technical_features.py   # RSI, MACD, BB, etc.
│   ├── macro_features.py        # Rate differentials, momentum
│   └── sentiment_features.py    # LLM classification + deterministic aggregation
│
├── signal_layer/            # Deterministic signal generation
│   ├── technical_agent_v2.py   # Threshold-based logic
│   ├── macro_agent_v2.py        # Economic rules
│   ├── sentiment_agent_v2.py   # Weighted sentiment
│   └── coordinator_agent_v2.py # Meta-agent with dynamic weights
│
├── monitoring/              # Performance tracking & safety
│   ├── performance_tracker.py  # Per-agent Sharpe, win rate
│   ├── drift_detector.py       # Distribution shift detection
│   └── safety_monitor.py       # Cooldown, limits, circuit breaker
│
└── api/                     # REST endpoints
    ├── views_v2.py
    └── urls_v2.py
```

## 🔬 Technical Agent V2

**100% Deterministic** - No LLM

```python
Rules:
1. RSI < 30 → BUY signal (weight: 0.25)
2. RSI > 70 → SELL signal (weight: 0.25)
3. MACD crossover → Direction signal (weight: 0.30)
4. Bollinger Band position (weight: 0.20)
5. SMA trend alignment (weight: 0.25)

Weighted vote → Final signal (-1/0/1)
```

## 📊 Macro Agent V2

**100% Deterministic** - No LLM

```python
Calculations:
- Rate differential = base_rate - quote_rate
- Inflation differential
- Rate momentum (90-day change)
- Carry score = rate_diff / volatility

Thresholds:
- rate_diff > 0.5% → Bullish
- rate_diff < -0.5% → Bearish
- Combine with momentum for confidence
```

## 💬 Sentiment Agent V2

**LLM for classification ONLY** - Aggregation is deterministic

```python
LLM Step (with retry logic):
- Input: News article
- Output: {"sentiment": -1 to 1, "relevance": 0 to 1}
- Validation: Strict JSON schema
- Retry if invalid (max 3 attempts)

Deterministic Aggregation:
- Time decay: exp(-hours / 24)
- Weight = relevance * time_decay
- Weighted average sentiment
- Threshold: >0.3 = BUY, <-0.3 = SELL
```

## 🎯 Coordinator Agent V2

**Meta-agent with dynamic weights**

```python
Process:
1. Collect all agent signals (deterministic)
2. Update weights based on 30-day performance:
   - Calculate Sharpe ratio per agent
   - Normalize to weights
   - Smooth transition (80% old, 20% new)
3. Detect market regime:
   - Trending: Boost technical weight
   - Ranging: Boost macro weight
   - Volatile: Reduce all weights
4. Weighted vote (PURE MATH)
5. Apply safety rules:
   - Conflicts → reduce confidence
   - Volatile → reduce confidence
   - Min confidence threshold
6. Generate explanation (LLM optional)
```

## 📈 Performance Monitoring

### Per-Agent Metrics (30-day rolling)

```python
Tracked:
- Sharpe Ratio (annualized)
- Win Rate
- Average PnL
- Max Drawdown
- Trade Count

Auto-disable if:
- Sharpe < -0.5
- Drawdown > 20%
```

### Drift Detection

```python
Monitors:
- Sentiment distribution (KS test)
- Volatility regime changes
- Volume pattern shifts

Alert if significant drift detected (p < 0.05)
```

## 🛡️ Safety Rules

### 1. Signal Cooldown
- Minimum 60 minutes between signals
- Prevents overtrading

### 2. Daily Trade Limit
- Max 10 trades per day per symbol
- Prevents excessive activity

### 3. Circuit Breaker
- Auto-stop if drawdown > 15%
- Requires manual reset

### 4. Conflict Detection
- Reduce confidence if agents disagree
- Signal: BUY + SELL → reduced confidence

## 🔌 API Endpoints

### Generate Signal
```
POST /api/v2/signals/generate_signal/
Body: {
    "symbol": "EURUSD",
    "base_currency": "EUR",
    "quote_currency": "USD"
}

Response: {
    "signal": 1,  # -1/0/1
    "confidence": 0.75,
    "agent_breakdown": {...},
    "weights_used": {...},
    "market_regime": "trending",
    "conflicts_detected": false,
    "explanation": "...",
    "safety_checks": {...}
}
```

### Performance Monitoring
```
GET /api/v2/monitoring/agent_performance/?days=30
GET /api/v2/monitoring/drift_detection/
GET /api/v2/monitoring/safety_status/
GET /api/v2/monitoring/health_check/
```

## 🚀 Key Improvements Over V1

1. **Reliability**: Deterministic logic = reproducible results
2. **Transparency**: Every decision has clear explanation
3. **Performance tracking**: Auto-disable poor performers
4. **Safety**: Multiple layers (cooldown, limits, circuit breaker)
5. **Drift detection**: Adapt to changing market conditions
6. **LLM control**: Strict JSON validation with retry logic

## 📊 Testing

```bash
# Run performance tests
python manage.py test monitoring.tests

# Check system health
curl http://localhost:8000/api/v2/monitoring/health_check/

# Generate test signal
curl -X POST http://localhost:8000/api/v2/signals/generate_signal/ \
  -H "Content-Type: application/json" \
  -d '{"symbol": "EURUSD", "base_currency": "EUR", "quote_currency": "USD"}'
```

## 🔒 Production Checklist

- [x] Deterministic logic for all decisions
- [x] LLM with retry + validation
- [x] Performance tracking per agent
- [x] Drift detection
- [x] Safety monitors (cooldown, limits, circuit breaker)
- [x] Conflict detection
- [x] Structured logging
- [x] API with full explainability

## 📝 Next Steps

1. Deploy database schema (`monitoring/schema.sql`)
2. Populate test data
3. Run integration tests
4. Monitor performance for 30 days
5. Tune thresholds based on results
