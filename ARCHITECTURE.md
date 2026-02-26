# Trady System Architecture

## 🏗️ System Overview

**Trady** is built using a microservices-inspired architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                     DATA ACQUISITION LAYER                   │
├─────────────────────────────────────────────────────────────┤
│  • MT5 (OHLCV) → InfluxDB                                   │
│  • FRED API (Macro) → PostgreSQL                            │
│  • RSS Feeds (News) → PostgreSQL                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     VALIDATION LAYER                         │
├─────────────────────────────────────────────────────────────┤
│  • Time-series integrity checks                              │
│  • Macro data validation & cleaning                          │
│  • News deduplication & embedding                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  FEATURE ENGINEERING LAYER                   │
├─────────────────────────────────────────────────────────────┤
│  • Technical indicators (RSI, MACD, BB, ATR, etc.)          │
│  • Macro features (rate diff, inflation, sentiment)          │
│  • Sentiment features (LLM classification)                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   MULTI-AGENT REASONING                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Technical  │  │    Macro    │  │  Sentiment  │        │
│  │    Agent    │  │    Agent    │  │    Agent    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│         │                 │                │                │
│         └─────────────────┴────────────────┘                │
│                          ↓                                   │
│              ┌────────────────────┐                         │
│              │  Coordinator Agent │                         │
│              │ (Dynamic Weighting)│                         │
│              └────────────────────┘                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      DECISION LAYER                          │
├─────────────────────────────────────────────────────────────┤
│  • BUY / SELL / NEUTRAL signal                              │
│  • Confidence score (0-1)                                    │
│  • Risk level (LOW/MEDIUM/HIGH)                              │
│  • Explainable reasoning                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    BACKTESTING ENGINE                        │
├─────────────────────────────────────────────────────────────┤
│  • Walk-forward validation                                   │
│  • Performance metrics (Sharpe, MDD, Win Rate)              │
│  • Trade-by-trade analysis                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      API & FRONTEND                          │
├─────────────────────────────────────────────────────────────┤
│  • Django REST API                                           │
│  • Next.js Dashboard                                         │
│  • Real-time WebSocket updates                               │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Technology Stack

### Backend
- **Framework**: Django 5.0 + Django REST Framework
- **Databases**: 
  - PostgreSQL (relational data, features, signals)
  - InfluxDB (time-series OHLCV data)
  - Redis (caching, task queue)
- **AI/ML**:
  - LangChain (agent orchestration)
  - HuggingFace Transformers (free LLMs)
  - Sentence Transformers (embeddings)
  - scikit-learn (traditional ML)
  - ta (technical analysis)

### Frontend
- **Framework**: Next.js 14 + TypeScript
- **UI**: TailwindCSS + shadcn/ui
- **Charts**: Recharts / TradingView
- **State**: React Query

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Task Queue**: Celery + Redis
- **Reverse Proxy**: Nginx (production)

## 📦 Module Breakdown

### Core (`backend/core/`)
- `database.py`: Connection managers for PostgreSQL and InfluxDB
- `llm_factory.py`: Factory pattern for LLM instantiation

### Validation (`backend/validation/`)
- `timeseries_validator.py`: Validates OHLCV data integrity
- `macro_validator.py`: Cleans and validates macro data
- `news_preprocessor.py`: Processes and embeds news articles

### Features (`backend/features/`)
- `technical_calculator.py`: Computes technical indicators
- `macro_calculator.py`: Calculates macro differentials
- `sentiment_calculator.py`: LLM-based sentiment analysis

### Agents (`backend/agents/`)
- `base_agent.py`: Abstract base class for all agents
- `technical_agent.py`: Technical analysis specialist
- `macro_agent.py`: Macroeconomic analysis specialist
- `sentiment_agent.py`: News sentiment specialist
- `coordinator.py`: Meta-agent that coordinates all signals

### Backtesting (`backend/backtesting/`)
- `engine.py`: Walk-forward backtesting implementation
- `models.py`: Django models for backtest results

