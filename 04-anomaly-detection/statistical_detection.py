"""
Statistical Anomaly Detection
==============================
The simplest form of intelligent anomaly detection using:
- Z-Score (how many standard deviations from mean)
- Rolling statistics (adapts to recent behavior)
- Modified Z-Score (robust to outliers)

This replaces static thresholds with DYNAMIC, data-driven thresholds.

Usage:
    python statistical_detection.py
"""

import sys
from datetime import datetime, timedelta

try:
    from prometheus_api_client import PrometheusConnect
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
except ImportError:
    print("Install: pip install prometheus-api-client pandas numpy matplotlib")
    sys.exit(1)

prom = PrometheusConnect(url="http://localhost:9090", disable_ssl=True)

print("=" * 70)
print("  Statistical Anomaly Detection")
print("=" * 70)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def fetch_metric(query, minutes=60, step='15s'):
    """Fetch metric data from Prometheus."""
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=minutes)

    result = prom.custom_query_range(
        query=query,
        start_time=start_time,
        end_time=end_time,
        step=step
    )

    if not result or not result[0]['values']:
        return None

    values = [float(v[1]) for v in result[0]['values']]
    timestamps = [datetime.fromtimestamp(float(v[0])) for v in result[0]['values']]
    return pd.DataFrame({'timestamp': timestamps, 'value': values})


# =============================================================================
# METHOD 1: Simple Z-Score
# =============================================================================
print("\n" + "─" * 70)
print("METHOD 1: Z-Score Anomaly Detection")
print("─" * 70)
print("""
  Z-Score = (value - mean) / standard_deviation
  
  If |Z| > 2: unusual (5% of normal data)
  If |Z| > 3: very unusual (0.3% of normal data)
  
  We flag anything with |Z| > 2.5 as anomalous.
""")

df = fetch_metric('app_cpu_usage_percent', minutes=60)
if df is not None:
    # Calculate Z-scores
    mean = df['value'].mean()
    std = df['value'].std()
    df['z_score'] = (df['value'] - mean) / std
    df['is_anomaly'] = abs(df['z_score']) > 2.5

    anomalies = df[df['is_anomaly']]
    print(f"  Data points: {len(df)}")
    print(f"  Mean: {mean:.2f}, Std: {std:.2f}")
    print(f"  Anomalies found: {len(anomalies)} ({len(anomalies)/len(df)*100:.1f}%)")

    if len(anomalies) > 0:
        print(f"\n  Top anomalies:")
        top = anomalies.nlargest(5, 'z_score')
        for _, row in top.iterrows():
            print(f"    {row['timestamp'].strftime('%H:%M:%S')} → "
                  f"CPU={row['value']:.1f}% (Z={row['z_score']:.2f})")
else:
    print("  No data available. Run docker-compose and wait a few minutes.")


# =============================================================================
# METHOD 2: Rolling Z-Score (Adaptive)
# =============================================================================
print("\n" + "─" * 70)
print("METHOD 2: Rolling Z-Score (Adaptive Window)")
print("─" * 70)
print("""
  Instead of comparing to the GLOBAL mean, compare to RECENT behavior.
  This adapts to trends and seasonality automatically.
  
  Window = 20 samples (~5 minutes with 15s scrape interval)
""")

if df is not None:
    window = 20
    df['rolling_mean'] = df['value'].rolling(window=window, center=False).mean()
    df['rolling_std'] = df['value'].rolling(window=window, center=False).std()
    df['rolling_z'] = (df['value'] - df['rolling_mean']) / df['rolling_std']
    df['rolling_anomaly'] = abs(df['rolling_z']) > 2.5

    # Drop NaN rows from rolling calculation
    df_valid = df.dropna()
    rolling_anomalies = df_valid[df_valid['rolling_anomaly']]

    print(f"  Window size: {window} samples")
    print(f"  Rolling anomalies: {len(rolling_anomalies)} "
          f"({len(rolling_anomalies)/len(df_valid)*100:.1f}%)")
    print(f"\n  Compare: Simple Z-Score found {len(anomalies)} anomalies")
    print(f"           Rolling Z-Score found {len(rolling_anomalies)} anomalies")
    print(f"\n  Rolling is better because it adapts to the changing pattern!")


