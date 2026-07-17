"""
Isolation Forest Anomaly Detection
====================================
Isolation Forest is an unsupervised ML algorithm specifically designed
for anomaly detection. It works on the principle that:

  "Anomalies are few and different — they're easier to ISOLATE"

The algorithm builds random trees. Anomalies need fewer splits to isolate,
so they have shorter path lengths in the trees.

Advantages over statistical methods:
- No assumption about data distribution
- Works with multiple dimensions (multi-metric)
- Handles non-linear relationships
- Computationally efficient

Usage:
    python isolation_forest_detector.py
"""

import sys
from datetime import datetime, timedelta

try:
    from prometheus_api_client import PrometheusConnect
    import pandas as pd
    import numpy as np
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    import matplotlib.pyplot as plt
except ImportError:
    print("Install: pip install prometheus-api-client pandas numpy scikit-learn matplotlib")
    sys.exit(1)

prom = PrometheusConnect(url="http://localhost:9090", disable_ssl=True)

print("=" * 70)
print("  Isolation Forest Anomaly Detection")
print("=" * 70)


def fetch_metric(query, minutes=60, step='15s'):
    """Fetch metric data from Prometheus."""
    end = datetime.now()
    start = end - timedelta(minutes=minutes)
    result = prom.custom_query_range(query=query, start_time=start,
                                      end_time=end, step=step)
    if not result or not result[0]['values']:
        return None
    values = [float(v[1]) for v in result[0]['values']]
    timestamps = [datetime.fromtimestamp(float(v[0])) for v in result[0]['values']]
    return pd.DataFrame({'timestamp': timestamps, 'value': values})


# =============================================================================
# SINGLE METRIC: Isolation Forest on CPU
# =============================================================================
print("\n" + "─" * 70)
print("PART 1: Single-Metric Isolation Forest")
print("─" * 70)

df = fetch_metric('app_cpu_usage_percent', minutes=60)

if df is not None:
    # Feature engineering: Add temporal features
    df['hour'] = df['timestamp'].dt.hour
    df['minute'] = df['timestamp'].dt.minute
    df['rate_of_change'] = df['value'].diff().fillna(0)
    df['rolling_mean'] = df['value'].rolling(window=10, min_periods=1).mean()
    df['deviation_from_rolling'] = df['value'] - df['rolling_mean']

    # Prepare features
    features = ['value', 'rate_of_change', 'deviation_from_rolling']
    X = df[features].values

    # Normalize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train Isolation Forest
    # contamination = expected fraction of anomalies (tune this!)
    model = IsolationForest(
        n_estimators=100,       # Number of trees
        contamination=0.05,     # Expect ~5% anomalies
        random_state=42,
        max_samples='auto'
    )

    # Fit and predict (-1 = anomaly, 1 = normal)
    df['prediction'] = model.fit_predict(X_scaled)
    df['anomaly_score'] = model.decision_function(X_scaled)
    df['is_anomaly'] = df['prediction'] == -1

    anomalies = df[df['is_anomaly']]
    print(f"\n  Algorithm: Isolation Forest")
    print(f"  Features used: {features}")
    print(f"  Data points: {len(df)}")
    print(f"  Anomalies detected: {len(anomalies)} ({len(anomalies)/len(df)*100:.1f}%)")
    print(f"\n  Anomaly Score Range: [{df['anomaly_score'].min():.3f}, "
          f"{df['anomaly_score'].max():.3f}]")
    print(f"  (More negative = more anomalous)")

    if len(anomalies) > 0:
        print(f"\n  Top 5 most anomalous points:")
        top = anomalies.nsmallest(5, 'anomaly_score')
        for _, row in top.iterrows():
            print(f"    {row['timestamp'].strftime('%H:%M:%S')} → "
                  f"CPU={row['value']:.1f}%, "
                  f"Change={row['rate_of_change']:.1f}%, "
                  f"Score={row['anomaly_score']:.3f}")

    # Visualization
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    # Plot 1: Raw data with anomalies
    ax = axes[0]
    normal = df[~df['is_anomaly']]
    ax.plot(df['timestamp'], df['value'], 'b-', linewidth=0.8, alpha=0.6)
    ax.scatter(anomalies['timestamp'], anomalies['value'],
               color='red', s=60, zorder=5, label=f'Anomalies ({len(anomalies)})')
    ax.set_title('Isolation Forest: CPU Anomaly Detection')
    ax.set_ylabel('CPU %')
    ax.legend()

    # Plot 2: Anomaly scores
    ax = axes[1]
    ax.plot(df['timestamp'], df['anomaly_score'], 'purple', linewidth=0.8)
    ax.axhline(y=0, color='orange', linestyle='--', label='Decision boundary')
    ax.fill_between(df['timestamp'], df['anomaly_score'], 0,
                    where=(df['anomaly_score'] < 0), alpha=0.3, color='red')
    ax.set_title('Anomaly Scores (negative = anomalous)')
    ax.set_ylabel('Score')
    ax.legend()

    # Plot 3: Rate of change
    ax = axes[2]
    ax.plot(df['timestamp'], df['rate_of_change'], 'g-', linewidth=0.8)
    ax.scatter(anomalies['timestamp'], anomalies['rate_of_change'],
               color='red', s=40, zorder=5)
    ax.set_title('Rate of Change (sudden jumps are suspicious)')
    ax.set_ylabel('Δ CPU %')
    ax.set_xlabel('Time')

    plt.tight_layout()
    plt.savefig('isolation_forest_results.png', dpi=100)
    print(f"\n  📊 Chart saved to: isolation_forest_results.png")

