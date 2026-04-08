# FX Alpha Platform — AI-Powered Multi-Agent Forex Trading

<div align="center">

![FX Alpha](https://img.shields.io/badge/FX%20Alpha-V2%20Production-blue)
![Python](https://img.shields.io/badge/python-3.13-blue.svg)
![Django](https://img.shields.io/badge/django-6.0-green.svg)
![Next.js](https://img.shields.io/badge/next.js-16-black.svg)
![HuggingFace](https://img.shields.io/badge/HuggingFace-flan--t5--base-yellow.svg)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Production multi-agent system for FX signal generation — Deterministic decisions + LLM explainability**

[Architecture](#architecture) • [Features](#features) • [Installation](#installation) • [API](#api-endpoints) • [Team](#team-dataminds)

</div>

---

## Overview

**FX Alpha Platform** is a production-grade forex trading intelligence system developed by **Team DATAMINDS**. It uses a layered architecture following the **TDSP (Team Data Science Process)** methodology with three specialized AI agents orchestrated by a meta-coordinator.

### Website Experience

The current frontend website is fully in English and includes:

- An animated landing page (`/`) with ReactBits LightPillar and SplashCursor effects
- **Secure authentication** with 2FA support (Face Recognition, Email OTP, SMS OTP)
- Authentication pages (`/login`, `/register`) with KYC verification
- Dashboard modules for trading, analytics, monitoring, reports, agents, and settings

The UI is designed to reflect the DATAMINDS product identity while consuming live backend APIs.

### Security Features

- **Two-Factor Authentication (2FA)** with multiple methods:
  - **Face Recognition** (DeepFace + ArcFace, 512-d embeddings, Fernet encryption)
  - **Email OTP** (6-digit codes via Gmail SMTP)
  - **SMS OTP** (via Twilio)
- **KYC Verification** with OCR extraction (Tesseract + Google Gemini)
- **Token-based authentication** (Django REST Framework authtoken)
- **Rate limiting** on sensitive endpoints (5 attempts/10min for 2FA)

📄 **See [DATABASE_2FA_FINAL_REPORT.md](DATABASE_2FA_FINAL_REPORT.md)** for complete 2FA architecture details.

### Key Principles

- **Deterministic decisions** — All trading signals use rule-based logic (fast, reproducible, auditable)
- **LLM for explainability only** — `google/flan-t5-base` generates human-readable explanations, never trading decisions
- **Multi-source data fusion** — MT5 OHLCV, FRED macroeconomic data, financial news sentiment
- **Production monitoring** — Drift detection, safety rules, performance tracking

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js 16 · React 19)                 │
│           TanStack Query · shadcn/ui · Recharts · Tailwind           │
│                          Port: 3000                                   │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ REST API (CORS)
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    BACKEND (Django 6 + DRF)                           │
│                        Port: 8000                                     │
│                                                                       │
│   API Layer ──► Signal Layer (V2 Agents)                              │
│                   CoordinatorAgentV2 (weighted voting)                 │
│                     ├── TechnicalAgentV2    (40%)                     │
│                     ├── MacroAgentV2        (35%)                     │
│                     └── SentimentAgentV2    (25%)                     │
│                                                                       │
│   Feature Layer ──► 85+ features (60 technical + 25 temporal)         │
│                     Cross-pair correlations · Multi-timeframe          │
│                                                                       │
│   Data Layer ──► TimeSeriesLoader (InfluxDB)                          │
│                  MacroDataLoader  (PostgreSQL)                         │
│                  NewsLoader       (PostgreSQL + HuggingFace)           │
│                                                                       │
│   Monitoring ──► PerformanceTracker · DriftDetector · SafetyMonitor   │
│                                                                       │
│   Backtesting ──► Walk-forward · Kelly Criterion · ATR Position Sizing│
└────────┬─────────────────┬──────────────────┬────────────────────────┘
         │                 │                  │
    InfluxDB 2.7      PostgreSQL 15       Redis 7
     (OHLCV)       (Macro + News + Signals)  (Cache)
```

### Directory Structure

```
fx-alpha-platform/
├── backend/
│   ├── config/                 # Django settings, CORS, DB config
│   ├── core/                   # DatabaseManager, LLMFactory
│   ├── data_layer/             # TimeSeriesLoader, MacroDataLoader, NewsLoader
│   ├── feature_layer/          # TechnicalFeatureEngine, MacroFeatureEngine
│   │   ├── technical_features.py   # 60+ technical indicators
│   │   └── cross_pair_correlations.py  # Cross-pair correlation engine
│   ├── signal_layer/           # V2 Agents (deterministic)
│   │   ├── coordinator_agent_v2.py     # Meta-agent + correlation validation
│   │   ├── technical_agent_v2.py       # RSI, MACD, Bollinger, ADX rules
│   │   ├── macro_agent_v2.py           # Rate diff, inflation, carry trade
│   │   └── sentiment_agent_v2.py       # NLP scores + LLM classification
│   ├── backtesting/            # Walk-forward engine + Kelly Criterion
│   ├── monitoring/             # Drift, safety, performance tracking
│   ├── api/                    # V2 REST endpoints (DRF ViewSets)
│   ├── agents/                 # Legacy agent status endpoints
│   ├── analytics/              # KPIs & performance (real PostgreSQL queries)
│   ├── data/                   # Calendar, technical indicator endpoints
│   └── signals/                # Legacy signal endpoints
├── frontend/
│   └── src/
│       ├── app/(dashboard)/    # Pages: trading, agents, analytics, reports
│       ├── components/ui/      # shadcn/ui components
│       ├── lib/api.ts          # API client (V2 endpoints)
│       └── types/              # TypeScript interfaces
├── docker-compose.yml          # PostgreSQL + InfluxDB + Redis
└── ARCHITECTURE.md             # Full 16-section technical documentation
```

---

## Features

### Data Science Objectives (DSOs)

| DSO | Description | Status |
|-----|-------------|--------|
| **DSO1.1** | Multi-source data pipeline (MT5, FRED, News) | ✅ |
| **DSO1.2** | Multi-timeframe analysis (1H, 4H, D1, W1, M1) | ✅ |
| **DSO1.3** | Cross-pair correlation validation | ✅ |
| **DSO2.1** | 85+ feature engineering (technical + temporal) | ✅ |
| **DSO2.2** | Walk-forward backtesting (no look-ahead bias) | ✅ |
| **DSO2.3** | Kelly Criterion + ATR position sizing | ✅ |
| **DSO3.1** | Multi-agent voting with dynamic weights | ✅ |
| **DSO3.2** | LLM explainability (flan-t5-base) | ✅ |
| **DSO4.1** | Data quality validation (>90% threshold) | ✅ |
| **DSO4.2** | Drift detection & safety monitoring | ✅ |
| **DSO5.1** | Full TDSP documentation & reporting | ✅ |

### Technical Features (85+)

- **Trend**: SMA (10/20/50/200), EMA (9/12/21/26/55), MACD, ADX, Ichimoku, Parabolic SAR
- **Momentum**: RSI, Stochastic, Williams %R, CCI, MFI, ROC
- **Volatility**: Bollinger Bands, ATR, Keltner Channel, Donchian Channel, Historical Vol
- **Volume**: OBV, VWAP, Accumulation/Distribution
- **Temporal**: Session flags (Asian/European/US/Overlap), cyclical encoding, NFP week, high-volume hours

### Cross-Pair Correlations

- Pearson correlation matrix on log-returns (EURUSD, GBPUSD, USDJPY, USDCHF, EURGBP, EURJPY)
- Fundamental expected values vs calculated (deviation detection)
- Signal confidence adjustment: +15% if aligned, -25% if conflicting

### Multi-Agent System

| Agent | Weight | Method |
|-------|--------|--------|
| **TechnicalAgentV2** | 40% | RSI/MACD/Bollinger/ADX rules → BUY/SELL/NEUTRAL |
| **MacroAgentV2** | 35% | Rate differentials, carry trade, inflation analysis |
| **SentimentAgentV2** | 25% | Pre-computed DB scores (fast) + LLM fallback |
| **CoordinatorAgentV2** | — | Weighted voting, regime detection, correlation validation |

---

## Installation

### Prerequisites

- Python 3.13+
- Docker & Docker Compose (for PostgreSQL, InfluxDB, Redis)
- Node.js 18+ (for frontend)

### 1. Infrastructure

```bash
cd fx-alpha-platform
docker-compose up -d  # PostgreSQL 15 + InfluxDB 2.7 + Redis 7
```

### 2. Backend

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev    # http://localhost:3000
```

---

## API Endpoints

### V2 Signal Pipeline

```bash
# Generate trading signal (full pipeline)
POST /api/v2/signals/generate_signal/
Body: {"pair": "EURUSD"}

# Health check + agent performances
GET  /api/v2/monitoring/health_check/

# Drift detection
GET  /api/v2/monitoring/drift_detection/

# Explainability
POST /api/v2/explain/explain_signal/
Body: {"pair": "EURUSD"}
```

### Backtesting & Correlations

```bash
# Run walk-forward backtest
POST /api/v2/backtesting/run_backtest/
Body: {"pair": "EURUSD", "days": 60}

# Kelly Criterion position sizing
POST /api/v2/backtesting/position_sizing/
Body: {"pair": "EURUSD"}

# Cross-pair correlation matrix
GET  /api/v2/correlations/correlation_matrix/

# Single pair correlation analysis
GET  /api/v2/correlations/pair_analysis/?symbol=EURUSD

# Data quality validation
GET  /api/v2/validation/validate_data/?symbol=EURUSD
```

### Legacy Endpoints

```bash
GET  /api/kpis/                     # KPI dashboard (real PostgreSQL queries)
GET  /api/analytics/performance/    # Performance history
GET  /api/agents/status/            # Agent status + metrics
POST /api/agents/run/               # Run agents (real V2 pipeline)
GET  /api/data/economic-calendar/   # Economic calendar (27 events, 5 currencies)
GET  /api/data/technical-indicators/ # Technical indicators (real feature engine)
```

### Example Response — Signal Generation

```json
{
  "success": true,
  "signal": {
    "direction": "NEUTRAL",
    "confidence": 0.44,
    "weighted_score": 0.0,
    "reasoning": "Final Decision: NEUTRAL\n\nAgent Breakdown:\n- TechnicalV2: BUY (55%, w=40%)\n- MacroV2: NEUTRAL (80%, w=35%)\n- SentimentV2: NEUTRAL (54%, w=25%)",
    "agent_votes": {
      "technical": {"signal": "BUY", "confidence": 0.55},
      "macro": {"signal": "NEUTRAL", "confidence": 0.80},
      "sentiment": {"signal": "NEUTRAL", "confidence": 0.54}
    },
    "market_regime": "volatile"
  }
}
```

---

## Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Backend | Django + DRF | 6.0 |
| Frontend | Next.js + React | 16 / 19 |
| Time Series DB | InfluxDB | 2.7 |
| Relational DB | PostgreSQL | 15 |
| Cache | Redis | 7-alpine |
| NLP/LLM | HuggingFace transformers | 4.57.6 |
| LLM Model | google/flan-t5-base | — |
| Embeddings | all-MiniLM-L6-v2 | — |
| Technical Analysis | ta library | 0.11.0 |
| UI Components | shadcn/ui + Tailwind CSS | — |
| Charts | Recharts | — |

---

## Performance

| Metric | Value |
|--------|-------|
| Signal Generation (cold) | ~6.7s |
| Signal Generation (warm) | ~0.4s |
| Technical Features | 85+ indicators |
| Currency Pairs | 6 (EURUSD, GBPUSD, USDJPY, USDCHF, EURGBP, EURJPY) |
| Data Quality Score | 100% (3000+ OHLCV records validated) |

---

## Team DATAMINDS

- Ines Chtioui - Project Lead
- Amine Manai - Project Manager
- Mariem Fersi - Solution Architect
- Malek Chairat - Data Scientist
- Maha Aloui - Data Scientist

---

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — Full 16-section technical documentation
- [Data Preparation](../Data%20Preparation/README.md) — ETL pipeline docs
- [Data Acquisition](../Data%20Acquisition/README.md) — Source data pipeline

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built by Team DATAMINDS — March 2026**

</div>
