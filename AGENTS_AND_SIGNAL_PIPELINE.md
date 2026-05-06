# FX Alpha Platform — Agents & Signal Generation Pipeline
### Analyse technique complète · Avril 2026

---

## Table des matières

1. [Vue d'ensemble de l'architecture](#1-vue-densemble-de-larchitecture)
2. [Principes fondamentaux de conception](#2-principes-fondamentaux-de-conception)
3. [Couche d'acquisition des données](#3-couche-dacquisition-des-données)
4. [Couche de données (Data Layer)](#4-couche-de-données-data-layer)
5. [Couche de features (Feature Layer)](#5-couche-de-features-feature-layer)
6. [Couche de signal (Signal Layer) — Les 4 Agents](#6-couche-de-signal-signal-layer--les-4-agents)
   - 6.1 [TechnicalAgentV2](#61-technicalagentv2)
   - 6.2 [MacroAgentV2](#62-macroagentv2)
   - 6.3 [SentimentAgentV2](#63-sentimentagentv2)
   - 6.4 [GeopoliticalAgentV2](#64-geopoliticalagentv2)
7. [CoordinatorAgentV2 — Le Meta-Agent](#7-coordinatoragentv2--le-meta-agent)
8. [Couche de décision (Decision Layer)](#8-couche-de-décision-decision-layer)
   - 8.1 [ActuarialScorer](#81-actuarialscorer)
   - 8.2 [LLMToolJudge (Stage 2.5)](#82-llmtooljudge-stage-25)
   - 8.3 [LLMJudge (Stage 3)](#83-llmjudge-stage-3)
   - 8.4 [RiskManager](#84-riskmanager)
   - 8.5 [XAIFormatter](#85-xaiformatter)
9. [TradingDecisionPipeline — Orchestrateur Final](#9-tradingdecisionpipeline--orchestrateur-final)
10. [Couche de monitoring](#10-couche-de-monitoring)
11. [Flux complet de A à Z](#11-flux-complet-de-a-à-z)
12. [Matrices de décision et seuils](#12-matrices-de-décision-et-seuils)
13. [Technologies et frameworks utilisés](#13-technologies-et-frameworks-utilisés)

---

## 1. Vue d'ensemble de l'architecture

Le système est organisé en **couches verticales strictement séparées** :

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ACQUISITION LAYER                           │
│  MT5Collector (OHLCV)  │  FREDCollector (macro)  │  NewsCollector   │
│         InfluxDB        │       PostgreSQL         │    PostgreSQL    │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────┐
│                           DATA LAYER                                │
│    TimeSeriesLoader       │   MacroDataLoader   │   NewsLoader       │
│    (OHLCV InfluxDB)       │   (PostgreSQL)      │   (PostgreSQL)     │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────┐
│                         FEATURE LAYER                               │
│  TechnicalFeatureEngine  │  MacroFeatureEngine  │ SentimentFeature   │
│  (60 indicateurs TA)     │  (taux, inflation)   │ Engine (NLP/Heur.) │
│                          │                      │                    │
│         CrossPairCorrelationEngine (DSO1.3)                         │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────┐
│                          SIGNAL LAYER                               │
│ TechnicalAgentV2 │ MacroAgentV2 │ SentimentAgentV2 │ GeoPoliticalV2  │
│                                                                     │
│                    CoordinatorAgentV2 (Meta-Agent)                  │
│           Weighted Vote + Dynamic Weights + Regime Detection        │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────┐
│                        DECISION LAYER                               │
│  ActuarialScorer  │  LLMToolJudge  │  LLMJudge  │  RiskManager      │
│  (EV, P(win), RR) │  (advisory)    │  (APPROVE/ │  (veto absolu)    │
│                                   │   REJECT)   │                   │
│                         XAIFormatter                                │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │
                              API Response (Django REST)
```

---

## 2. Principes fondamentaux de conception

Le système repose sur un **principe de séparation strict** entre logique déterministe et LLM :

| Composant | LLM utilisé ? | Justification |
|-----------|--------------|---------------|
| Calcul d'indicateurs TA | ❌ Non | Math pure |
| Règles de signal (RSI, MACD…) | ❌ Non | Seuils déterministes |
| Agrégation pondérée des agents | ❌ Non | Algèbre vectorielle |
| Détection de régime de marché | ❌ Non | Seuils ADX/volatilité |
| Corrélations inter-paires | ❌ Non | Pearson sur log-returns |
| Calcul EV / Kelly / RR | ❌ Non | Formules actuarielles |
| Risk Manager | ❌ Non | Règles discrètes |
| Classification sentiment articles | ✅ Oui (optionnel) | Heuristique en fallback |
| LLMJudge validation | ✅ Oui (Ollama local) | Gate de validation |
| Explication finale en langage naturel | ✅ Oui (Ollama local) | Interface utilisateur |

> **Règle cardinale** : Le LLM ne peut **jamais** générer un signal de trading. Il ne peut qu'approuver, rejeter, ou commenter une décision déjà prise par des algorithmes déterministes.

---

## 3. Couche d'acquisition des données

**Fichiers** : `backend/acquisition/`

L'orchestrateur `orchestrator.py` lance séquentiellement 3 collecteurs :

### 3.1 MT5Collector (`mt5_collector.py`)

- **Source** : MetaTrader 5 via l'API Python `MetaTrader5`
- **Paires** : `EURUSD`, `USDJPY`, `GBPUSD`, `USDCHF`
- **Timeframes collectés** : `1H`, `4H`, `1D`
- **Horizon historique** : 5 ans (`days_back=1825`)
- **Destination** : **InfluxDB** (time-series database)
- **Format stocké** : Points `forex_prices` avec tags `symbol`, `timeframe` et fields `open`, `high`, `low`, `close`, `volume`

```python
# Exemple de point InfluxDB écrit
Point("forex_prices")
    .tag("symbol", "EURUSD")
    .tag("timeframe", "1H")
    .field("open", 1.0852)
    .field("close", 1.0864)
    ...
```

### 3.2 FREDCollector (`fred_collector.py`)

- **Source** : API publique FRED (Federal Reserve Economic Data)
- **Données** : Taux directeurs et inflation par devise (EUR, USD, JPY, GBP, CHF)
- **Destination** : **PostgreSQL** (tables `interest_rates`, `inflation_rates`)

### 3.3 NewsCollector (`news_collector.py`)

- **Sources RSS** (par priorité de fallback) :
  1. Investing.com Forex RSS
  2. FXStreet RSS
  3. DailyFX RSS
  4. ForexLive RSS
  5. Reuters Business RSS
- **Filtrage** : Articles contenant les mots-clés `forex`, `EUR`, `USD`, `JPY`, `GBP`, `CHF`, `Federal Reserve`, `ECB`, `currency`, `exchange rate`
- **Destination** : **PostgreSQL** (table `news_articles`)
- **Champs** : `url`, `title`, `content` (max 1000 chars), `source`, `published_at`, `currencies[]`, `sentiment_score`

---

## 4. Couche de données (Data Layer)

**Fichiers** : `backend/data_layer/`

Couche de **lecture pure** — aucun calcul, aucune logique métier.

### 4.1 TimeSeriesLoader (`timeseries_loader.py`)

- Charge les données OHLCV depuis **InfluxDB** (primaire) + **SQLite** (fallback)
- Supporte le **multi-timeframe** (DSO1.2) :

| Timeframe | Label | Resample |
|-----------|-------|---------|
| `1h` | Intraday | — |
| `4h` | Intraday Swing | `4h` |
| `1d` | Daily Swing | `1D` |
| `1w` | Weekly Position | `1W` |
| `1M` | Monthly Position | `1ME` |

- Méthode `latest_timestamp()` compare InfluxDB et SQLite pour retourner le timestamp le plus récent
- Fallback SQLite via le modèle Django `OHLCVCandle`

### 4.2 MacroDataLoader (`macro_loader.py`)

- Charge depuis PostgreSQL les tables `interest_rates` et `inflation_rates`
- Retourne des DataFrames avec colonnes `currency`, `rate`/`inflation_rate`, `date`

### 4.3 NewsLoader (`news_loader.py`)

- Charge les articles de PostgreSQL filtrés par `currencies` et `start_time`
- Retourne `news_df` avec `id`, `title`, `content`, `timestamp`, `sentiment_score` (pré-calculé si disponible)
- Méthode `latest_timestamp()` pour détection de fraîcheur des données

---

## 5. Couche de features (Feature Layer)

**Fichiers** : `backend/feature_layer/`

Couche de **calcul mathématique pur** — aucun LLM, aucune décision.

### 5.1 TechnicalFeatureEngine (`technical_features.py`)

Calcule **85+ features** organisées en 4 groupes via la bibliothèque **`ta` (Technical Analysis Library)** :

#### Indicateurs de Momentum (groupe A)
| Feature | Paramètre | Bibliothèque |
|---------|----------|-------------|
| `rsi_14` | RSI 14 périodes | `ta.momentum.RSIIndicator` |
| `rsi_7` | RSI 7 périodes | `ta.momentum.RSIIndicator` |
| `macd` | MACD line | `ta.trend.MACD` |
| `macd_signal` | Signal line | `ta.trend.MACD` |
| `macd_diff` | Histogramme | `ta.trend.MACD` |
| `stoch_k` | Stochastique %K | `ta.momentum.StochasticOscillator` |
| `stoch_d` | Stochastique %D | `ta.momentum.StochasticOscillator` |
| `williams_r` | Williams %R | `ta.momentum.WilliamsRIndicator` |
| `roc_5/10/20` | Rate of Change | calcul manuel |
| `cci_20` | CCI 20 | `ta.trend.CCIIndicator` |
| `mfi_14` | Money Flow Index | `ta.volume.MFIIndicator` |

#### Indicateurs de Tendance (groupe B)
| Feature | Paramètre |
|---------|----------|
| `bb_upper/middle/lower` | Bollinger Bands (20, 2σ) |
| `bb_width` | Largeur des bandes |
| `bb_pctb` | %B position |
| `sma_10/20/50/200` | Moyennes mobiles simples |
| `ema_9/12/21/26/55` | Moyennes mobiles exponentielles |
| `adx` | Average Directional Index (14) |
| `adx_pos/neg` | +DI / -DI |
| `ichimoku_a/b/base/conv` | Ichimoku Cloud |

#### Indicateurs de Volatilité (groupe C)
| Feature | Paramètre |
|---------|----------|
| `atr_14/7` | Average True Range |
| `keltner_high/low` | Keltner Channel |
| `donchian_high/low` | Canal Donchian (20) |
| `volatility_20/60` | Vol historique annualisée × √252 |

#### Indicateurs de Volume (groupe D)
| Feature | Paramètre |
|---------|----------|
| `volume_sma_20` | Volume SMA 20 |
| `volume_ratio` | Volume / SMA |
| `obv` | On-Balance Volume |
| `vwap` | VWAP approximé |
| `ad_line` | Accumulation/Distribution |

#### Features Temporelles (25 features)
```python
# Sessions FX (critiques pour le Forex)
'session_asian'      # 00h-08h UTC
'session_european'   # 07h-16h UTC
'session_us'         # 13h-22h UTC
'session_overlap_eu_us'  # 13h-16h UTC (chevauchement, max volatilité)

# Encodage cyclique (sin/cos pour la périodicité)
'hour_sin', 'hour_cos'      # Heure de la journée
'dow_sin', 'dow_cos'        # Jour de la semaine
'month_sin', 'month_cos'    # Mois de l'année

# Drapeaux événementiels
'is_nfp_week'        # Premier vendredi du mois (Non-Farm Payrolls)
'is_high_volume_hour'  # 13h-17h UTC
```

#### Features dérivées (interactions)
```python
'rsi_macd_divergence'    # (RSI>50).int - (MACD_diff>0).int
'price_sma50_dist'       # Distance % au SMA50
'price_sma200_dist'      # Distance % au SMA200
'atr_pct'                # ATR en % du prix
'bb_position'            # Position normalisée dans les bandes BB
'sma_trend'              # "strong_bullish" | "bullish" | "neutral" | etc.
```

### 5.2 MacroFeatureEngine (`macro_features.py`)

Calculs économiques déterministes :

```
rate_differential = rate_base - rate_quote
inflation_differential = inflation_base - inflation_quote
real_rate = nominal_rate - inflation_rate              (Fisher)
carry_score = rate_differential / price_volatility
rate_momentum = (rate_t - rate_t-90j) / rate_t-90j × 100
```

### 5.3 SentimentFeatureEngine (`sentiment_features.py`)

**Deux chemins** :

**Fast Path** (utilisé par défaut) — heuristique déterministe :
```python
bullish_terms = ["hawkish", "rate hike", "beats", "strong", "growth", "surge", ...]
bearish_terms = ["dovish", "rate cut", "misses", "weak", "recession", "drop", ...]
raw = bull_count - bear_count
sentiment = clamp(raw / 4.0, -1.0, 1.0)
```

**Slow Path** (si `ENABLE_LLM_SENTIMENT=true` ET budget non épuisé) :
- Budget : max **6 articles** ou **8 secondes**
- Appel Ollama local pour extraction JSON `{sentiment: float, relevance: float, explained: str}`
- Fallback automatique sur heuristique si budget dépassé ou erreur

**Agrégation déterministe** (indépendante du chemin) :
```python
time_decay = exp(-(hours_since_publication) / 24.0)
weight = relevance × time_decay
sentiment_agg = Σ(sentiment_i × weight_i) / Σ(weight_i)

# Seuils de signal
if sentiment_agg > 0.3  → signal = +1 (BUY)
if sentiment_agg < -0.3 → signal = -1 (SELL)
else                     → signal = 0  (NEUTRAL)
confidence = min(|sentiment_agg| × article_count × 0.1, 1.0)
```

### 5.4 CrossPairCorrelationEngine (`cross_pair_correlations.py`)

Corrélations inter-paires pour validation des signaux (DSO1.3) :

**Méthode** : Corrélation de Pearson sur **log-returns** (90 jours, données 1H)

```python
log_returns = ln(price_t / price_t-1)
corr_matrix = log_returns.corr()  # Pearson
```

**Corrélations fondamentales connues** (fallback si données insuffisantes) :
| Paires | Corrélation |
|--------|-------------|
| EURUSD ↔ GBPUSD | +0.76 |
| USDJPY ↔ USDCHF | +0.68 |
| EURUSD ↔ USDCHF | -0.76 |
| EURUSD ↔ USDJPY | -0.59 |
| GBPUSD ↔ USDCHF | -0.58 |
| GBPUSD ↔ USDJPY | -0.42 |

**Ajustement de confiance** basé sur l'alignement inter-paires :
```
signal_alignment > +0.3  → confidence × 1.15 (+15%)
signal_alignment < -0.3  → confidence × 0.75 (-25%)
```

---

## 6. Couche de signal (Signal Layer) — Les 4 Agents

**Fichiers** : `backend/signal_layer/`

Chaque agent retourne un dict standardisé :
```python
{
    'signal': -1 | 0 | 1,      # SELL | NEUTRAL | BUY
    'confidence': float,        # 0.0 → 1.0
    'features_used': dict,      # Indicateurs utilisés pour audit
    'deterministic_reason': str # Raison textuelle déterministe
}
```

---

### 6.1 TechnicalAgentV2

**Fichier** : `backend/signal_layer/technical_agent_v2.py`  
**Type** : 100% déterministe — aucun LLM

#### Pipeline interne

```
TimeSeriesLoader.load_ohlcv(symbol)
        ↓
TechnicalFeatureEngine.calculate_all(df)    ← 85+ indicateurs
        ↓
TechnicalFeatureEngine.get_current_values() ← Valeurs actuelles
        ↓
_apply_technical_rules(indicators)          ← Vote pondéré
        ↓
{signal, confidence, features_used, reason}
```

#### Règles de décision (vote pondéré)

| Règle | Condition BUY (+1) | Condition SELL (-1) | Poids |
|-------|-------------------|---------------------|-------|
| **RSI** | `rsi_14 < 30` (oversold) | `rsi_14 > 70` (overbought) | 0.25 |
| **MACD** | `macd_diff > 0` (momentum haussier) | `macd_diff < 0` (momentum baissier) | 0.30 |
| **Bollinger** | `bb_position < -0.8` (bande basse) | `bb_position > 0.8` (bande haute) | 0.20 |
| **SMA Trend** | `sma_trend == 'strong_bullish'` | `sma_trend == 'strong_bearish'` | 0.25 |

#### Calcul du signal final

```python
weighted_signal = Σ(signal_i × weight_i) / Σ(weight_i)

if weighted_signal > 0.3  → final_signal = +1
if weighted_signal < -0.3 → final_signal = -1
else                       → final_signal = 0

confidence = min(Σ(weight_i_fired), 1.0)
```

---

### 6.2 MacroAgentV2

**Fichier** : `backend/signal_layer/macro_agent_v2.py`  
**Type** : 100% déterministe — aucun LLM

#### Pipeline interne

```
MacroDataLoader.load_interest_rates(currencies)
MacroDataLoader.load_inflation_rates(currencies)
        ↓
MacroFeatureEngine.calculate_rate_differentials()  → rate_diff
MacroFeatureEngine.calculate_inflation_differential() → infl_diff
MacroFeatureEngine.calculate_macro_momentum()       → rate_momentum
MacroFeatureEngine.calculate_carry_score()          → carry_score
        ↓
MacroFeatureEngine.get_macro_signal(rate_diff, infl_diff, momentum, carry)
        ↓
{signal, confidence, features_used, reason}
```

#### Règles de décision

```
signal_score = 0
confidence_factors = []

# Règle 1 — Différentiel de taux (poids 50%)
if rate_diff > +0.5%  → signal_score += 1.0,   confidence += 0.5
if rate_diff < -0.5%  → signal_score -= 1.0,   confidence += 0.5
else                  →                         confidence += 0.2

# Règle 2 — Momentum des taux (poids 30%)
if rate_momentum > +0.1% → signal_score += 0.6, confidence += 0.3
if rate_momentum < -0.1% → signal_score -= 0.6, confidence += 0.3

# Règle 3 — Carry score (poids 20%)
if carry_score > +10  → signal_score += 0.4,   confidence += 0.2
if carry_score < -10  → signal_score -= 0.4,   confidence += 0.2

# Normalisation
if signal_score > +0.7  → signal = +1
if signal_score < -0.7  → signal = -1
else                     → signal = 0
```

---

### 6.3 SentimentAgentV2

**Fichier** : `backend/signal_layer/sentiment_agent_v2.py`  
**Type** : LLM pour classification uniquement (optionnel), agrégation déterministe

#### Pipeline interne

```
NewsLoader.load_news(currencies, start=now-168h, limit=100)
        ↓
[Si données vides ou > 4h de fraîcheur]
        → _refresh_news_data_async()   ← Thread background
        → Rechargement immédiat
        ↓
[Fallback 30 jours si toujours vide]
        ↓
SentimentFeatureEngine.calculate_sentiment_batch(news_df, currencies)
        │
        ├─ Fast path : Pre-computed DB score → utilise directement
        ├─ Fast path : Heuristique lexicale (par défaut)
        └─ Slow path : Ollama LLM (si ENABLE_LLM_SENTIMENT=true, budget restant)
        ↓
SentimentFeatureEngine.aggregate_sentiment(sentiment_df)
        ↓
{signal, confidence, avg_sentiment, article_count}
```

#### Gestion de la fraîcheur des données
- **Max staleness** : 4 heures
- **Rafraîchissement** : Thread daemon asynchrone (non-bloquant)
- **Fenêtre de lookback** : 168h (7 jours) → garantit la couverture même si le pipeline était inactif

---

### 6.4 GeopoliticalAgentV2

**Fichier** : `backend/signal_layer/geopolitical_agent_v2.py`  
**Type** : 100% déterministe — scoring par mots-clés

#### Sources de données (cascade de fallback)

```
1. GDELT 2.0 DOC API      — gratuit, sans clé API  (max 20 résultats)
2. NewsAPI.org             — tier gratuit, NEWSAPI_KEY env var (100 req/jour)
3. GNews API               — tier gratuit, GNEWS_KEY env var (10 req/jour)
4. RSS Feeds               — BBC World, CNN, BBC Business, Al Jazeera
5. PostgreSQL fallback     — table news_articles déjà en base
```

**Cache** : Résultats mis en cache 3600 secondes (1 heure) par paire de devises

#### Scoring géopolitique déterministe

**Profils devises** :
```python
SAFE_HAVEN = {"CHF", "JPY", "USD"}          # Flux risk-off
RISK_ON_CURRENCIES = {"EUR", "GBP", "AUD", "NZD", "CAD"}  # Flux risk-on
```

**Mots-clés de risque** :
```python
RISK_OFF_KEYWORDS = [
    "war", "conflict", "invasion", "crisis", "collapse", "sanctions",
    "nuclear", "terrorism", "banking crisis", "debt default", ...
]
RISK_ON_KEYWORDS = [
    "peace", "ceasefire", "deal", "recovery", "growth", "stimulus",
    "gdp growth", "trade deal", "unemployment fell", ...
]
```

**Algorithme de scoring** :
```python
for headline in headlines:
    risk_off_hits = count(RISK_OFF_KEYWORDS in headline)
    risk_on_hits  = count(RISK_ON_KEYWORDS in headline)
    
    # Impact sur les devises (safe haven vs risk-on)
    if risk_off_hits > risk_on_hits:
        base_currency ∈ SAFE_HAVEN  → signal = +1 (BUY safe haven)
        base_currency ∈ RISK_ON     → signal = -1 (SELL risk-on)
    elif risk_on_hits > risk_off_hits:
        base_currency ∈ RISK_ON     → signal = +1 (BUY risk-on)
        base_currency ∈ SAFE_HAVEN  → signal = -1 (SELL safe haven)

confidence = tanh(|net_score| / 10)  # Normalisé 0—1
```

---

## 7. CoordinatorAgentV2 — Le Meta-Agent

**Fichier** : `backend/signal_layer/coordinator_agent_v2.py`

Le Coordinator est le **cerveau central** qui agrège les 4 agents via un vote pondéré dynamique.

### Poids par défaut

```python
agent_weights = {
    'TechnicalV2':    0.35,   # Plus grand poids (données exactes)
    'MacroV2':        0.25,
    'SentimentV2':    0.20,
    'GeopoliticalV2': 0.20,
}
```

### Pipeline du Coordinator (6 étapes)

```
Step 1 → Collecter les signaux des 4 agents
Step 2 → Ajuster les poids dynamiquement (Sharpe 30j)
Step 3 → Détecter le régime de marché
Step 4 → Vote pondéré (pure math)
Step 5 → Règles de sécurité + conflits
Step 5b→ Validation corrélations inter-paires (DSO1.3)
Step 6 → Générer l'explication texte (LLM uniquement)
```

---

#### Step 1 — Collecte des signaux

```python
technical_signal   = TechnicalAgentV2.generate_signal(symbol)
macro_signal       = MacroAgentV2.generate_signal(base, quote, volatility)
sentiment_signal   = SentimentAgentV2.generate_signal([base, quote])
geopolitical_signal = GeopoliticalAgentV2.generate_signal([base, quote])
```

---

#### Step 2 — Poids dynamiques (basés sur la performance)

Algorithme de mise à jour des poids par **Sharpe Ratio glissant 30 jours** :

```python
# Récupérer le Sharpe 30j de chaque agent depuis PostgreSQL
sharpe_30j = PerformanceTracker.get_agent_performance(agent_name, days=30)

# Ajustement softmax-like
adjusted_perf = max(sharpe + 2.0, 0.1)    # Évite les poids négatifs
new_weights = adjusted_perf / Σ(adjusted_perf)

# Lissage (momentum des poids)
smoothed_weights = 0.8 × old_weights + 0.2 × new_weights

# Renormalisation
final_weights = smoothed_weights / Σ(smoothed_weights)
```

> Si aucune donnée de performance n'est disponible → utilisation des poids par défaut.

---

#### Step 3 — Détection du régime de marché

```python
adx = technical_signal['features_used'].get('adx', 0)
annual_volatility = _estimate_volatility(symbol)  # Vol annualisée depuis InfluxDB 30D

if annual_volatility > 0.15:   → regime = 'volatile'
elif adx > 25:                 → regime = 'trending'
else:                          → regime = 'ranging'
```

---

#### Step 4 — Vote pondéré avec adaptation au régime

```python
# Ajustement des poids selon le régime
if regime == 'trending':
    weights['TechnicalV2'] *= 1.3    # Favorise l'analyse TA en tendance
elif regime == 'ranging':
    weights['MacroV2'] *= 1.2        # Favorise les fondamentaux en range
elif regime == 'volatile':
    weights = {k: v * 0.7 for ...}  # Réduit tous les poids en volatilité

# Renormalisation (somme = 1.0)
# Vote final
weighted_score = Σ(signal_i × confidence_i × weight_i)
avg_confidence = Σ(confidence_i × weight_i)

# Seuil de décision (0.12 — assez bas pour déclencher avec 1 seul agent)
if weighted_score > +0.12 → signal = +1
if weighted_score < -0.12 → signal = -1
else                       → signal = 0
```

---

#### Step 5 — Règles de sécurité et détection de conflits

```python
# Détection de conflit : agents divergents (1 long ET 1 short)
conflicts = (+1 in signals) AND (-1 in signals)

# Application des règles
if conflicts:             adjusted_confidence *= 0.5   # -50% de confiance
if regime == 'volatile':  adjusted_confidence *= 0.7   # -30% en volatilité
if adjusted_confidence < 0.12 → force signal = 0      # Force NEUTRAL
```

---

#### Step 5b — Validation corrélations inter-paires (DSO1.3)

```python
corr_info = CrossPairCorrelationEngine.get_correlation_signals(symbol)

# Ajustement basé sur l'alignement des paires corrélées
if corr_info['signal_alignment'] > +0.3:
    confidence *= 1.15    # Signal confirmé par paires corrélées → +15%
elif corr_info['signal_alignment'] < -0.3:
    confidence *= 0.75    # Signal en contradiction → -25%
```

---

#### Step 6 — Génération de l'explication (LLM uniquement)

```python
# LLM appelé SEULEMENT pour générer du texte explicatif
# N'a AUCUNE influence sur le signal ou la confiance
explanation = _generate_explanation_text(
    final_signal, agent_signals, weights, conflicts
)
```

### Output du Coordinator

```python
{
    'final_signal':          -1 | 0 | 1,
    'confidence':            float,
    'weighted_score':        float,
    'agent_signals':         { 'TechnicalV2': {...}, 'MacroV2': {...}, ... },
    'weights_used':          { 'TechnicalV2': 0.35, ... },
    'market_regime':         'trending' | 'ranging' | 'volatile',
    'conflicts_detected':    bool,
    'cross_pair_correlations': { 'signal_alignment': float, 'conflicts': [...], ... },
    'deterministic_reason':  str,
    'explanation':           str,   # LLM — texte uniquement
    'timestamp':             ISO8601
}
```

---

## 8. Couche de décision (Decision Layer)

**Fichiers** : `backend/decision_layer/`

Cette couche applique **5 filtres successifs** au signal du Coordinator avant toute décision de trading.

---

### 8.1 ActuarialScorer

**Fichier** : `backend/decision_layer/actuarial_scorer.py`

Convertit le signal en métriques probabilistes via des formules actuarielles.

#### Estimation de P(win)

```python
# Ajustement de la base win_rate par la confiance
confidence_adjusted = base_win_rate + (confidence - 0.5) × 0.3
p_win = clamp(confidence_adjusted, 0.40, 0.75)
p_loss = 1.0 - p_win
```

#### Expected Value (EV)

```python
EV_pips = P(win) × avg_win_pips - P(loss) × avg_loss_pips
EV_usd  = EV_pips × 10    # Hypothèse $10/pip
```

#### Ratio Risk/Reward

```python
RR = avg_win_pips / avg_loss_pips    # Cible ≥ 1.5
```

#### Critère de Kelly

```python
R = avg_win / avg_loss
Kelly = P(win) - (1 - P(win)) / R
half_kelly = Kelly / 2    # Conservation (half-Kelly)
```

#### Statistiques historiques (100 derniers jours)

L'ActuarialScorer interroge `agent_performance_log` pour récupérer :
- `win_rate` historique par symbole
- `avg_win_pips` et `avg_loss_pips` réels

**Output** :
```python
{
    'expected_value_pips':  float,      # Seuil de rejet : EV < 0
    'expected_value_usd':   float,
    'probability_win':      float,
    'probability_loss':     float,
    'risk_reward_ratio':    float,
    'kelly_fraction':       float,
    'recommendation':       str,
    'verdict':              'TRADE' | 'NO_TRADE'
}
```

> **Règle d'arrêt précoce** : Si `EV < 0` → rejet immédiat **sans** appel au LLMJudge.

---

### 8.2 LLMToolJudge (Stage 2.5)

**Fichier** : `backend/decision_layer/llm_tool_judge.py`  
**Rôle** : Enrichissement metadata **purement consultatif** — ne peut jamais bloquer le pipeline

- **Modèle** : `llama3.2:3b` via Ollama local
- **Timeout** : 800ms
- **Verdict** : Toujours `COMMENT_ONLY` (contract garanti par code)
- **Output** : `confidence_adjustment`, `risk_flags`, `inconsistencies`
- **Application** : La confiance est ajustée (clampée entre 0 et 1) si `confidence_adjustment ≠ 0`

**Fail-safe** : Si Ollama est indisponible ou timeout → retourne `_FAIL_SAFE_RESPONSE` sans bloquer.

```python
_FAIL_SAFE_RESPONSE = {
    "verdict": "COMMENT_ONLY",
    "confidence_adjustment": 0.0,
    "risk_flags": ["LLM_UNAVAILABLE"],
    ...
}
```

---

### 8.3 LLMJudge (Stage 3)

**Fichier** : `backend/decision_layer/llm_judge.py`  
**Rôle** : Gate de validation — peut **APPROVE**, **REJECT** ou **MODIFY**

- **Modèle** : `llama3.2:3b` via Ollama local
- **Timeout HTTP** : 30 secondes (inférence CPU locale)
- **Seuil de performance warning** : 5 secondes

#### Vérifications pré-LLM (déterministes)

```python
MIN_CONFIDENCE = 0.20
MIN_EV_PIPS    = 0.0

if confidence < MIN_CONFIDENCE → REJECT (avant appel LLM)
if EV_pips < MIN_EV_PIPS      → REJECT (avant appel LLM)
```

#### Cache

- Clé de cache : SHA256 de `{signal, confidence, EV, P(win), RR}`
- Évite les appels LLM redondants pour des setups identiques

#### Fail-safe

Si Ollama est indisponible ou retourne une erreur → **verdict `APPROVE`** (pass-through vers RiskManager plutôt que blocage).

**Output** :
```python
{
    'verdict':              'APPROVE' | 'REJECT' | 'MODIFY',
    'reasoning':            str,
    'latency_ms':           int,
    'confidence_adjusted':  float | None,    # Si MODIFY
    'rejection_criteria':   list[str],
    'from_cache':           bool
}
```

---

### 8.4 RiskManager

**Fichier** : `backend/risk/risk_manager.py`  
**Rôle** : Veto absolu — peut bloquer un trade approuvé par le LLMJudge

**Configuration par défaut** :
```python
MAX_RISK_PER_TRADE_PCT    = 2.0%   # Max capital risqué par trade
MAX_DRAWDOWN_PCT          = 15.0%  # Stop si drawdown > 15%
MIN_RR_RATIO              = 1.5    # Risk/Reward minimal
MAX_CONCURRENT_POSITIONS  = 4      # Max positions simultanées
MIN_CONFIDENCE            = 0.50   # Confiance minimale
MIN_EV_PIPS               = 5.0    # EV minimale en pips
STOP_LOSS_ATR_MULTIPLIER  = 1.5    # SL = entry ± 1.5 × ATR
TAKE_PROFIT_ATR_MULTIPLIER = 2.5   # TP = entry ± 2.5 × ATR
```

#### 7 vérifications séquentielles

```
1. confidence ≥ MIN_CONFIDENCE          (0.50)
2. signal ≠ 0                           (pas NEUTRAL)
3. EV_pips ≥ MIN_EV_PIPS               (≥ 5.0 pips)
4. drawdown ≥ -MAX_DRAWDOWN_PCT         (≥ -15%)
5. current_positions < 4               (max 4 open)
6. RR_ratio ≥ MIN_RR_RATIO             (≥ 1.5)
7. risk_pct ≤ MAX_RISK_PER_TRADE_PCT   (≤ 2%)
```

#### Position Sizing (PositionSizer)

Combinaison de deux méthodes :
1. **Fixed Risk** : `position_size = (capital × risk_pct) / (SL_pips × pip_value)`
2. **Half-Kelly** : `position_size = capital × (Kelly / 2)`

Position finale = `min(fixed_risk, half_kelly)` — conservateur par design.

**Stop-Loss et Take-Profit basés sur ATR** :
```
SL = entry_price ± 1.5 × ATR14
TP = entry_price ± 2.5 × ATR14
→ RR théorique = 2.5/1.5 = 1.67
```

---

### 8.5 XAIFormatter

**Fichier** : `backend/decision_layer/xai_formatter.py`  
**Rôle** : Structuration de la sortie pour l'API et l'interface utilisateur

Génère un output complet avec :
- `agent_breakdown` : Contribution et signal de chaque agent avec poids
- `coordinator_analysis` : Régime marché, conflits, corrélations
- `actuarial_metrics` : EV, P(win), RR, Kelly
- `judge_evaluation` : Verdict, raisonnement, latence
- `risk_assessment` : Violations, position sizing, SL/TP
- `human_explanation` : Texte lisible généré déterministiquement

---

## 9. TradingDecisionPipeline — Orchestrateur Final

**Fichier** : `backend/decision_layer/pipeline.py`

C'est le **point d'entrée unique** pour toute décision de trading.

### Flux complet d'exécution

```
TradingDecisionPipeline.execute(symbol, base, quote, entry_price)
    │
    ├─ Step 1: CoordinatorAgentV2.generate_final_signal()
    │   └─ [4 agents + vote pondéré + corrélations]
    │
    ├─ Step 2: ActuarialScorer.score_trade()
    │   └─ [EV, P(win), RR, Kelly]
    │   └─ [Si EV < 0 → REJET IMMÉDIAT]
    │
    ├─ Step 2.5: LLMToolJudge.analyze()    ← Advisory only (jamais bloquant)
    │   └─ [Ajustement confidence si ≠ 0]
    │
    ├─ Step 3: LLMJudge.evaluate()
    │   └─ APPROVE → continuer
    │   └─ REJECT  → retourner rejection response
    │   └─ MODIFY  → ajuster confidence, continuer
    │
    ├─ Step 4: RiskManager.validate_trade()
    │   └─ approved=True  → continuer
    │   └─ approved=False → retourner rejection response
    │
    └─ Step 5: XAIFormatter.format()
        └─ Retourner décision complète avec position sizing
```

### Output final (trade approuvé)

```python
{
    'status':           'success',
    'decision':         'APPROVED' | 'APPROVED_MODIFIED',
    'signal':           -1 | 0 | 1,
    'signal_name':      'BUY' | 'SELL' | 'NEUTRAL',
    'confidence':       float,
    'symbol':           str,
    'entry_price':      float,
    'position_size':    float,    # En lots
    'stop_loss':        float,    # Prix exact
    'take_profit':      float,    # Prix exact
    'stop_loss_pips':   float,
    'take_profit_pips': float,
    'risk_pct':         float,    # % du capital risqué
    'expected_value_pips': float,
    'probability_win':  float,
    'tool_judge':       dict,     # Advisory metadata
    'xai':              dict,     # Explication structurée complète
    'timestamp':        ISO8601
}
```

---

## 10. Couche de monitoring

**Fichiers** : `backend/monitoring/`

### PerformanceTracker (`performance_tracker.py`)

Suit les performances des agents dans PostgreSQL (`agent_performance_log`).

**Métriques calculées** :
```python
sharpe_ratio = (avg_pnl / std_pnl) × √252   # Annualisé
win_rate     = count(pnl > 0) / total_trades
avg_pnl      = mean(pnl_series)
max_drawdown = min(cumulative_pnl - running_max)
```

**Fenêtres de recherche progressive** (évite les données vides) :
```
30 jours → 90 jours → 365 jours → 10 ans (jusqu'à trouver des données)
```

### SafetyMonitor (`safety_monitor.py`)

Règles de sécurité de production :

| Règle | Valeur | Objectif |
|-------|--------|---------|
| `cooldown_minutes` | 60 min | Évite le sur-trading |
| `max_daily_trades` | 10 | Limite d'exposition journalière |
| `max_drawdown_threshold` | -15% | Circuit breaker d'urgence |

### DriftDetector (`drift_detector.py`)

Détection de **distribution shift** sur les features pour alerter en cas de changement de régime non couvert par les règles.

---

## 11. Flux complet de A à Z

```
DATA ACQUISITION (périodique)
┌─────────────────────────────────────────────────────┐
│ 1. MT5Collector  → OHLCV 1H/4H/1D → InfluxDB        │
│ 2. FREDCollector → Taux/Inflation  → PostgreSQL      │
│ 3. NewsCollector → Articles RSS    → PostgreSQL      │
└─────────────────────────┬───────────────────────────┘
                          │
REQUEST: execute("EURUSD", "EUR", "USD")
                          │
┌─────────────────────────▼───────────────────────────┐
│ DATA LAYER                                          │
│ TimeSeriesLoader : InfluxDB → OHLCV DataFrame       │
│ MacroDataLoader  : PostgreSQL → rates DataFrame     │
│ NewsLoader       : PostgreSQL → news DataFrame      │
└─────────────────────────┬───────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│ FEATURE LAYER                                       │
│ TechnicalFeatureEngine : 85+ indicateurs TA         │
│ MacroFeatureEngine     : rate_diff, carry_score     │
│ SentimentFeatureEngine : score heuristique/LLM      │
│ CrossPairCorrelation   : Pearson sur log-returns    │
└─────────────────────────┬───────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│ SIGNAL LAYER — 4 AGENTS (parallèle conceptuel)      │
│                                                     │
│ TechnicalAgent: RSI+MACD+BB+SMA → signal_T         │
│ MacroAgent:     rate_diff+carry  → signal_M         │
│ SentimentAgent: news weighted    → signal_S         │
│ GeopoliticalAgent: keyword score → signal_G         │
│                                                     │
│ CoordinatorAgentV2:                                 │
│  → Poids dynamiques (Sharpe 30j)                    │
│  → Régime marché (ADX + vol annualisée)             │
│  → Vote pondéré régime-adaptatif                    │
│  → Détection conflits                               │
│  → Validation corrélations inter-paires             │
│  → signal_final, confidence                         │
└─────────────────────────┬───────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│ DECISION LAYER                                      │
│                                                     │
│ [1] ActuarialScorer                                 │
│     EV = P(win)×avg_win - P(loss)×avg_loss          │
│     Si EV < 0 → REJET IMMÉDIAT                      │
│                                                     │
│ [2] LLMToolJudge (advisory, 800ms timeout)          │
│     Ajuste la confiance (COMMENT_ONLY)              │
│                                                     │
│ [3] LLMJudge (Ollama llama3.2:3b, 30s timeout)     │
│     APPROVE / REJECT / MODIFY                       │
│     REJECT → reponse de rejet                       │
│                                                     │
│ [4] RiskManager (veto absolu)                       │
│     7 vérifications: conf, EV, drawdown, DD, RR...  │
│     Calcule: SL/TP/sizing via ATR + Kelly           │
│     REJECT → reponse de rejet                       │
│                                                     │
│ [5] XAIFormatter                                    │
│     Formate l'output complet pour l'API             │
└─────────────────────────┬───────────────────────────┘
                          │
                    API Response (Django REST)
                          │
                    Frontend (Next.js)
```

---

## 12. Matrices de décision et seuils

### Seuils de signal par agent

| Agent | BUY (+1) | NEUTRAL (0) | SELL (-1) |
|-------|----------|-------------|-----------|
| Technical (RSI) | RSI < 30 | 30 ≤ RSI ≤ 70 | RSI > 70 |
| Technical (MACD) | macd_diff > 0 | macd_diff ≈ 0 | macd_diff < 0 |
| Technical (BB) | bb_pos < -0.8 | -0.8 ≤ bb_pos ≤ 0.8 | bb_pos > 0.8 |
| Technical (SMA) | strong_bullish | neutral/weak | strong_bearish |
| Macro | rate_diff > 0.5% | -0.5% ≤ diff ≤ 0.5% | rate_diff < -0.5% |
| Sentiment | sentiment_agg > 0.3 | -0.3 ≤ s ≤ 0.3 | sentiment_agg < -0.3 |
| Geopolitical | risk-on confirmed | ambiguous | risk-off triggered |

### Seuils d'agrégation (Coordinator)

| Paramètre | Seuil | Effet |
|-----------|-------|-------|
| `weighted_score > 0.12` | → BUY | Signal directionnel |
| `weighted_score < -0.12` | → SELL | Signal directionnel |
| `confidence < 0.12` | → Force NEUTRAL | Trop peu de conviction |
| `conflicts = True` | confidence × 0.5 | Pénalité divergence |
| `regime = volatile` | confidence × 0.7 | Pénalité volatilité |
| `correlation aligned` | confidence × 1.15 | Bonus confirmation |
| `correlation conflict` | confidence × 0.75 | Pénalité contradiction |

### Critères de rejet du pipeline complet

| Stade | Critère | Strictness |
|-------|---------|-----------|
| ActuarialScorer | EV < 0 pips | Rejet immédiat |
| LLMJudge (pré-LLM) | confidence < 0.20 | Rejet sans LLM |
| LLMJudge (pré-LLM) | EV < 0.0 pips | Rejet sans LLM |
| LLMJudge (LLM) | Setup incohérent | REJECT |
| RiskManager | confidence < 0.50 | Veto |
| RiskManager | EV_pips < 5.0 | Veto |
| RiskManager | drawdown < -15% | Veto (circuit-breaker) |
| RiskManager | positions ≥ 4 | Veto |
| RiskManager | RR < 1.5 | Veto |
| RiskManager | risk_pct > 2% | Veto |

---

## 13. Technologies et frameworks utilisés

### Backend (Python / Django)

| Technologie | Usage |
|-------------|-------|
| **Django 4.x** | Framework web REST API |
| **Django REST Framework** | Endpoints `/api/v2/signal/`, `/api/v2/decision/` |
| **InfluxDB** (via `influxdb-client`) | Stockage time-series OHLCV |
| **PostgreSQL** (via `psycopg2`) | News, macro data, performance logs |
| **SQLite** | Fallback local pour OHLCV (modèle `OHLCVCandle`) |
| **`ta` library** | 60+ indicateurs techniques (RSI, MACD, BB, ADX…) |
| **pandas / numpy** | Manipulation de données et calculs |
| **MetaTrader5** (Python API) | Collecte de données OHLCV historiques |
| **feedparser** | Parsing RSS multi-sources nouvelles |
| **requests** | HTTP calls (Ollama, NewsAPI, GDELT, GNews) |
| **Ollama** (local) | LLM inference locale (`llama3.2:3b`) |
| **urllib** | Fallback HTTP sans dépendances |

### LLM Infrastructure

| Composant | Modèle | Rôle |
|-----------|--------|------|
| Ollama local | `llama3.2:3b` | LLMJudge + LLMToolJudge |
| Ollama local | `llama3.2:3b` | Explanations (optionnel) |
| Heuristique lexicale | — | Fallback sentiment sans LLM |

### Sources de données externes (gratuites)

| Source | Type | Données |
|--------|------|---------|
| MetaTrader 5 | Price data | OHLCV 1H/4H/1D (4 paires) |
| FRED (Federal Reserve) | Macro | Taux directeurs, inflation |
| GDELT 2.0 | News | Headlines géopolitiques mondiales |
| BBC/CNN/Al Jazeera RSS | News | Actualités mondiales |
| Investing.com RSS | News | Actualités forex |
| FXStreet / DailyFX / ForexLive RSS | News | Analyse forex |
| NewsAPI.org (tier gratuit) | News | 100 requêtes/jour |
| GNews API (tier gratuit) | News | 10 requêtes/jour |

### Architecture de décision — Résumé

```
               DÉTERMINISTE (math pure)
               ─────────────────────
               Feature Engineering (85+ features)
               Règles de signal par agent
               Vote pondéré du Coordinator
               Poids dynamiques (Sharpe)
               Régime de marché (ADX/vol)
               Corrélations inter-paires (Pearson)
               Actuarial Scoring (EV, Kelly)
               Risk Manager (7 vérifications)
               Cooldown / SafetyMonitor

               LLM (Ollama llama3.2:3b) — rôle limité
               ─────────────────────────────────────
               LLMToolJudge : advisory metadata enrichment
               LLMJudge     : gate APPROVE/REJECT/MODIFY
               Explication  : texte en langage naturel uniquement
```

> Le principe fondamental du système est que **le LLM ne génère jamais de signal de trading**. Il agit comme un validateur consultatif (advisory gate) et un générateur d'explications, jamais comme moteur de décision.

---

*Document généré le 20 avril 2026 — FX Alpha Platform v2*
