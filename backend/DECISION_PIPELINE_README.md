# FX Trading System - Decision Pipeline Upgrade

## Vue d'ensemble

Système de trading FX amélioré avec **LLM Judge**, **Risk Management**, et **Explainability (XAI)**.

### Architecture avant/après

**AVANT (V2 basique)**:
```
CoordinatorAgentV2 → API Response
```

**APRÈS (V2 + Pipeline)**:
```
CoordinatorAgentV2 
    ↓
ActuarialScorer (EV, P(win), RR)
    ↓
LLM Judge (Ollama, APPROVE/REJECT)
    ↓
RiskManager (veto absolu)
    ↓
XAI Formatter (explication structurée)
    ↓
API Response
```

---

## Composants nouveaux

### 1. **ActuarialScorer** (`backend/decision_layer/actuarial_scorer.py`)
- Calcule **Expected Value**: `EV = P(win) × avg_win - P(loss) × avg_loss`
- Estime **P(win)** depuis la confiance + historique
- Ratio **Risk/Reward**: TP/SL >= 1.5
- Bloque si EV < 0

### 2. **LLM Judge** (`backend/decision_layer/llm_judge.py`)
- **Ollama local** (llama3.2:3b)
- Rejette:
  - Signaux conflictuels
  - Confiance < 0.5
  - EV négatif
  - Setup incohérent
- **Latence cible**: < 500ms
- **Cache** pour décisions identiques

### 3. **RiskManager** (`backend/risk/risk_manager.py`)
- **Veto absolu** (peut bloquer trade approuvé par Judge)
- Limites configurables:
  - Max risque/trade: 2% du capital
  - Max drawdown: -15%
  - Min RR ratio: 1.5
  - Max positions simultanées: 4
- Position sizing: Kelly + ATR

### 4. **XAI Formatter** (`backend/decision_layer/xai_formatter.py`)
- Sortie structurée:
  - Contribution par agent
  - Top features
  - Métriques actuarielles
  - Raison du Judge
  - Analyse de risque
  - Explication humaine

### 5. **TradingDecisionPipeline** (`backend/decision_layer/pipeline.py`)
- Orchestrateur principal
- Gère le flux complet
- Tracking equity/drawdown
- Emergency stop

---

## Installation

### 1. Installer Ollama

```bash
# Windows/Mac/Linux
curl https://ollama.ai/install.sh | sh

# Pull le modèle
ollama pull llama3.2:3b

# Démarrer Ollama
ollama serve
```

### 2. Vérifier la latence

```bash
cd fx-alpha-platform/backend
python core/benchmark_ollama.py --runs 10
```

**Résultat attendu**: Latence moyenne < 500ms

---

## Utilisation

### API Endpoint (nouvelle version)

**POST** `/api/v2/signals-enhanced/generate_with_pipeline/`

```json
{
  "pair": "EURUSD",
  "capital": 10000.0,
  "current_equity": 10200.0,
  "peak_equity": 10500.0,
  "current_positions": 2
}
```

**Réponse (Trade approuvé)**:
```json
{
  "success": true,
  "decision": "APPROVED",
  "signal": {
    "direction": "BUY",
    "signal_value": 1,
    "confidence": 0.85,
    "symbol": "EURUSD"
  },
  "execution_plan": {
    "entry_price": 1.1000,
    "position_size": 0.57,
    "stop_loss": 1.0965,
    "take_profit": 1.1023,
    "stop_loss_pips": 35,
    "take_profit_pips": 58,
    "risk_pct": 1.8
  },
  "expected_outcome": {
    "expected_value_pips": 22.5,
    "probability_win": 0.68
  },
  "xai": {
    "decision": "APPROVED",
    "agent_breakdown": {...},
    "actuarial_metrics": {...},
    "judge_evaluation": {...},
    "risk_assessment": {...},
    "human_explanation": {
      "summary": "Trade APPROVED: BUY EURUSD with 85% confidence.",
      "details": "Primary driver: Technical Agent (BUY, 82% confidence, 40% weight)...",
      "recommendation": "Execute BUY trade as planned."
    }
  }
}
```

