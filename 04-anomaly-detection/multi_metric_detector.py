"""
Multi-Metric Correlation-Based Anomaly Detection
==================================================
In real systems, anomalies rarely affect just ONE metric.
This script demonstrates how correlating multiple metrics
catches issues that single-metric analysis misses.

Key insight: A CPU spike during batch processing = normal.
             A CPU spike + latency spike + error spike = INCIDENT.

Usage:
    python multi_metric_detector.py
"""

import sys
from datetime import datetime, timedelta

try:
    from prometheus_api_client import PrometheusConnect
    import pandas as pd
    import numpy as np
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import DBSCAN
    import matplotlib.pyplot as plt
except ImportError:
    print("Install: pip install prometheus-api-client pandas numpy scikit-learn matplotlib")
    sys.exit(1)

prom = PrometheusConnect(url="http://localhost:9090", disable_ssl=True)

print("=" * 70)
print("  Multi-Metric Correlation Anomaly Detection")
print("=" * 70)


def fetch_aligned_metrics(queries, minutes=60, step='30s'):
    """Fetch multiple metrics and align them by timestamp."""
    end = datetime.now()
    start = end - timedelta(minutes=minutes)

    all_data = {}
    for name, query in queries.items():
        result = prom.custom_query_range(
            query=query, start_time=start, end_time=end, step=step
        )
        if result and result[0]['values']:
            values = [float(v[1]) for v in result[0]['values']]
            all_data[name] = values

    if not all_data:
        return None

    # Align to shortest series
    min_len = min(len(v) for v in all_data.values())
    df = pd.DataFrame({k: v[:min_len] for k, v in all_data.items()})

    # Add timestamps from first metric
    first_result = prom.custom_query_range(
        query=list(queries.values())[0], start_time=start, end_time=end, step=step
    )
    timestamps = [datetime.fromtimestamp(float(v[0]))
                  for v in first_result[0]['values'][:min_len]]
    df['timestamp'] = timestamps

    return df


# =============================================================================
# FETCH ALL METRICS
# =============================================================================
print("\nFetching metrics from Prometheus...")

queries = {
    'cpu': 'app_cpu_usage_percent',
    'memory_mb': 'app_memory_usage_bytes / 1024 / 1024',
    'queue_depth': 'app_queue_depth',
    'connections': 'active_connections',
    'request_rate': 'sum(rate(http_requests_total[1m]))',
    'error_rate': 'sum(rate(http_requests_total{status=~"5.."}[1m]))',
    'latency_p95': 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[1m]))',
}

df = fetch_aligned_metrics(queries, minutes=60)

if df is None or len(df) < 20:
    print("\n  ⚠️  Not enough data. Let docker-compose run for ~10 minutes first.")
    print("  Then re-run this script.")
    sys.exit(0)

print(f"  Fetched {len(df)} data points across {len(queries)} metrics")
metric_cols = [c for c in df.columns if c != 'timestamp']


# =============================================================================
# CORRELATION ANALYSIS
# =============================================================================
print("\n" + "─" * 70)
print("STEP 1: Metric Correlation Matrix")
print("─" * 70)
print("""
  Understanding which metrics move TOGETHER helps identify:
  - Causal relationships (CPU→Latency→Errors)
  - Shared dependencies
  - Normal co-movement vs anomalous divergence
""")

corr_matrix = df[metric_cols].corr()
print("\n  Correlation Matrix:")
print(corr_matrix.round(2).to_string())

# Find strong correlations
print("\n  Strong correlations (|r| > 0.5):")
for i in range(len(metric_cols)):
    for j in range(i+1, len(metric_cols)):
        r = corr_matrix.iloc[i, j]
        if abs(r) > 0.5:
            direction = "↑↑" if r > 0 else "↑↓"
            print(f"    {metric_cols[i]:15s} ↔ {metric_cols[j]:15s}: "
                  f"r={r:+.2f} {direction}")


# =============================================================================
# MULTI-METRIC ISOLATION FOREST
# =============================================================================
print("\n" + "─" * 70)
print("STEP 2: Multi-Metric Isolation Forest")
print("─" * 70)

# Feature engineering
feature_df = df[metric_cols].copy()

# Add derived features
for col in metric_cols:
    feature_df[f'{col}_change'] = df[col].diff().fillna(0)

# Normalize
X = feature_df.values
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Train model
model = IsolationForest(
    n_estimators=200,
    contamination=0.05,
    random_state=42
)

predictions = model.fit_predict(X_scaled)
scores = model.decision_function(X_scaled)

df['anomaly_score'] = scores
df['is_anomaly'] = predictions == -1

anomalies = df[df['is_anomaly']]
print(f"\n  Multi-metric anomalies: {len(anomalies)} / {len(df)} "
      f"({len(anomalies)/len(df)*100:.1f}%)")


# =============================================================================
# ANOMALY EXPLANATION
# =============================================================================
print("\n" + "─" * 70)
print("STEP 3: Anomaly Explanation (WHY is it anomalous?)")
print("─" * 70)
print("""
  For each anomaly, we identify WHICH metrics are most unusual
  by comparing them to normal behavior.
""")

if len(anomalies) > 0:
    # Calculate z-scores for normal data to establish baseline
    normal_data = df[~df['is_anomaly']][metric_cols]
    normal_mean = normal_data.mean()
    normal_std = normal_data.std()

    print("\n  Anomaly Explanations:")
    for idx, (_, row) in enumerate(anomalies.head(5).iterrows()):
        print(f"\n  Anomaly #{idx+1} at {row['timestamp'].strftime('%H:%M:%S')} "
              f"(score: {row['anomaly_score']:.3f})")

        # Find which metrics are most unusual
        deviations = {}
        for col in metric_cols:
            if normal_std[col] > 0:
                z = (row[col] - normal_mean[col]) / normal_std[col]
                deviations[col] = z

        # Sort by absolute deviation
        sorted_devs = sorted(deviations.items(), key=lambda x: abs(x[1]), reverse=True)
        print("    Contributing factors:")
        for metric, z in sorted_devs[:3]:
            direction = "HIGH" if z > 0 else "LOW"
            print(f"      {metric:15s}: {direction} (z={z:+.2f}, "
                  f"value={row[metric]:.2f})")


# =============================================================================
# DBSCAN CLUSTERING
# =============================================================================
print("\n" + "─" * 70)
print("STEP 4: DBSCAN Clustering (Finding Anomaly Patterns)")
print("─" * 70)
print("""
  DBSCAN groups similar data points into clusters.
  Points that don't belong to ANY cluster = anomalies (noise).
  
  Unlike Isolation Forest, DBSCAN can find arbitrarily shaped clusters
  and naturally identifies outliers.
""")

# Use DBSCAN on scaled features
dbscan = DBSCAN(eps=1.5, min_samples=5)
clusters = dbscan.fit_predict(X_scaled[:, :len(metric_cols)])

df['cluster'] = clusters
noise_points = df[df['cluster'] == -1]
n_clusters = len(set(clusters)) - (1 if -1 in clusters else 0)

print(f"\n  Clusters found: {n_clusters}")
print(f"  Noise points (anomalies): {len(noise_points)} ({len(noise_points)/len(df)*100:.1f}%)")
print(f"\n  Cluster distribution:")
for c in sorted(set(clusters)):
    count = (clusters == c).sum()
    label = "NOISE/Anomalies" if c == -1 else f"Cluster {c}"
    print(f"    {label}: {count} points")


# =============================================================================
# VISUALIZATION
# =============================================================================
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Plot 1: Multi-metric time series with anomalies
ax = axes[0, 0]
for col in ['cpu', 'queue_depth', 'connections']:
    if col in df.columns:
        normalized = (df[col] - df[col].min()) / (df[col].max() - df[col].min())
        ax.plot(df['timestamp'], normalized, linewidth=0.8, label=col)
if len(anomalies) > 0:
    ax.scatter(anomalies['timestamp'],
               [0.5] * len(anomalies),
               color='red', s=100, marker='x', zorder=5, label='Anomalies')
ax.set_title('Multi-Metric View (Normalized)')
ax.legend(loc='upper right')
ax.set_ylabel('Normalized Value')

# Plot 2: Anomaly scores over time
ax = axes[0, 1]
ax.plot(df['timestamp'], df['anomaly_score'], 'purple', linewidth=0.8)
ax.axhline(y=0, color='red', linestyle='--', alpha=0.7, label='Decision boundary')
ax.fill_between(df['timestamp'], df['anomaly_score'], 0,
                where=(df['anomaly_score'] < 0), alpha=0.3, color='red')
ax.set_title('Anomaly Scores Over Time')
ax.set_ylabel('Score (< 0 = anomalous)')
ax.legend()

# Plot 3: 2D projection (CPU vs Latency)
ax = axes[1, 0]
if 'latency_p95' in df.columns:
    normal_pts = df[~df['is_anomaly']]
    ax.scatter(normal_pts['cpu'], normal_pts['latency_p95'],
               c='blue', alpha=0.3, s=20, label='Normal')
    if len(anomalies) > 0:
        ax.scatter(anomalies['cpu'], anomalies['latency_p95'],
                   c='red', s=80, marker='x', label='Anomaly')
    ax.set_xlabel('CPU %')
    ax.set_ylabel('Latency p95 (s)')
    ax.set_title('CPU vs Latency (anomalies in red)')
    ax.legend()

# Plot 4: DBSCAN clusters
ax = axes[1, 1]
if 'cpu' in df.columns and 'connections' in df.columns:
    scatter = ax.scatter(df['cpu'], df['connections'],
                         c=df['cluster'], cmap='viridis', s=20, alpha=0.6)
    noise = df[df['cluster'] == -1]
    if len(noise) > 0:
        ax.scatter(noise['cpu'], noise['connections'],
                   c='red', s=80, marker='x', label='Noise (anomalies)')
    ax.set_xlabel('CPU %')
    ax.set_ylabel('Connections')
    ax.set_title(f'DBSCAN Clusters ({n_clusters} clusters found)')
    ax.legend()
    plt.colorbar(scatter, ax=ax, label='Cluster ID')

plt.tight_layout()
plt.savefig('multi_metric_anomalies.png', dpi=100)
print(f"\n  📊 Chart saved to: multi_metric_anomalies.png")

print("\n" + "=" * 70)
print("  KEY TAKEAWAY: Multi-metric detection catches correlation-based anomalies")
print("  that single-metric approaches completely miss!")
print("=" * 70)
