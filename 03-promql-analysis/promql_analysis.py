"""
PromQL Analysis via Python
===========================
This script demonstrates how to query Prometheus programmatically
and analyze the results using pandas.

Prerequisites:
    pip install prometheus-api-client pandas matplotlib

Usage:
    python promql_analysis.py

Make sure Prometheus is running at http://localhost:9090
"""

import sys
import time
from datetime import datetime, timedelta

try:
    from prometheus_api_client import PrometheusConnect
    import pandas as pd
    import matplotlib.pyplot as plt
except ImportError:
    print("Please install dependencies:")
    print("  pip install prometheus-api-client pandas matplotlib")
    sys.exit(1)

# Connect to Prometheus
prom = PrometheusConnect(url="http://localhost:9090", disable_ssl=True)

print("=" * 70)
print("  PromQL Analysis - Querying Prometheus from Python")
print("=" * 70)


# =============================================================================
# 1. INSTANT QUERY - Current values
# =============================================================================
print("\n" + "─" * 70)
print("1. INSTANT QUERY: Current request rate")
print("─" * 70)

result = prom.custom_query(
    query='sum by(endpoint) (rate(http_requests_total[5m]))'
)

print("\nEndpoint request rates (req/sec):")
for series in result:
    endpoint = series['metric'].get('endpoint', 'unknown')
    value = float(series['value'][1])
    print(f"  {endpoint:20s} → {value:.4f} req/s")


# =============================================================================
# 2. RANGE QUERY - Values over time
# =============================================================================
print("\n" + "─" * 70)
print("2. RANGE QUERY: CPU usage over last 30 minutes")
print("─" * 70)

end_time = datetime.now()
start_time = end_time - timedelta(minutes=30)

result = prom.custom_query_range(
    query='app_cpu_usage_percent',
    start_time=start_time,
    end_time=end_time,
    step='60s'
)

if result:
    values = [float(v[1]) for v in result[0]['values']]
    timestamps = [datetime.fromtimestamp(float(v[0])) for v in result[0]['values']]

    df = pd.DataFrame({'timestamp': timestamps, 'cpu_percent': values})
    print(f"\n  Data points: {len(df)}")
    print(f"  Mean CPU: {df['cpu_percent'].mean():.2f}%")
    print(f"  Max CPU: {df['cpu_percent'].max():.2f}%")
    print(f"  Min CPU: {df['cpu_percent'].min():.2f}%")
    print(f"  Std Dev: {df['cpu_percent'].std():.2f}%")

    # Save a plot
    plt.figure(figsize=(12, 4))
    plt.plot(df['timestamp'], df['cpu_percent'], 'b-', linewidth=0.8)
    plt.axhline(y=df['cpu_percent'].mean(), color='g', linestyle='--', label='Mean')
    plt.axhline(y=80, color='r', linestyle='--', label='Static Threshold (80%)')
    plt.fill_between(
        df['timestamp'],
        df['cpu_percent'].mean() - 2 * df['cpu_percent'].std(),
        df['cpu_percent'].mean() + 2 * df['cpu_percent'].std(),
        alpha=0.2, color='green', label='±2σ (dynamic range)'
    )
    plt.title('CPU Usage: Static Threshold vs Dynamic Range')
    plt.xlabel('Time')
    plt.ylabel('CPU %')
    plt.legend()
    plt.tight_layout()
    plt.savefig('cpu_analysis.png', dpi=100)
    print("\n  📊 Chart saved to: cpu_analysis.png")
else:
    print("  No data available yet. Let the app run for a few minutes first.")


# =============================================================================
# 3. ERROR RATE ANALYSIS
# =============================================================================
print("\n" + "─" * 70)
print("3. ERROR RATE: Calculating from counters")
print("─" * 70)

error_query = '''
  sum(rate(http_requests_total{status=~"5.."}[5m])) 
  / 
  sum(rate(http_requests_total[5m])) * 100
'''

result = prom.custom_query(query=error_query)
if result:
    error_rate = float(result[0]['value'][1])
    print(f"\n  Current error rate: {error_rate:.2f}%")
    print(f"  Status: {'⚠️  ELEVATED' if error_rate > 5 else '✅ Normal'}")
else:
    print("  No request data yet.")


# =============================================================================
# 4. LATENCY PERCENTILES
# =============================================================================
print("\n" + "─" * 70)
print("4. LATENCY PERCENTILES: Understanding response time distribution")
print("─" * 70)

percentiles = [0.50, 0.90, 0.95, 0.99]
print("\n  Percentile │ Latency")
print("  ───────────┼──────────")

for p in percentiles:
    query = f'histogram_quantile({p}, rate(http_request_duration_seconds_bucket[5m]))'
    result = prom.custom_query(query=query)
    if result:
        latency = float(result[0]['value'][1])
        bar = '█' * int(latency * 20)
        print(f"  p{int(p*100):>2}       │ {latency:.3f}s  {bar}")


# =============================================================================
# 5. PREDICT_LINEAR - Built-in simple forecasting
# =============================================================================
print("\n" + "─" * 70)
print("5. PREDICT_LINEAR: Prometheus's built-in (limited) forecasting")
print("─" * 70)

# Predict memory in 1 hour based on last 30 min trend
query = 'predict_linear(app_memory_usage_bytes[30m], 3600)'
result = prom.custom_query(query=query)
if result:
    predicted_mb = float(result[0]['value'][1]) / (1024 * 1024)
    print(f"\n  Predicted memory in 1 hour: {predicted_mb:.0f} MB")
    print(f"  ⚠️  This is LINEAR extrapolation only!")
    print(f"     It doesn't account for GC cycles, seasonality, or trends.")
    print(f"     We'll do much better with ML in Topic 5.")


print("\n" + "=" * 70)
print("  Analysis Complete! Check the generated charts.")
print("=" * 70)
