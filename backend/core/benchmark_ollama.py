"""
Ollama Latency Benchmark Script
Tests LLM Judge performance with trading decision prompts
Target: < 500ms for 200-token response
"""
import time
import statistics
from typing import List, Dict
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_tutor.services.ollama_service import generate_answer, _check_ollama_available


def benchmark_ollama(
    model: str = "llama3.2:3b",
    num_runs: int = 10
) -> Dict:
    """
    Benchmark Ollama latency for trading decisions.
    
    Args:
        model: Ollama model to test
        num_runs: Number of test runs
    
    Returns:
        Dict with latency statistics
    """
    print(f"\n{'='*60}")
    print(f"OLLAMA LATENCY BENCHMARK")
    print(f"{'='*60}")
    print(f"Model: {model}")
    print(f"Runs: {num_runs}")
    print(f"Target: < 500ms per decision\n")
    
    # Check if Ollama is available
    if not _check_ollama_available():
        print("❌ ERROR: Ollama is not running at http://localhost:11434")
        print("\nTo fix:")
        print("1. Install Ollama: https://ollama.ai/download")
        print("2. Run: ollama pull llama3.2:3b")
        print("3. Start: ollama serve")
        return {
            'available': False,
            'error': 'Ollama not running'
        }
    
    print("✓ Ollama is running\n")
    
    # Test prompts (realistic trading scenarios)
    test_prompts = [
        # Scenario 1: Approve strong setup
        """You are a risk-averse trading validator reviewing a proposed FX trade.

PROPOSED TRADE:
- Final Signal: BUY
- Confidence: 0.85
- Symbol: EURUSD

AGENT CONSENSUS:
- Technical Agent: BUY (confidence: 0.82)
- Macro Agent: BUY (confidence: 0.78)
- Sentiment Agent: NEUTRAL (confidence: 0.55)

CONFLICTS DETECTED: NO

ACTUARIAL ANALYSIS:
- Expected Value: +22.50 pips
- Probability of Win: 68%
- Risk/Reward Ratio: 1.75

MARKET REGIME: trending

Should this trade be APPROVED, REJECTED, or MODIFIED?

Respond in this EXACT format:
VERDICT: [APPROVE/REJECT/MODIFY]
REASON: [One concise sentence explaining your decision]
CONFIDENCE: [Adjusted confidence 0.0-1.0 if MODIFY, otherwise same]
""",
        
        # Scenario 2: Reject conflicting signals
        """You are a risk-averse trading validator reviewing a proposed FX trade.

PROPOSED TRADE:
- Final Signal: BUY
- Confidence: 0.47
- Symbol: EURUSD

AGENT CONSENSUS:
- Technical Agent: BUY (confidence: 0.78)
- Macro Agent: SELL (confidence: 0.52)
- Sentiment Agent: NEUTRAL (confidence: 0.45)

CONFLICTS DETECTED: YES

ACTUARIAL ANALYSIS:
- Expected Value: +6.58 pips
- Probability of Win: 54%
- Risk/Reward Ratio: 1.20

MARKET REGIME: ranging

Should this trade be APPROVED, REJECTED, or MODIFIED?

Respond in this EXACT format:
VERDICT: [APPROVE/REJECT/MODIFY]
REASON: [One concise sentence explaining your decision]
CONFIDENCE: [Adjusted confidence 0.0-1.0 if MODIFY, otherwise same]
""",
        
        # Scenario 3: Marginal setup
        """You are a risk-averse trading validator reviewing a proposed FX trade.

PROPOSED TRADE:
- Final Signal: SELL
- Confidence: 0.62
- Symbol: GBPUSD

AGENT CONSENSUS:
- Technical Agent: SELL (confidence: 0.68)
- Macro Agent: SELL (confidence: 0.58)
- Sentiment Agent: NEUTRAL (confidence: 0.50)

CONFLICTS DETECTED: NO

ACTUARIAL ANALYSIS:
- Expected Value: +12.30 pips
- Probability of Win: 58%
- Risk/Reward Ratio: 1.55

MARKET REGIME: ranging

Should this trade be APPROVED, REJECTED, or MODIFIED?

Respond in this EXACT format:
VERDICT: [APPROVE/REJECT/MODIFY]
REASON: [One concise sentence explaining your decision]
CONFIDENCE: [Adjusted confidence 0.0-1.0 if MODIFY, otherwise same]
"""
    ]
    
    latencies: List[float] = []
    responses: List[str] = []
    
    print("Running benchmark...")
    print(f"{'Run':<6} {'Latency (ms)':<15} {'Status'}")
    print("-" * 40)
    
    for i in range(num_runs):
        # Rotate through test prompts
        prompt = test_prompts[i % len(test_prompts)]
        
        # Measure latency
        start_time = time.perf_counter()
        
        try:
            response = generate_answer(
                query=prompt,
                top_k=1,
                temperature=0.2
            )
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            latencies.append(latency_ms)
            responses.append(response)
            
            # Check if within target
            status = "✓ PASS" if latency_ms < 500 else "⚠ SLOW"
            
            print(f"{i+1:<6} {latency_ms:<15.1f} {status}")
        
        except Exception as e:
            print(f"{i+1:<6} ERROR: {str(e)}")
            continue
    
    # Calculate statistics
    if not latencies:
        print("\n❌ No successful runs")
        return {
            'available': True,
            'success': False,
            'error': 'All runs failed'
        }
    
    mean_latency = statistics.mean(latencies)
    median_latency = statistics.median(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)
    stdev_latency = statistics.stdev(latencies) if len(latencies) > 1 else 0
    
    # Percentiles
    sorted_latencies = sorted(latencies)
    p50 = sorted_latencies[int(len(sorted_latencies) * 0.50)]
    p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
    p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)] if len(sorted_latencies) > 100 else max_latency
    
    # Pass rate
    pass_count = sum(1 for lat in latencies if lat < 500)
    pass_rate = (pass_count / len(latencies)) * 100
    
    # Print results
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}")
    print(f"Total runs:        {len(latencies)}")
    print(f"Successful:        {len(latencies)}")
    print(f"Pass rate (<500ms): {pass_rate:.1f}% ({pass_count}/{len(latencies)})")
    print(f"\nLATENCY STATISTICS (ms):")
    print(f"  Mean:            {mean_latency:.1f} ms")
    print(f"  Median:          {median_latency:.1f} ms")
    print(f"  Std Dev:         {stdev_latency:.1f} ms")
    print(f"  Min:             {min_latency:.1f} ms")
    print(f"  Max:             {max_latency:.1f} ms")
    print(f"\nPERCENTILES:")
    print(f"  P50:             {p50:.1f} ms")
    print(f"  P95:             {p95:.1f} ms")
    print(f"  P99:             {p99:.1f} ms")
    
    # Assessment
    print(f"\n{'='*60}")
    print("ASSESSMENT")
    print(f"{'='*60}")
    
    if mean_latency < 300:
        print("✓ EXCELLENT: Well below 500ms target")
        print("  Recommendation: Safe for real-time trading (1H+ timeframes)")
    elif mean_latency < 500:
        print("✓ GOOD: Within 500ms target")
        print("  Recommendation: Suitable for 4H/Daily timeframes")
    elif mean_latency < 800:
        print("⚠ ACCEPTABLE: Above target but usable")
        print("  Recommendation: Consider GPU acceleration or smaller model")
    else:
        print("❌ TOO SLOW: Exceeds acceptable latency")
        print("  Recommendation: Enable GPU or switch to phi-3:mini")
    
    # Sample response check
    print(f"\n{'='*60}")
    print("SAMPLE RESPONSE (Run 1)")
    print(f"{'='*60}")
    if responses:
        print(responses[0][:300] + "..." if len(responses[0]) > 300 else responses[0])
    
    return {
        'available': True,
        'success': True,
        'model': model,
        'num_runs': len(latencies),
        'pass_rate': pass_rate,
        'mean_latency_ms': mean_latency,
        'median_latency_ms': median_latency,
        'min_latency_ms': min_latency,
        'max_latency_ms': max_latency,
        'stdev_latency_ms': stdev_latency,
        'p50_ms': p50,
        'p95_ms': p95,
        'p99_ms': p99,
        'target_met': mean_latency < 500
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Benchmark Ollama latency for trading decisions')
    parser.add_argument('--model', default='llama3.2:3b', help='Ollama model to test')
    parser.add_argument('--runs', type=int, default=10, help='Number of test runs')
    
    args = parser.parse_args()
    
    results = benchmark_ollama(model=args.model, num_runs=args.runs)
    
    # Exit code based on results
    if results.get('success') and results.get('target_met'):
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure
