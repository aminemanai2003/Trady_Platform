"""Full pipeline verification with timing."""
import os, sys, time, json, warnings
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
sys.path.insert(0, os.path.dirname(__file__))
import django; django.setup()
warnings.filterwarnings('ignore')

print('='*60)
print('FULL PIPELINE VERIFICATION')
print('='*60)

# 1. Verify data sources
print('\n--- 1. DATA SOURCES ---')
t0 = time.time()
from data_layer.timeseries_loader import TimeSeriesLoader
ts = TimeSeriesLoader()
ohlcv = ts.load_ohlcv('EURUSD')
t1 = time.time()
print(f'OHLCV: {len(ohlcv)} rows (InfluxDB) [{t1-t0:.2f}s]')
ts_col = ohlcv['timestamp']
print(f'  Date range: {ts_col.min()} -> {ts_col.max()}')
print(f'  Columns: {list(ohlcv.columns)}')
print(f'  Last close: {ohlcv.iloc[-1]["close"]:.5f}')

t0 = time.time()
from data_layer.macro_loader import MacroDataLoader
ml = MacroDataLoader()
rates = ml.load_interest_rates(['EUR', 'USD'])
inflation = ml.load_inflation_rates(['EUR', 'USD'])
t1 = time.time()
print(f'Macro rates: {len(rates)} rows, inflation: {len(inflation)} rows (PostgreSQL) [{t1-t0:.2f}s]')

t0 = time.time()
from data_layer.news_loader import NewsLoader
nl = NewsLoader()
news = nl.load_news(currencies=['EUR', 'USD'])
t1 = time.time()
print(f'News: {len(news)} articles (PostgreSQL) [{t1-t0:.2f}s]')
scored = sum(1 for _, row in news.iterrows() if row.get('sentiment_score') is not None)
print(f'  Pre-scored: {scored}/{len(news)} (these skip LLM)')

# 2. Verify feature calculation
print('\n--- 2. FEATURE ENGINES ---')
t0 = time.time()
from feature_layer.technical_features import TechnicalFeatureEngine
tfe = TechnicalFeatureEngine()
df_feat = tfe.calculate_all(ohlcv)
indicators = tfe.get_current_values(df_feat)
t1 = time.time()
print(f'Technical features: {len(indicators)} indicators [{t1-t0:.2f}s]')
for k, v in indicators.items():
    print(f'  {k}: {v}')

t0 = time.time()
from feature_layer.macro_features import MacroFeatureEngine
mfe = MacroFeatureEngine()
rate_diff = mfe.calculate_rate_differentials(rates, 'EUR', 'USD')
infl_diff = mfe.calculate_inflation_differential(inflation, 'EUR', 'USD')
t1 = time.time()
print(f'Macro features: rate_diff={rate_diff:.3f}, infl_diff={infl_diff:.3f} [{t1-t0:.2f}s]')

# 3. Verify agents
print('\n--- 3. AGENT SIGNALS ---')
signal_map = {1: 'BUY', 0: 'NEUTRAL', -1: 'SELL'}

t0 = time.time()
from signal_layer.technical_agent_v2 import TechnicalAgentV2
tech = TechnicalAgentV2()
tech_sig = tech.generate_signal('EURUSD')
t1 = time.time()
print(f'Technical: {signal_map[tech_sig["signal"]]} conf={tech_sig["confidence"]:.2f} [{t1-t0:.2f}s]')
print(f'  Reason: {tech_sig["deterministic_reason"]}')

t0 = time.time()
from signal_layer.macro_agent_v2 import MacroAgentV2
macro = MacroAgentV2()
macro_sig = macro.generate_signal('EUR', 'USD', 0.01)
t1 = time.time()
print(f'Macro: {signal_map[macro_sig["signal"]]} conf={macro_sig["confidence"]:.2f} [{t1-t0:.2f}s]')
print(f'  Reason: {macro_sig["deterministic_reason"]}')

t0 = time.time()
from signal_layer.sentiment_agent_v2 import SentimentAgentV2
sent = SentimentAgentV2()
sent_sig = sent.generate_signal(['EUR', 'USD'])
t1 = time.time()
print(f'Sentiment: {signal_map[sent_sig["signal"]]} conf={sent_sig["confidence"]:.2f} [{t1-t0:.2f}s]')
print(f'  Reason: {sent_sig["deterministic_reason"]}')

# 4. Full coordinator
print('\n--- 4. COORDINATOR (FULL PIPELINE) ---')
t0 = time.time()
from signal_layer.coordinator_agent_v2 import CoordinatorAgentV2
coord = CoordinatorAgentV2()
result = coord.generate_final_signal('EURUSD', 'EUR', 'USD')
t1 = time.time()
print(f'Final: {signal_map[result["final_signal"]]} conf={result["confidence"]:.2f} [{t1-t0:.2f}s]')
print(f'  Regime: {result["market_regime"]}')
print(f'  Conflicts: {result["conflicts_detected"]}')

# 5. API endpoint
print('\n--- 5. HTTP API TEST ---')
import requests
t0 = time.time()
r = requests.post('http://127.0.0.1:8000/api/v2/signals/generate_signal/', json={'pair': 'EURUSD'}, timeout=120)
t1 = time.time()
d = r.json()
print(f'HTTP Status: {r.status_code} [{t1-t0:.2f}s]')
sig = d.get('signal', {})
print(f'Direction: {sig.get("direction")}')
print(f'Confidence: {sig.get("confidence", 0)*100:.1f}%')
votes = sig.get('agent_votes', {})
for agent, v in votes.items():
    print(f'  {agent}: {v.get("signal")} ({v.get("confidence", 0)*100:.0f}%)')

print('\n' + '='*60)
print('VERIFICATION COMPLETE - All components real, no mocks')
print('='*60)
