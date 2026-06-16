"""E2E test after yfinance 1h data ingestion."""
import requests, time, json

def test(pair):
    start = time.time()
    r = requests.post(
        "http://localhost:8000/api/v2/master/generate/",
        json={"pair": pair},
        timeout=60,
    )
    elapsed = time.time() - start
    d = r.json()

    sig   = d.get("signal") or {}
    tj    = d.get("tool_judge") or {}
    judge = d.get("judge") or {}
    act   = d.get("actuarial") or {}
    rej   = d.get("rejection") or {}

    print(f"\n{'='*56}")
    print(f"  {pair}  |  HTTP {r.status_code}  |  {elapsed:.1f}s")
    print(f"{'='*56}")
    print(f"  Decision   : {d.get('decision')}")
    print(f"  Signal     : {sig.get('direction')}  conf={sig.get('confidence', 0):.3f}")
    print(f"  EV (pips)  : {act.get('expected_value_pips', 0):.2f}")
    print(f"  P(win)     : {act.get('probability_win', 0):.1%}")
    print(f"  Judge      : {judge.get('verdict')} — {judge.get('reasoning', '')[:80]}")
    print(f"  ToolJudge  : {tj.get('verdict')} | flags={tj.get('risk_flags')}")
    if rej.get("reason"):
        print(f"  Rejected   : {rej.get('reason')[:100]}")
    if d.get("decision") == "APPROVED":
        ep = d.get("execution_plan") or {}
        print(f"  Entry      : {ep.get('entry_price')}")
        print(f"  SL / TP    : {ep.get('stop_loss')} / {ep.get('take_profit')}")
        print(f"  Size       : {ep.get('position_size')}")

pairs = ["EURUSD", "GBPUSD", "USDJPY"]
for p in pairs:
    try:
        test(p)
    except Exception as e:
        print(f"[{p}] ERROR: {e}")

print("\nDone.")