**Réponse (Trade rejeté)**:
```json
{
  "success": true,
  "decision": "REJECTED",
  "signal": {
    "direction": "BUY",
    "signal_value": 1,
    "confidence": 0.47,
    "symbol": "EURUSD"
  },
  "rejection": {
    "stage": "LLM_JUDGE",
    "reason": "LLM Judge: Conflicting signals with low confidence below threshold"
  },
  "xai": {
    "decision": "REJECTED",
    "rejection_stage": "LLM_JUDGE",
    "rejection_reason": "Conflicting agent signals + low confidence (0.47) + ranging market",
    "human_explanation": {
      "summary": "Trade REJECTED: EUR/USD buy signal declined due to conflicting agent opinions and low confidence.",
      "details": "While technical indicators show oversold conditions...",
      "recommendation": "NO TRADE - Wait for technical and macro alignment"
    }
  }
}
```

---

## Tests

### Tests unitaires

```bash
cd fx-alpha-platform/backend
python -m pytest tests/test_decision_layer.py -v
```

**Tests couverts**:
- ✅ ActuarialScorer: EV, P(win), RR calculations
- ✅ RiskManager: Validation, rejections, limites
- ✅ PositionSizer: Kelly, ATR, combined sizing
- ✅ LLMJudge: Quick rejections, parsing
- ✅ XAIFormatter: Structure output

### Test d'intégration

```python
from decision_layer.pipeline import TradingDecisionPipeline

# Créer pipeline
pipeline = TradingDecisionPipeline(initial_capital=10000.0)

# Exécuter décision
result = pipeline.execute(
    symbol='EURUSD',
    base_currency='EUR',
    quote_currency='USD'
)

print(result['decision'])  # 'APPROVED' ou 'REJECTED'
print(result['xai']['human_explanation']['summary'])
```

---

## Configuration

### Paramètres de risque (Django settings)

```python
# config/settings.py

# Risk Management Configuration
MAX_RISK_PER_TRADE_PCT = 2.0  # Max 2% capital per trade
MAX_DRAWDOWN_PCT = 15.0        # Emergency stop at -15%
MIN_RR_RATIO = 1.5             # Minimum risk/reward
MAX_CONCURRENT_POSITIONS = 4   # Max 4 pairs open
MIN_CONFIDENCE = 0.50          # Reject if < 50%
MIN_EV_PIPS = 5.0              # Reject if EV < 5 pips
STOP_LOSS_ATR_MULTIPLIER = 1.5  # SL = 1.5 × ATR
TAKE_PROFIT_ATR_MULTIPLIER = 2.5  # TP = 2.5 × ATR
```

---

## Flux de décision détaillé

```
1. API Request: POST /api/v2/signals-enhanced/generate_with_pipeline/
        ↓
2. CoordinatorAgentV2:
   - TechnicalV2: BUY 0.78
   - MacroV2: BUY 0.68
   - SentimentV2: NEUTRAL 0.45
   → Agrégation pondérée → BUY 0.82
        ↓
3. ActuarialScorer:
   - EV = +22.5 pips ✅
   - P(win) = 68%
   - RR = 1.75
        ↓
4. LLM Judge (420ms):
   - Prompt: Tous les signaux + contexte
   - LLM (Ollama): "VERDICT: APPROVE | REASON: Strong setup..."
   → APPROVE ✅
        ↓
5. RiskManager:
   - Confiance: 0.82 > 0.50 ✅
   - EV: 22.5 > 5.0 ✅
   - Drawdown: -8% > -15% ✅
   - Positions: 2 < 4 ✅
   - Position size: 0.57 lots
   → APPROVE ✅
        ↓
6. XAIFormatter:
   - Structure explication complète
   - Agent breakdown, metrics, human text
        ↓
7. API Response: APPROVED with full XAI
```

