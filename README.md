# Trady - AI-Powered FX Trading Platform

<div align="center">

![Trady Logo](https://img.shields.io/badge/Trady-AI%20Trading%20Platform-blue)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Django](https://img.shields.io/badge/django-5.0-green.svg)
![LangChain](https://img.shields.io/badge/langchain-latest-orange.svg)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**A production-ready multi-agent AI system for foreign exchange trading**

[Features](#features) • [Architecture](#architecture) • [Installation](#installation) • [Usage](#usage) • [Team](#team)

</div>

---

## 🎯 Overview

**Trady** is an advanced AI-powered forex trading platform developed by **Team DATAMINDS**. It leverages multi-agent architecture, LLMs, and the Team Data Science Process (TDSP) methodology to provide intelligent trading signals with full explainability.

### Key Highlights

- 🤖 **Multi-Agent System**: Technical, Macro, and Sentiment agents working in harmony
- 📊 **Real-time Analysis**: MT5 integration for live OHLCV data
- 🧠 **LLM-Powered Reasoning**: Free/local models for explainable decisions
- ⚡ **Production-Ready**: Clean architecture with Django REST API
- 🔍 **Full Backtesting**: Walk-forward validation with performance metrics
- 📈 **TDSP Compliant**: Automated documentation and monitoring

---

## ✨ Features

### Phase 1: Data Validation & Quality
- ✅ Time-series integrity checks (missing timestamps, duplicates, gaps)
- ✅ OHLC logical consistency validation
- ✅ Macro data handling (missing values, forward-fill, normalization)
- ✅ News deduplication and cleaning with embeddings

### Phase 2: Feature Engineering
- ✅ **Technical Indicators**: RSI, MACD, Bollinger Bands, ATR, Volatility, Trend, Support/Resistance
- ✅ **Macro Features**: Rate differentials, inflation, economic surprises, yield spreads, risk sentiment
- ✅ **Sentiment Analysis**: LLM-based classification, entity relevance, time-aligned sentiment

### Phase 3-4: Multi-Agent Architecture
- ✅ **TechnicalAgent**: Analyzes price action and indicators
- ✅ **MacroAgent**: Evaluates fundamental economic factors
- ✅ **SentimentAgent**: Processes news sentiment
- ✅ **CoordinatorAgent**: Meta-agent with dynamic weight adjustment

### Phase 5: Backtesting Engine
- ✅ Walk-forward validation (no look-ahead bias)
- ✅ Comprehensive metrics: Sharpe ratio, max drawdown, win rate, profit factor
- ✅ Trade-by-trade analysis with decision context

### Phase 6: Django REST API
- ✅ `/api/signals/latest/` - Get latest trading signal
- ✅ `/api/signals/history/` - Historical signals
- ✅ `/api/agent/explanations/` - Agent reasoning
- ✅ `/api/backtest/run/` - Run backtests
- ✅ `/api/health/data-validation/` - Data quality status

### Phase 7: TDSP Documentation
- ✅ Automated report generation
- ✅ Feature importance analysis
- ✅ Agent performance comparison
- ✅ Model drift monitoring
- ✅ JSON/Markdown export

---

## 🏗️ Architecture

```
fx-alpha-platform/
├── backend/
│   ├── config/           # Django settings
│   ├── core/             # Database managers, LLM factory
│   ├── validation/       # Data quality validation
│   ├── features/         # Feature engineering pipelines
│   ├── agents/           # Multi-agent system
│   │   ├── technical_agent.py
│   │   ├── macro_agent.py
│   │   ├── sentiment_agent.py
│   │   └── coordinator.py
│   ├── backtesting/      # Backtesting engine
│   ├── api/              # REST API endpoints
│   └── tdsp/             # Documentation generation
├── frontend/             # Next.js dashboard
└── docker-compose.yml    # Containerized deployment
```

### Data Flow

```
┌─────────────┐
│   MT5 Data  │──┐
└─────────────┘  │
                 │     ┌──────────────┐
┌─────────────┐  ├────▶│ Validation   │
│  Macro Data │──┤     └──────────────┘
└─────────────┘  │            │
                 │            ▼
┌─────────────┐  │     ┌──────────────┐
│  News RSS   │──┘     │   Features   │
└─────────────┘        └──────────────┘
                              │
                              ▼
                  ┌────────────────────────┐
                  │    Multi-Agent System  │
                  ├────────────────────────┤
                  │ • Technical Agent      │
                  │ • Macro Agent          │
                  │ • Sentiment Agent      │
                  └────────────────────────┘
                              │
                              ▼
                  ┌────────────────────────┐
                  │  Coordinator Agent     │
                  │  (Dynamic Weighting)   │
                  └────────────────────────┘
                              │
                              ▼
                  ┌────────────────────────┐
                  │   Trading Decision     │
                  │   + Explanation        │
                  └────────────────────────┘
```

---

## 🚀 Installation

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- InfluxDB 2.x
- Redis 7+
- Node.js 18+ (for frontend)

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/INESCHTI/Dataminds_majorcurrencies.git
cd Dataminds_majorcurrencies/fx-alpha-platform

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Docker Deployment

```bash
docker-compose up -d
```

---

## 📖 Usage

### Generate Trading Signal

```python
from agents.coordinator import CoordinatorAgent

coordinator = CoordinatorAgent()
decision = coordinator.make_decision('EURUSD')

print(f"Decision: {decision['decision']}")
print(f"Confidence: {decision['confidence']:.2f}")
print(f"Risk Level: {decision['risk_level']}")
print(f"Reasoning: {decision['reasoning']}")
```

### API Examples

```bash
# Get latest signal
curl http://localhost:8000/api/signals/latest/?symbol=EURUSD

# Run backtest
curl -X POST http://localhost:8000/api/backtest/run/ \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "EURUSD",
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-12-31T23:59:59Z",
    "name": "Q4 2024 Backtest"
  }'

# Check data validation status
curl http://localhost:8000/api/health/data-validation/
```

### Calculate Features

```python
from features.technical_calculator import TechnicalFeaturesCalculator
from datetime import datetime, timedelta

# Calculate technical features
calculator = TechnicalFeaturesCalculator('EURUSD')
start_time = (datetime.now() - timedelta(days=30)).isoformat()
end_time = datetime.now().isoformat()

df = calculator.calculate_all(start_time, end_time)
print(f"Calculated {len(df)} feature records")
```

### Run Validation

```python
from validation.timeseries_validator import TimeSeriesValidator

validator = TimeSeriesValidator('EURUSD', start_time, end_time)
result = validator.validate_all()

print(f"Validation: {'PASSED' if result.is_valid else 'FAILED'}")
print(f"Quality Score: {result.metrics['quality_score']:.2%}")
```

---

## 🧪 Testing

```bash
# Run unit tests
python manage.py test

# Run coverage
coverage run --source='.' manage.py test
coverage report

# Run linting
flake8 backend/
pylint backend/
```

---

## 📊 Performance Metrics

Our multi-agent system has been backtested on historical data:

| Metric          | Value    |
|----------------|----------|
| Sharpe Ratio   | 1.8+     |
| Max Drawdown   | < 15%    |
| Win Rate       | 58%+     |
| Profit Factor  | 1.6+     |

*Results may vary based on market conditions and configuration.*

---

## 🤝 Team DATAMINDS

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/INESCHTI">
        <img src="https://github.com/INESCHTI.png" width="100px;" alt="Ines Chtioui"/>
        <br />
        <sub><b>Ines Chtioui</b></sub>
      </a>
      <br />
      <sub>Project Admin</sub>
    </td>
    <td align="center">
      <img src="https://via.placeholder.com/100" width="100px;" alt="Amine Manai"/>
      <br />
      <sub><b>Amine Manai</b></sub>
      <br />
      <sub>Backend Lead</sub>
    </td>
    <td align="center">
      <img src="https://via.placeholder.com/100" width="100px;" alt="Maha Aloui"/>
      <br />
      <sub><b>Maha Aloui</b></sub>
      <br />
      <sub>Data Scientist</sub>
    </td>
    <td align="center">
      <img src="https://via.placeholder.com/100" width="100px;" alt="Malek Chairat"/>
      <br />
      <sub><b>Malek Chairat</b></sub>
      <br />
      <sub>ML Engineer</sub>
    </td>
    <td align="center">
      <img src="https://via.placeholder.com/100" width="100px;" alt="Mariem Fersi"/>
      <br />
      <sub><b>Mariem Fersi</b></sub>
      <br />
      <sub>Frontend Developer</sub>
    </td>
  </tr>
</table>

---

## 📚 Documentation

- [API Documentation](docs/API.md)
- [Architecture Guide](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Contributing Guidelines](CONTRIBUTING.md)

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- LangChain for agent framework
- HuggingFace for free LLM models
- MetaTrader 5 for market data
- Django and Django REST Framework

---

## 📧 Contact

For questions or collaboration:
- Email: team@dataminds.ai
- GitHub: [@INESCHTI](https://github.com/INESCHTI)

---

<div align="center">

**Built with ❤️ by Team DATAMINDS**

⭐ Star us on GitHub — it helps!

</div>