# =============================================================================
# METHOD 3: Modified Z-Score (MAD-based, robust)
# =============================================================================
print("\n" + "─" * 70)
print("METHOD 3: Modified Z-Score (Robust to Outliers)")
print("─" * 70)
print("""
  Regular Z-Score uses mean and std, which are SENSITIVE to outliers.
  Modified Z-Score uses MEDIAN and MAD (Median Absolute Deviation).
  
  MAD = median(|x_i - median(x)|)
  Modified Z = 0.6745 * (x_i - median) / MAD
  
  This is more robust when your data already contains anomalies.
""")

if df is not None:
    median = df['value'].median()
    mad = np.median(np.abs(df['value'] - median))

    if mad > 0:
        df['modified_z'] = 0.6745 * (df['value'] - median) / mad
        df['mad_anomaly'] = abs(df['modified_z']) > 3.0

        mad_anomalies = df[df['mad_anomaly']]
        print(f"  Median: {median:.2f}, MAD: {mad:.2f}")
        print(f"  MAD-based anomalies: {len(mad_anomalies)} "
              f"({len(mad_anomalies)/len(df)*100:.1f}%)")
    else:
        print("  MAD is zero (data is constant). Skipping.")


# =============================================================================
# VISUALIZATION
# =============================================================================
if df is not None and len(df) > window:
    fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)

    # Plot 1: Simple Z-Score
    ax = axes[0]
    ax.plot(df['timestamp'], df['value'], 'b-', linewidth=0.8, label='CPU %')
    ax.axhline(y=mean + 2.5*std, color='r', linestyle='--', alpha=0.7, label='Upper bound')
    ax.axhline(y=mean - 2.5*std, color='r', linestyle='--', alpha=0.7, label='Lower bound')
    if len(anomalies) > 0:
        ax.scatter(anomalies['timestamp'], anomalies['value'],
                   color='red', s=50, zorder=5, label=f'Anomalies ({len(anomalies)})')
    ax.set_title('Method 1: Simple Z-Score (Global Mean ± 2.5σ)')
    ax.set_ylabel('CPU %')
    ax.legend(loc='upper right')

    # Plot 2: Rolling Z-Score
    ax = axes[1]
    ax.plot(df['timestamp'], df['value'], 'b-', linewidth=0.8, label='CPU %')
    ax.plot(df['timestamp'], df['rolling_mean'], 'g-', linewidth=1.5, label='Rolling Mean')
    upper = df['rolling_mean'] + 2.5 * df['rolling_std']
    lower = df['rolling_mean'] - 2.5 * df['rolling_std']
    ax.fill_between(df['timestamp'], lower, upper, alpha=0.2, color='green',
                    label='Dynamic ±2.5σ Band')
    if len(rolling_anomalies) > 0:
        ax.scatter(rolling_anomalies['timestamp'], rolling_anomalies['value'],
                   color='red', s=50, zorder=5,
                   label=f'Anomalies ({len(rolling_anomalies)})')
    ax.set_title('Method 2: Rolling Z-Score (Adaptive Window)')
    ax.set_ylabel('CPU %')
    ax.legend(loc='upper right')

    # Plot 3: Comparison
    ax = axes[2]
    ax.plot(df['timestamp'], abs(df['z_score']), 'b-', alpha=0.6,
            label='Simple |Z|', linewidth=0.8)
    ax.plot(df['timestamp'], abs(df['rolling_z']), 'g-', alpha=0.6,
            label='Rolling |Z|', linewidth=0.8)
    ax.axhline(y=2.5, color='r', linestyle='--', label='Threshold (2.5)')
    ax.set_title('Comparison: Z-Scores Over Time')
    ax.set_ylabel('|Z-Score|')
    ax.set_xlabel('Time')
    ax.legend(loc='upper right')

    plt.tight_layout()
    plt.savefig('statistical_anomalies.png', dpi=100)
    print(f"\n  📊 Chart saved to: statistical_anomalies.png")

print("\n" + "=" * 70)
print("  KEY INSIGHT: Rolling/adaptive methods are always better than static!")
print("  But they still assume roughly Gaussian distributions.")
print("  For complex patterns → use Isolation Forest (next exercise)")
print("=" * 70)