---

## Métriques de performance

### Latence attendue

| Composant | Latence cible | Latence typique |
|-----------|--------------|-----------------|
| CoordinatorAgentV2 | < 300ms | ~150ms |
| ActuarialScorer | < 50ms | ~10ms |
| LLM Judge | < 500ms | ~350-450ms |
| RiskManager | < 50ms | ~5ms |
| XAIFormatter | < 50ms | ~10ms |
| **Total Pipeline** | **< 1000ms** | **~550ms** |

### Taux de rejet attendu

- **Avant (V2 seul)**: ~10-15% rejetés (conflits uniquement)
- **Après (V2 + Pipeline)**: ~30-50% rejetés (filtrage strict)

### Critères de rejet

| Critère | Occurrences attendues |
|---------|----------------------|
| Conflits agents | 15-20% |
| Confiance < 0.50 | 10-15% |
| EV négatif | 5-10% |
| Limites de risque | 5-10% |
| Max drawdown | 2-5% (rare) |

---

## Monitoring

### Status de risque

**GET** `/api/v2/signals-enhanced/risk_status/`

```json
{
  "risk_status": {
    "max_risk_per_trade_usd": 200.0,
    "drawdown_current_pct": -8.2,
    "drawdown_remaining_pct": 6.8,
    "positions_current": 2,
    "positions_remaining": 2,
    "can_trade": true
  },
  "emergency_stop": {
    "emergency_stop": false,
    "reason": "Within limits: Drawdown -8.2%",
    "drawdown_pct": -8.2,
    "threshold": -15.0
  }
}
```

### Update equity

**POST** `/api/v2/signals-enhanced/update_equity/`

```json
{
  "current_equity": 10200.0,
  "current_positions": 2
}
```

---

## Troubleshooting

### Ollama non disponible

```
❌ ERROR: Ollama is not running at http://localhost:11434

Fix:
1. ollama serve
2. Vérifier http://localhost:11434
3. Relancer benchmark
```

**Fallback**: Si Ollama non disponible, le Judge utilise des règles déterministes.

### Latence > 500ms

```
⚠ WARNING: LLM Judge latency 820ms > 500ms target

Solutions:
1. Activer GPU: OLLAMA_GPU_LAYERS=99 ollama serve
2. Modèle plus petit: ollama pull phi-3:mini
3. Augmenter timeout (non recommandé)
```

### Taux de rejet trop élevé

Si >60% des trades sont rejetés:

1. Vérifier les limites de risque (peut-être trop strictes)
2. Analyser les raisons de rejet dans les logs
3. Ajuster `MIN_CONFIDENCE` ou `MIN_EV_PIPS`

---

## Prochaines étapes

### Phase 2 (optionnel)

1. **Multi-timeframe Judge**: Analyser 4H + Daily
2. **Position hedging**: Limiter corrélations négatives
3. **Adaptive risk**: Réduire limites en haute volatilité
4. **Judge calibration**: Tracker rejections vs résultats

### Phase 3 (avancé)

1. **WebSocket real-time** (si migration vers < 1H timeframes)
2. **Reinforcement learning** pour poids agents
3. **Backtesting comparatif** (V2 vs V2+Pipeline)

---

## Documentation API complète

Voir `/api/v2/docs/` pour la documentation Swagger interactive.

**Endpoints disponibles**:
- `POST /api/v2/signals-enhanced/generate_with_pipeline/` - Décision complète
- `GET /api/v2/signals-enhanced/risk_status/` - Status de risque
- `POST /api/v2/signals-enhanced/update_equity/` - Update equity
- `POST /api/v2/signals/generate_signal/` - V2 basique (sans pipeline)

---

## License

Propriétaire - FX Alpha Platform

## Contact

Pour questions ou support: [votre contact]
