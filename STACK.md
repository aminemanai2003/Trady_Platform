# FX Alpha Platform — Stack & Pipeline

## Stack Technique

| Couche | Technologie | Intérêt |
|--------|------------|---------|
| **Backend** | Django 5 + DRF | API REST rapide, ORM puissant, admin intégré |
| **Frontend** | Next.js 16 + React 19 | SSR/SSG, routing, performances |
| **UI** | shadcn/ui + Tailwind CSS | Composants accessibles, style utilitaire |
| **Charts** | Recharts | Visualisation de séries temporelles forex |
| **Auth** | NextAuth + Prisma | Sessions sécurisées, ORM TypeScript |
| **Data fetching** | TanStack Query | Cache, synchronisation état serveur/client |
| **BDD relationnelle** | PostgreSQL 15 | Stockage macro, news, signaux, métadonnées |
| **BDD time-series** | InfluxDB 2.7 | Stockage optimal des OHLCV haute fréquence |
| **Cache / Queue** | Redis 7 | Cache API, broker Celery |
| **Task queue** | Celery | Collecte de données asynchrone planifiée |
| **LLM** | HuggingFace `flan-t5-base` | Explications textuelles des signaux (lecture seule) |
| **ML / features** | scikit-learn, pandas, numpy | Feature engineering, 85+ indicateurs |
| **TA** | `ta` library | RSI, MACD, Bollinger, ADX, ATR |
| **NLP** | sentence-transformers | Analyse de sentiment sur les news financières |
| **LangChain / LangGraph** | LangChain + LangGraph | Orchestration multi-agents |
| **Infra** | Docker Compose | Déploiement local reproducible |
| **API Docs** | drf-spectacular | Génération OpenAPI automatique |

---

## Pipeline de A à Z

```
1. ACQUISITION
   MT5 (OHLCV) + FRED (macro) + News API
        │
        ▼
2. STOCKAGE
   InfluxDB ← OHLCV  |  PostgreSQL ← Macro + News + Signaux
        │
        ▼
3. FEATURE ENGINEERING
   60 indicateurs techniques (RSI, MACD, BB, ADX…)
   + 25 features temporelles/macro + corrélations cross-pairs
        │
        ▼
4. AGENTS (signal_layer)
   TechnicalAgentV2 (40%) + MacroAgentV2 (35%) + SentimentAgentV2 (25%)
        │ vote pondéré
        ▼
5. COORDINATOR
   CoordinatorAgentV2 → signal final BUY/SELL/HOLD + confidence score
        │
        ▼
6. LLM EXPLAINABILITY
   flan-t5-base → explication textuelle (jamais décisionnaire)
        │
        ▼
7. MONITORING
   DriftDetector + SafetyMonitor() + PerformanceTracker
        │
        ▼
8. BACKTESTING
   Walk-forward + Kelly Criterion + ATR position sizing
        │
        ▼
9. API REST (DRF)  →  FRONTEND (Next.js)  →  Dashboard UI
```

> **Démarrage :** `docker-compose up -d` puis `python manage.py runserver` (backend :8000) et `npm run dev` (frontend :3000)



safety monitor = Vérifie que le signal ne propose pas un trade trop risqué
Ex: si la confidence est < 50% → bloque le signal
C'est le garde-fou du système

PerformanceTracker 📊
"Est-ce que nos signaux sont bons ou nuls ?"
Calcule le taux de réussite des signaux passés
Suit les métriques : précision, recall, profit/loss
Si les perfs chutent → recalibration du modèle






Étape 8 — BACKTESTING ⏪
"Et si on avait utilisé ce modèle dans le passé, qu'est-ce qui se serait passé ?"

C'est comme rejouer l'histoire pour tester la stratégie.

Walk-forward 🚶
Au lieu de tester une seule fois, on teste fenêtre par fenêtre dans le temps.

Train [Jan-Juin] → Test [Juil]
Train [Jan-Juil] → Test [Août]
Train [Jan-Août] → Test [Sep]
...


Kelly Criterion 💰
"Combien d'argent je mets sur ce trade ?"
Formule mathématique qui calcule la taille optimale de la mise
Si confiance = 90% → mise plus grosse
Si confiance = 51% → mise minimale
Évite de tout perdre sur un seul trade

ATR Position Sizing 📏
"Le marché est agité ? Je réduis ma mise."
ATR = mesure de la volatilité du marché
Si le forex est très volatil → position plus petite pour limiter le risque
Si le marché est calme → position plus grande
