"""
Linear Trend Forecasting
=========================
The simplest forecasting approach: fit a line through historical data
and extrapolate into the future.

Good for:
- Disk usage growing steadily
- Consistent user growth
- Any metric with a constant rate of change

Limitations:
- Can't handle seasonality
- Assumes constant growth rate
- Doesn't capture acceleration/deceleration

Usage:
    python linear_forecast.py
"""

import sys
from datetime import datetime, timedelta

try:
    from prometheus_api_client import PrometheusConnect
    import pandas as pd
    import numpy as np
    from sklearn.linear_model import LinearRegression
    import matplotlib.pyplot as plt
except ImportError:
    print("Install: pip install prometheus-api-client pandas numpy scikit-learn matplotlib")
    sys.exit(1)

prom = PrometheusConnect(url="http://localhost:9090", disable_ssl=True)

print("=" * 70)
print("  Linear Trend Forecasting")
print("=" * 70)


def fetch_metric(query, minutes=60, step='30s'):
    """Fetch historical metric data."""
    end = datetime.now()
    start = end - timedelta(minutes=minutes)
    result = prom.custom_query_range(
        query=query, start_time=start, end_time=end, step=step
    )
    if not result or not result[0]['values']:
        return None
    values = [float(v[1]) for v in result[0]['values']]
    timestamps = [datetime.fromtimestamp(float(v[0])) for v in result[0]['values']]
    return pd.DataFrame({'timestamp': timestamps, 'value': values})


# =============================================================================
# EXAMPLE 1: Memory Usage Forecast
# =============================================================================
print("\n" + "─" * 70)
print("FORECAST 1: Memory Usage (Linear Trend)")
print("─" * 70)

df = fetch_metric('app_memory_usage_bytes / 1024 / 1024', minutes=60)

if df is not None and len(df) > 10:
    # Convert timestamps to numeric (seconds since start)
    df['seconds'] = (df['timestamp'] - df['timestamp'].min()).dt.total_seconds()

    # Fit linear regression
    X = df['seconds'].values.reshape(-1, 1)
    y = df['value'].values

    model = LinearRegression()
    model.fit(X, y)

    # Model parameters
    slope = model.coef_[0]  # MB per second
    intercept = model.intercept_
    r_squared = model.score(X, y)

    print(f"\n  Historical data: {len(df)} points over {df['seconds'].max()/60:.0f} minutes")
    print(f"  Current memory: {y[-1]:.1f} MB")
    print(f"  Growth rate: {slope * 3600:.2f} MB/hour ({slope * 86400:.1f} MB/day)")
    print(f"  R² score: {r_squared:.4f} (1.0 = perfect linear fit)")

    # Forecast next 2 hours
    forecast_minutes = 120
    future_seconds = np.arange(
        df['seconds'].max(),
        df['seconds'].max() + forecast_minutes * 60,
        30  # every 30 seconds
    ).reshape(-1, 1)

    future_values = model.predict(future_seconds)
    future_timestamps = [df['timestamp'].max() + timedelta(seconds=int(s))
                         for s in future_seconds.flatten() - df['seconds'].max()]

    # Find when threshold will be breached
    threshold_mb = 500  # Alert at 500MB
    if slope > 0:
        time_to_threshold = (threshold_mb - y[-1]) / slope  # seconds
        if time_to_threshold > 0:
            breach_time = df['timestamp'].max() + timedelta(seconds=time_to_threshold)
            print(f"\n  ⚠️  At current rate, memory will reach {threshold_mb}MB in:")
            print(f"     {time_to_threshold/3600:.1f} hours ({breach_time.strftime('%Y-%m-%d %H:%M')})")
        else:
            print(f"\n  ✅ Memory already above threshold or decreasing")
    else:
        print(f"\n  ✅ Memory is stable or decreasing (slope={slope:.6f})")

    # Visualization
    plt.figure(figsize=(14, 6))
    plt.plot(df['timestamp'], df['value'], 'b-', linewidth=1, label='Historical')
    plt.plot(future_timestamps, future_values, 'r--', linewidth=2, label='Forecast')
    plt.axhline(y=threshold_mb, color='orange', linestyle=':', linewidth=2,
                label=f'Threshold ({threshold_mb}MB)')

    # Confidence interval (simple: ±1 RMSE)
    residuals = y - model.predict(X)
    rmse = np.sqrt(np.mean(residuals**2))
    plt.fill_between(future_timestamps,
                     future_values - 2*rmse,
                     future_values + 2*rmse,
                     alpha=0.2, color='red', label='±2 RMSE')

    plt.title('Memory Usage: Linear Forecast')
    plt.xlabel('Time')
    plt.ylabel('Memory (MB)')
    plt.legend()
    plt.tight_layout()
    plt.savefig('linear_forecast_memory.png', dpi=100)
    print(f"\n  📊 Chart saved to: linear_forecast_memory.png")
else:
    print("  No data available. Run docker-compose for a few minutes first.")


# =============================================================================
# EXAMPLE 2: Request Rate with Confidence Intervals
# =============================================================================
print("\n" + "─" * 70)
print("FORECAST 2: Request Rate with Confidence Intervals")
print("─" * 70)

df2 = fetch_metric('sum(rate(http_requests_total[1m]))', minutes=60)

if df2 is not None and len(df2) > 10:
    df2['seconds'] = (df2['timestamp'] - df2['timestamp'].min()).dt.total_seconds()

    X2 = df2['seconds'].values.reshape(-1, 1)
    y2 = df2['value'].values

    model2 = LinearRegression()
    model2.fit(X2, y2)

    r2 = model2.score(X2, y2)
    print(f"\n  R² = {r2:.4f}")

    if r2 < 0.3:
        print(f"  ⚠️  Low R² means the data is NOT linear!")
        print(f"  Linear regression is a POOR fit for this metric.")
        print(f"  This metric likely has seasonality → use Holt-Winters or Prophet instead.")
    else:
        print(f"  ✅ Reasonable linear fit.")
        print(f"  Trend: {model2.coef_[0]*60:.4f} req/s per minute")

    # Plot anyway to show the limitation
    plt.figure(figsize=(14, 6))
    plt.scatter(df2['timestamp'], df2['value'], s=10, alpha=0.5, label='Actual')
    plt.plot(df2['timestamp'], model2.predict(X2), 'r-', linewidth=2, label='Linear fit')
    plt.title(f'Request Rate: Linear Fit (R²={r2:.3f})')
    plt.xlabel('Time')
    plt.ylabel('Requests/sec')
    plt.legend()
    plt.tight_layout()
    plt.savefig('linear_forecast_requests.png', dpi=100)
    print(f"\n  📊 Chart saved to: linear_forecast_requests.png")
else:
    print("  No data available.")


# =============================================================================
# KEY LESSON
# =============================================================================
print("\n" + "─" * 70)
print("KEY LESSON")
print("─" * 70)
print("""
  Linear forecasting is:
  ✅ Simple and fast
  ✅ Good for steadily growing metrics (disk, users, data volume)
  ✅ Easy to explain to stakeholders
  
  ❌ Bad for seasonal data (traffic patterns)
  ❌ Bad for oscillating data (CPU, latency)  
  ❌ Can't capture acceleration/deceleration
  ❌ No uncertainty quantification (beyond basic RMSE)
  
  ALWAYS check R² score:
  - R² > 0.8: Linear model is appropriate
  - R² < 0.5: Need a more complex model (try Holt-Winters or Prophet)
  
  → Next: holtwinters_forecast.py for seasonal data
""")
