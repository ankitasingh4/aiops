"""
Facebook Prophet Forecasting
==============================
Prophet is Meta's open-source forecasting library designed for:
- Multiple seasonalities (daily + weekly + yearly)
- Holiday effects
- Missing data handling
- Automatic outlier detection
- Uncertainty intervals

It's the go-to tool for forecasting infrastructure metrics.

Usage:
    python prophet_forecast.py

Note: Prophet requires: pip install prophet
(This can take a while to install due to Stan compilation)
"""

import sys
from datetime import datetime, timedelta

try:
    from prometheus_api_client import PrometheusConnect
    import pandas as pd
    import numpy as np
    from prophet import Prophet
    import matplotlib.pyplot as plt
    import warnings
    warnings.filterwarnings('ignore')
except ImportError as e:
    missing = str(e).split("'")[1] if "'" in str(e) else str(e)
    print(f"Missing: {missing}")
    print("Install: pip install prometheus-api-client pandas numpy prophet matplotlib")
    sys.exit(1)

prom = PrometheusConnect(url="http://localhost:9090", disable_ssl=True)

print("=" * 70)
print("  Facebook Prophet Forecasting for Infrastructure Metrics")
print("=" * 70)


def fetch_metric(query, minutes=120, step='60s'):
    """Fetch metric from Prometheus."""
    end = datetime.now()
    start = end - timedelta(minutes=minutes)
    result = prom.custom_query_range(
        query=query, start_time=start, end_time=end, step=step
    )
    if not result or not result[0]['values']:
        return None
    values = [float(v[1]) for v in result[0]['values']]
    timestamps = [datetime.fromtimestamp(float(v[0])) for v in result[0]['values']]
    return pd.DataFrame({'ds': timestamps, 'y': values})  # Prophet requires 'ds' and 'y'


# =============================================================================
# STEP 1: Prepare Data for Prophet
# =============================================================================
print("\n" + "─" * 70)
print("STEP 1: Preparing Data for Prophet")
print("─" * 70)
print("""
  Prophet requires a DataFrame with exactly two columns:
  - 'ds': datetime column (timestamps)
  - 'y': numeric column (values to forecast)
  
  That's it! Prophet handles everything else automatically.
""")

# Try to fetch real data, fall back to synthetic
df = fetch_metric('app_cpu_usage_percent', minutes=120)

if df is None or len(df) < 50:
    print("  Insufficient Prometheus data. Generating synthetic data...")
    print("  (Run docker-compose for 2+ hours for real data)")

    # Generate realistic synthetic data
    np.random.seed(42)
    n = 500  # 500 minutes of data
    timestamps = [datetime.now() - timedelta(minutes=n-i) for i in range(n)]

    # Simulate: trend + daily seasonality + noise + occasional spikes
    t = np.arange(n)
    trend = 35 + 0.02 * t  # Slow upward trend
    daily = 15 * np.sin(2 * np.pi * t / (24 * 60 / 1))  # Compressed daily cycle
    weekly = 5 * np.sin(2 * np.pi * t / (7 * 24 * 60 / 1))  # Weekly pattern
    noise = np.random.normal(0, 3, n)
    spikes = np.zeros(n)
    spike_indices = np.random.choice(n, size=10, replace=False)
    spikes[spike_indices] = np.random.uniform(15, 30, 10)

    values = trend + daily + weekly + noise + spikes
    values = np.clip(values, 5, 95)

    df = pd.DataFrame({'ds': timestamps, 'y': values})
    print(f"  Generated {n} synthetic data points")

print(f"\n  Data shape: {df.shape}")
print(f"  Time range: {df['ds'].min()} → {df['ds'].max()}")
print(f"  Value range: {df['y'].min():.1f} → {df['y'].max():.1f}")


# =============================================================================
# STEP 2: Train Prophet Model
# =============================================================================
print("\n" + "─" * 70)
print("STEP 2: Training Prophet Model")
print("─" * 70)
print("""
  Prophet automatically detects:
  - Trend (linear or logistic growth)
  - Seasonality (daily, weekly, yearly)
  - Changepoints (when the trend changes)
""")

