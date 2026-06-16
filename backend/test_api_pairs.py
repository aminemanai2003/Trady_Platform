import requests, time

for pair in ['EURUSD', 'GBPUSD', 'USDJPY']:
    t0 = time.time()
    r = requests.post('http://127.0.0.1:8000/api/v2/signals/generate_signal/', json={'pair': pair}, timeout=120)
    t1 = time.time()
    d = r.json()
    sig = d.get('signal', {})
    direction = sig.get('direction')
    confidence = sig.get('confidence', 0) * 100
    votes = sig.get('agent_votes', {})
    tech_s = votes.get('technical', {}).get('signal', '?')
    macro_s = votes.get('macro', {}).get('signal', '?')
    sent_s = votes.get('sentiment', {}).get('signal', '?')
    elapsed = t1 - t0
    print(f"{pair}: {direction} ({confidence:.0f}%) [{elapsed:.2f}s] | Tech={tech_s} Macro={macro_s} Sent={sent_s}")