### API (`backend/api/`)
- `views.py`: REST API endpoints
- `serializers.py`: DRF serializers
- `urls.py`: URL routing

### TDSP (`backend/tdsp/`)
- `documentation_generator.py`: Automated TDSP reporting

## 🔄 Data Flow

### 1. Data Ingestion
```python
MT5 → InfluxDB (5min candles)
FRED → PostgreSQL (daily macro)
RSS → PostgreSQL (news articles)
```

### 2. Validation Pipeline
```python
Raw Data → Validators → Quality Metrics → Cleaned Data
```

### 3. Feature Engineering
```python
Cleaned Data → Feature Calculators → Feature Tables
```

### 4. Agent Decision Making
```python
Features → Individual Agents → Agent Signals
Agent Signals → Coordinator → Final Decision
```

### 5. Backtesting
```python
Historical Data + Agent Logic → Backtest Engine → Performance Metrics
```

## 🧠 Agent Architecture

### Individual Agents

Each specialized agent follows this pattern:

```python
class SpecializedAgent(BaseAgent):
    def _fetch_features(symbol, timestamp):
        # Get relevant features
        
    def _make_decision(features):
        # Use LLM + rules to decide
        # Return: signal, confidence, reasoning
```

### Coordinator Agent

The coordinator uses dynamic weighting:

```python
def calculate_weights(regime, performance):
    base_weights = {technical: 0.4, macro: 0.35, sentiment: 0.25}
    
    # Adjust for market regime
    if high_volatility:
        boost technical, reduce macro
    
    # Adjust for recent performance
    for agent in agents:
        if accuracy > threshold:
            increase weight
        else:
            decrease weight
    
    return normalized_weights
```

## 📊 Database Schema

### PostgreSQL Tables

```sql
-- Agent signals
agent_signals (
    id, agent_type, symbol, timestamp,
    signal, confidence, reasoning,
    features_used JSON
)

-- Coordinator decisions
coordinator_decisions (
    id, symbol, timestamp,
    decision, confidence, risk_level,
    technical_signal_id, macro_signal_id, sentiment_signal_id,
    weights JSON, reasoning, volatility_regime
)

-- Agent performance
agent_performance (
    id, agent_type, symbol, date,
    accuracy, precision, recall, sharpe_ratio,
    current_weight
)

-- Validation reports
validation_reports (
    id, report_type, symbol, timestamp,
    is_valid, issues_found, details JSON
)

-- Features
technical_features (symbol, timestamp, rsi_14, macd, bb_position, ...)
macro_features (currency_pair, date, rate_diff, inflation_diff, ...)
sentiment_features (timestamp, currency, sentiment_score, ...)
```

### InfluxDB Measurements

```
measurement: ohlcv
tags: symbol
fields: open, high, low, close, volume
```

## 🔐 Security Considerations

- Environment variables for sensitive credentials
- Token-based authentication for API
- Rate limiting on public endpoints
- Input validation on all API endpoints
- SQL injection prevention via ORM
- CORS configuration for frontend

## 🚀 Deployment

### Development
```bash
docker-compose up -d
python manage.py runserver
npm run dev
```

### Production
```bash
docker-compose -f docker-compose.prod.yml up -d
# Nginx reverse proxy
# SSL with Let's Encrypt
# Celery workers for async tasks
```

## 📈 Performance Optimization

1. **Database indexing** on frequently queried fields
2. **Redis caching** for agent decisions
3. **Bulk inserts** for feature storage
4. **Connection pooling** for databases
5. **Async tasks** via Celery for heavy computations
6. **Query optimization** with select_related/prefetch_related

## 🧪 Testing Strategy

- **Unit tests**: Individual components
- **Integration tests**: Agent pipeline
- **Backtests**: Historical performance validation
- **Load tests**: API performance under stress

## 📚 Further Reading

- [LangChain Documentation](https://python.langchain.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Team Data Science Process](https://docs.microsoft.com/en-us/azure/architecture/data-science-process/overview)

---

**Built by Team DATAMINDS** 🚀