else:
    print("  No data available. Start docker-compose and wait a few minutes.")


# =============================================================================
# MULTI-METRIC: Correlated Anomalies
# =============================================================================
print("\n" + "─" * 70)
print("PART 2: Multi-Metric Isolation Forest")
print("─" * 70)
print("""
  Real-world insight: Looking at MULTIPLE metrics together catches anomalies
  that single-metric analysis misses.
  
  Example: CPU=60% alone is fine. But CPU=60% + Latency=5s + Errors=20%
  together is clearly a problem.
""")

# Fetch multiple metrics
metrics = {
    'cpu': 'app_cpu_usage_percent',
    'memory': 'app_memory_usage_bytes',
    'queue': 'app_queue_depth',
    'connections': 'active_connections'
}

dfs = {}
for name, query in metrics.items():
    result = fetch_metric(query, minutes=60)
    if result is not None:
        dfs[name] = result

if len(dfs) >= 3:
    # Align all metrics on timestamp (they might have slightly different times)
    # Use the shortest dataframe's length
    min_len = min(len(d) for d in dfs.values())

    multi_df = pd.DataFrame()
    multi_df['timestamp'] = list(dfs.values())[0]['timestamp'][:min_len]
    for name, d in dfs.items():
        multi_df[name] = d['value'].values[:min_len]

    # Prepare multi-dimensional features
    feature_cols = [c for c in multi_df.columns if c != 'timestamp']
    X_multi = multi_df[feature_cols].values

    # Normalize
    scaler_multi = StandardScaler()
    X_multi_scaled = scaler_multi.fit_transform(X_multi)

    # Train on multiple metrics simultaneously
    model_multi = IsolationForest(
        n_estimators=200,
        contamination=0.03,  # More conservative with multi-metric
        random_state=42
    )

    multi_df['prediction'] = model_multi.fit_predict(X_multi_scaled)
    multi_df['score'] = model_multi.decision_function(X_multi_scaled)
    multi_df['is_anomaly'] = multi_df['prediction'] == -1

    multi_anomalies = multi_df[multi_df['is_anomaly']]
    print(f"\n  Metrics used: {feature_cols}")
    print(f"  Multi-metric anomalies: {len(multi_anomalies)} "
          f"({len(multi_anomalies)/len(multi_df)*100:.1f}%)")
    print(f"\n  These are points where the COMBINATION of metrics is unusual,")
    print(f"  even if individual metrics might look normal!")

    if len(multi_anomalies) > 0:
        print(f"\n  Sample multi-metric anomalies:")
        for _, row in multi_anomalies.head(3).iterrows():
            print(f"    {row['timestamp'].strftime('%H:%M:%S')} → "
                  f"CPU={row.get('cpu', 'N/A'):.1f}%, "
                  f"Queue={row.get('queue', 'N/A'):.0f}, "
                  f"Conns={row.get('connections', 'N/A'):.0f}")
else:
    print("  Not enough metrics available yet. Let the app run longer.")


# =============================================================================
# HOW TO TUNE THE MODEL
# =============================================================================
print("\n" + "─" * 70)
print("TUNING GUIDE")
print("─" * 70)
print("""
  Key parameters to tune:
  
  contamination (0.01 - 0.1):
    - Lower → fewer alerts, might miss things
    - Higher → more alerts, more noise
    - Start with 0.05, adjust based on results
    
  n_estimators (50 - 500):
    - More trees → more stable results, slower
    - 100-200 is usually sufficient
    
  Features to include:
    - Raw metric value
    - Rate of change (derivative)
    - Rolling mean/std
    - Time-of-day (for seasonality awareness)
    - Correlation with other metrics
    
  IMPORTANT: Retrain periodically! "Normal" changes over time.
  In production, retrain weekly or use sliding windows.
""")

print("\n" + "=" * 70)
print("  Exercise Complete!")
print("  Next: Try multi_metric_detector.py for correlation-based detection")
print("=" * 70)