# Initialize Prophet with custom settings for infrastructure data
model = Prophet(
    changepoint_prior_scale=0.05,  # Flexibility of trend (higher = more flexible)
    seasonality_prior_scale=10.0,  # Strength of seasonality
    interval_width=0.95,           # 95% confidence interval
    daily_seasonality=True,
    weekly_seasonality=True,
    yearly_seasonality=False,      # We don't have a year of data
)

# Add custom seasonality (e.g., our app's compressed "day" cycle)
# In real use, you'd add business-specific patterns
model.add_seasonality(
    name='shift_pattern',
    period=0.5,  # 12-hour shift pattern
    fourier_order=3
)

# Fit the model
print("\n  Training Prophet... (this may take a moment)")
model.fit(df)
print("  ✅ Model trained!")

# Print detected changepoints
changepoints = model.changepoints
print(f"\n  Detected {len(changepoints)} trend changepoints")
if len(changepoints) > 0:
    print(f"  Last changepoint: {changepoints.iloc[-1]}")


# =============================================================================
# STEP 3: Generate Forecast
# =============================================================================
print("\n" + "─" * 70)
print("STEP 3: Generating Forecast")
print("─" * 70)

# Create future dataframe (forecast 2 hours ahead)
forecast_periods = 120  # minutes
future = model.make_future_dataframe(periods=forecast_periods, freq='min')

# Predict
forecast = model.predict(future)

print(f"\n  Forecast horizon: {forecast_periods} minutes ({forecast_periods/60:.1f} hours)")
print(f"  Forecast points: {len(forecast) - len(df)}")

# Show forecast summary
future_only = forecast[forecast['ds'] > df['ds'].max()]
print(f"\n  Forecasted values (next 2 hours):")
print(f"    Min: {future_only['yhat'].min():.1f}")
print(f"    Max: {future_only['yhat'].max():.1f}")
print(f"    Mean: {future_only['yhat'].mean():.1f}")
print(f"    Uncertainty range: [{future_only['yhat_lower'].min():.1f}, "
      f"{future_only['yhat_upper'].max():.1f}]")


# =============================================================================
# STEP 4: Anomaly Detection with Prophet
# =============================================================================
print("\n" + "─" * 70)
print("STEP 4: Prophet as Anomaly Detector")
print("─" * 70)
print("""
  Prophet's confidence intervals make it a natural anomaly detector:
  - If actual value falls OUTSIDE the predicted interval → Anomaly!
  - The interval adapts to seasonality, so "normal" varies by time.
""")

# Check historical data against predictions
historical_forecast = forecast[forecast['ds'] <= df['ds'].max()].copy()
historical_forecast = historical_forecast.merge(df, on='ds', how='inner')

# Find anomalies (outside confidence interval)
historical_forecast['is_anomaly'] = (
    (historical_forecast['y'] > historical_forecast['yhat_upper']) |
    (historical_forecast['y'] < historical_forecast['yhat_lower'])
)

anomalies = historical_forecast[historical_forecast['is_anomaly']]
print(f"\n  Historical anomalies (outside 95% CI): {len(anomalies)} / "
      f"{len(historical_forecast)} ({len(anomalies)/max(1,len(historical_forecast))*100:.1f}%)")


# =============================================================================
# STEP 5: Component Analysis
# =============================================================================
print("\n" + "─" * 70)
print("STEP 5: Forecast Components")
print("─" * 70)
print("""
  Prophet decomposes the forecast into interpretable components:
  - Trend: long-term direction
  - Daily seasonality: within-day pattern
  - Weekly seasonality: day-of-week pattern
  - Custom seasonality: any pattern you added
""")

# Extract components
components = ['trend', 'daily', 'weekly']
for comp in components:
    if comp in forecast.columns:
        vals = forecast[comp]
        print(f"  {comp:10s}: range [{vals.min():.2f}, {vals.max():.2f}], "
              f"amplitude={vals.max()-vals.min():.2f}")


# =============================================================================
# VISUALIZATION
# =============================================================================
fig, axes = plt.subplots(3, 1, figsize=(14, 14))

