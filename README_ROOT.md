# Trady - AI-Powered FX Trading Platform

**Team DATAMINDS** - Intelligence Artificielle pour le Trading FX

## 🚀 Démarrage Rapide

Toute la plateforme se trouve dans le dossier **fx-alpha-platform**. 

```bash
cd fx-alpha-platform
```

Consultez le [README complet](fx-alpha-platform/README.md) pour les instructions d'installation et d'utilisation détaillées.

## 📁 Structure du Projet

```
fx-alpha-platform/
├── backend/              # Backend Django avec API REST
│   ├── acquisition/      # Acquisition de données (MT5, FRED, News)
│   ├── preparation/      # Préparation et nettoyage des données
│   ├── validation/       # Validation de la qualité des données
│   ├── features/         # Calcul des indicateurs et features
│   ├── agents/           # Système multi-agents avec LLM
│   ├── backtesting/      # Moteur de backtesting
│   ├── api/             # API REST Django
│   └── core/            # Infrastructure partagée
├── frontend/            # Interface Next.js + React
└── shared/              # Code partagé backend-frontend
```

## 🛠️ Technologies

- **Backend**: Django 5.0, PostgreSQL, InfluxDB, Redis
- **AI/ML**: LangChain, LangGraph, HuggingFace Transformers
- **Data**: MetaTrader 5, FRED API, RSS News  
- **Frontend**: Next.js 14, React, TypeScript, Tailwind CSS

## 🎯 Fonctionnalités Clés

### Acquisition de Données
- MetaTrader 5 pour les données OHLCV en temps réel
- FRED API pour les données macroéconomiques
- Flux RSS pour les actualités financières

### Préparation des Données
- Exploration et nettoyage automatisés
- Ingénierie de features avancée
- Validation de qualité des données

### Système Multi-Agents IA
- **TechnicalAgent**: Analyse technique des prix
- **MacroAgent**: Analyse fondamentale économique
- **SentimentAgent**: Analyse du sentiment des actualités
- **CoordinatorAgent**: Agrégation intelligente des signaux

### Backtesting & API
- Moteur de backtesting walk-forward
- API REST complète avec Django
- Documentation TDSP automatisée

## 👥 Équipe DATAMINDS

- **Ines Chtioui** - Project Lead
- **Amine Manai** - Project Manager
- **Mariem Fersi** - Solution Architect
- **Malek Chairat** - Data Scientist
- **Maha Aloui** - Data Scientist

## 🔗 Repository

GitHub: [INESCHTI/Dataminds_majorcurrencies](https://github.com/INESCHTI/Dataminds_majorcurrencies)

Branch: `aminemanai`

## 📄 License

MIT License - Voir [LICENSE](LICENSE) pour plus de détails.

---

**Built with ❤️ by Team DATAMINDS**


This UI is designed for the TDSP (Team Data Science Process) project:
- **Phase**: Multi-Agent FX Trading System
- **Objective**: Generate alpha signals for major currency pairs
- **Methodology**: Multi-modal analysis (Macro, Technical, Sentiment)
- **Target**: EUR/USD, USD/JPY, USD/CHF, GBP/USD

---

Built with ❤️ for the FX Multi-Agent Alpha Platform
