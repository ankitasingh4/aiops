"""
Threshold Problems Demonstration
=================================
This script demonstrates WHY static thresholds fail
by analyzing real Prometheus data and showing false positives/negatives.

Usage:
    python threshold_problems.py
"""

import sys
import time
from datetime import datetime, timedelta

try:
    from prometheus_api_client import PrometheusConnect
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
except ImportError:
    print("Please install: pip install prometheus-api-client pandas numpy matplotlib")
    sys.exit(1)

prom = PrometheusConnect(url="http://localhost:9090", disable_ssl=True)

print("=" * 70)
print("  WHY STATIC THRESHOLDS FAIL - A Demonstration")
print("=" * 70)


# =============================================================================
# PROBLEM 1: Context-blind thresholds
# =============================================================================
print("\n" + "─" * 70)
print("PROBLEM 1: Thresholds don't understand CONTEXT")
print("─" * 70)

# Get CPU data
end_time = datetime.now()
start_time = end_time - timedelta(minutes=60)

result = prom.custom_query_range(
    query='app_cpu_usage_percent',
    start_time=start_time,
    end_time=end_time,
    step='15s'
)

if result and result[0]['values']:
    values = [float(v[1]) for v in result[0]['values']]
    timestamps = [datetime.fromtimestamp(float(v[0])) for v in result[0]['values']]
    df = pd.DataFrame({'time': timestamps, 'cpu': values})

    threshold = 70  # A typical static threshold

    # Count threshold violations
    violations = df[df['cpu'] > threshold]
    print(f"\n  Static threshold: CPU > {threshold}%")
    print(f"  Total data points: {len(df)}")
    print(f"  Threshold violations: {len(violations)} ({len(violations)/len(df)*100:.1f}%)")
    print(f"\n  But are ALL these actually problems? NO!")
    print(f"  Our app has a sinusoidal pattern - high CPU during 'peak hours' is NORMAL.")
    print(f"  A static threshold can't distinguish expected peaks from real issues.")

    # Show the pattern
    plt.figure(figsize=(14, 6))
    plt.subplot(2, 1, 1)
    plt.plot(df['time'], df['cpu'], 'b-', linewidth=0.8, label='CPU %')
    plt.axhline(y=threshold, color='r', linestyle='--', linewidth=2,
                label=f'Static Threshold ({threshold}%)')
    plt.fill_between(df['time'], threshold, df['cpu'],
                     where=(df['cpu'] > threshold), alpha=0.3, color='red',
                     label='False Positives')
    plt.title('Problem 1: Static Threshold → Many False Positives')
    plt.ylabel('CPU %')
    plt.legend()

    # BETTER: Dynamic threshold based on rolling statistics
    plt.subplot(2, 1, 2)
    window = min(20, len(df) // 4)  # Rolling window
    if window > 1:
        rolling_mean = df['cpu'].rolling(window=window, center=True).mean()
        rolling_std = df['cpu'].rolling(window=window, center=True).std()
        upper_band = rolling_mean + 2 * rolling_std
        lower_band = rolling_mean - 2 * rolling_std

        plt.plot(df['time'], df['cpu'], 'b-', linewidth=0.8, label='CPU %')
        plt.plot(df['time'], rolling_mean, 'g-', linewidth=1.5, label='Rolling Mean')
        plt.fill_between(df['time'], lower_band, upper_band, alpha=0.2, color='green',
                         label='Dynamic ±2σ Band')

        # Real anomalies: outside the dynamic band
        anomalies = df[(df['cpu'] > upper_band) | (df['cpu'] < lower_band)]
        if len(anomalies) > 0:
            plt.scatter(anomalies['time'], anomalies['cpu'], color='red', s=50,
                        zorder=5, label=f'True Anomalies ({len(anomalies)})')

    plt.title('Better: Dynamic Band → Fewer, More Meaningful Alerts')
    plt.ylabel('CPU %')
    plt.xlabel('Time')
    plt.legend()
    plt.tight_layout()
    plt.savefig('threshold_problems.png', dpi=100)
    print(f"\n  📊 Chart saved to: threshold_problems.png")
else:
    print("\n  ⚠️  No data yet. Run for a few minutes and try again.")


# =============================================================================
# PROBLEM 2: Missing slow degradation
# =============================================================================
print("\n" + "─" * 70)
print("PROBLEM 2: Static thresholds MISS gradual degradation")
print("─" * 70)

# Simulate a slowly degrading metric
print("""
  Imagine response time slowly increasing:
  
  Day 1:  avg = 100ms   (Threshold: 500ms → no alert)
  Day 5:  avg = 180ms   (Threshold: 500ms → no alert)
  Day 10: avg = 280ms   (Threshold: 500ms → no alert)
  Day 15: avg = 390ms   (Threshold: 500ms → no alert)
  Day 18: avg = 480ms   (Threshold: 500ms → no alert)
  Day 19: avg = 520ms   (Threshold: 500ms → 🚨 ALERT! Too late!)
  
  By the time the threshold fires, users have been suffering for WEEKS.
  
  What we SHOULD detect:
  - The RATE OF CHANGE (trend) is alarming from Day 1
  - ML can detect: "this metric is increasing 20ms/day, will breach in 20 days"
""")


# =============================================================================
# PROBLEM 3: Alert fatigue simulation
# =============================================================================
print("\n" + "─" * 70)
print("PROBLEM 3: Alert fatigue from flapping")
print("─" * 70)

if result and result[0]['values']:
    # Simulate a tight threshold that causes flapping
    tight_threshold = df['cpu'].mean() + 0.5 * df['cpu'].std()

    # Count how many times it crosses the threshold
    above = df['cpu'] > tight_threshold
    crossings = (above != above.shift()).sum()

    print(f"\n  Tight threshold: CPU > {tight_threshold:.1f}%")
    print(f"  Threshold crossings in 1 hour: {crossings}")
    print(f"  That's ~{crossings} potential alert state changes!")
    print(f"\n  If each crossing fires an alert → engineer gets {crossings//2} alerts/hour")
    print(f"  In a day: ~{crossings//2 * 24} alerts")
    print(f"  Result: Engineer IGNORES alerts → misses real problems")
    print(f"\n  ML-based approach: Understand that oscillation IS the normal pattern")
    print(f"  and only alert when the pattern ITSELF changes.")


# =============================================================================
# PROBLEM 4: One threshold doesn't fit all times
# =============================================================================
print("\n" + "─" * 70)
print("PROBLEM 4: Seasonality makes single thresholds impossible")
print("─" * 70)

print("""
  Our simulated app has a day/night pattern (compressed to minutes):
  
  "Day" period:   CPU: 40-70%  (normal peak = 65%)
  "Night" period: CPU: 15-40%  (normal peak = 35%)
  
  If threshold = 60%:
    → Day: Never alerts (peak is "normal") 
    → Night: A spike to 50% doesn't alert but IS anomalous for night!
    
  If threshold = 40%:
    → Day: Constant false alarms
    → Night: Catches real issues
    
  SOLUTION: AI learns separate patterns for different time periods.
  This is exactly what we'll build in Topics 4 and 5.
""")


# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("  SUMMARY: What We Need Beyond Static Thresholds")
print("=" * 70)
print("""
  ┌─────────────────────────────────────────────────────────────────┐
  │                                                                  │
  │  1. DYNAMIC BASELINES    - Learn what "normal" looks like        │
  │  2. SEASONALITY AWARE    - Different expectations per time       │
  │  3. TREND DETECTION      - Catch slow degradation early          │
  │  4. SMART SUPPRESSION    - Reduce noise, highlight real issues   │
  │  5. PREDICTIVE ALERTS    - Warn BEFORE problems occur            │
  │                                                                  │
  │  All of this → Topics 4 (Anomaly Detection) & 5 (Forecasting)   │
  │                                                                  │
  └─────────────────────────────────────────────────────────────────┘
""")