# Plot 1: Main forecast
ax = axes[0]
ax.plot(df['ds'], df['y'], 'b.', markersize=2, alpha=0.5, label='Actual')
ax.plot(forecast['ds'], forecast['yhat'], 'r-', linewidth=1.5, label='Prophet Forecast')
ax.fill_between(forecast['ds'], forecast['yhat_lower'], forecast['yhat_upper'],
                alpha=0.2, color='red', label='95% Confidence Interval')
if len(anomalies) > 0:
    ax.scatter(anomalies['ds'], anomalies['y'], color='red', s=50, zorder=5,
               marker='x', label=f'Anomalies ({len(anomalies)})')
# Mark forecast region
ax.axvline(x=df['ds'].max(), color='black', linestyle=':', alpha=0.5, label='Forecast start')
ax.set_title('Prophet Forecast with Confidence Intervals')
ax.set_ylabel('Value')
ax.legend(loc='upper left')

# Plot 2: Trend + Changepoints
ax = axes[1]
ax.plot(forecast['ds'], forecast['trend'], 'g-', linewidth=2, label='Trend')
for cp in changepoints:
    ax.axvline(x=cp, color='orange', linestyle='--', alpha=0.5)
ax.axvline(x=changepoints.iloc[0] if len(changepoints) > 0 else df['ds'].min(),
           color='orange', linestyle='--', alpha=0.5, label='Changepoints')
ax.set_title('Trend Component with Changepoints')
ax.set_ylabel('Trend')
ax.legend()

# Plot 3: Seasonality
ax = axes[2]
if 'daily' in forecast.columns:
    # Plot one full day of seasonality
    daily_period = forecast[forecast['ds'] <= forecast['ds'].min() + timedelta(days=1)]
    ax.plot(daily_period['ds'], daily_period['daily'], 'purple',
            linewidth=2, label='Daily Seasonality')
if 'weekly' in forecast.columns:
    ax.plot(daily_period['ds'], daily_period['weekly'], 'orange',
            linewidth=2, label='Weekly Seasonality')
ax.set_title('Seasonal Components')
ax.set_ylabel('Effect')
ax.set_xlabel('Time')
ax.legend()

plt.tight_layout()
plt.savefig('prophet_forecast.png', dpi=100)
print(f"\n  📊 Charts saved to: prophet_forecast.png")


# =============================================================================
# STEP 6: Capacity Planning with Prophet
# =============================================================================
print("\n" + "─" * 70)
print("STEP 6: Capacity Planning - When Will We Hit Limits?")
print("─" * 70)

threshold = 80  # CPU threshold
# Find when upper confidence band exceeds threshold
breach_rows = future_only[future_only['yhat_upper'] > threshold]

if len(breach_rows) > 0:
    first_breach = breach_rows.iloc[0]
    time_until_breach = (first_breach['ds'] - df['ds'].max()).total_seconds() / 60
    print(f"\n  ⚠️  CAPACITY WARNING:")
    print(f"     Metric may exceed {threshold}% within {time_until_breach:.0f} minutes")
    print(f"     First potential breach: {first_breach['ds'].strftime('%H:%M')}")
    print(f"     Predicted value: {first_breach['yhat']:.1f}% "
          f"(CI: [{first_breach['yhat_lower']:.1f}, {first_breach['yhat_upper']:.1f}])")
else:
    print(f"\n  ✅ No capacity breach predicted in the next {forecast_periods} minutes")
    print(f"     Maximum forecasted value: {future_only['yhat_upper'].max():.1f}% "
          f"(threshold: {threshold}%)")


print("\n" + "=" * 70)
print("  PROPHET SUMMARY")
print("=" * 70)
print("""
  Prophet excels at:
  ✅ Multiple seasonalities (daily + weekly + yearly)
  ✅ Automatic changepoint detection
  ✅ Handling missing data gracefully
  ✅ Built-in uncertainty quantification
  ✅ Holiday/event effects
  ✅ Robust to outliers
  
  Use Prophet when:
  - You have at least a few days of data
  - The metric has clear seasonal patterns
  - You need interpretable forecasts
  - You want automatic anomaly detection (via CI)
  
  For real-time, streaming forecasting → consider online learning methods
  For very short-term (< 1 hour) → ARIMA or exponential smoothing may be better
""")
