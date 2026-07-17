"""
Holt-Winters (Triple Exponential Smoothing) Forecasting
=========================================================
Holt-Winters handles three components:
  1. Level (base value)
  2. Trend (going up or down)
  3. Seasonality (repeating patterns)

This makes it ideal for metrics with daily/weekly cycles like:
- Traffic patterns (peak at noon, low at 3am)
- CPU usage (batch jobs at midnight)
- Order volume (weekday vs weekend)

Usage:
    python holtwinters_forecast.py
"""

import sys
from datetime import datetime, timedelta

try:
    from prometheus_api_client import PrometheusConnect
    import pandas as pd
    import numpy as np
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    from statsmodels.tsa.seasonal import seasonal_decompose
    import matplotlib.pyplot as plt
    import warnings
    warnings.filterwarnings('ignore')
except ImportError:
    print("Install: pip install prometheus-api-client pandas numpy statsmodels matplotlib")
    sys.exit(1)

prom = PrometheusConnect(url="http://localhost:9090", disable_ssl=True)

print("=" * 70)
print("  Holt-Winters Forecasting (Triple Exponential Smoothing)")
print("=" * 70)


def fetch_metric(query, minutes=120, step='60s'):
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
# STEP 1: Time Series Decomposition
# =============================================================================
print("\n" + "─" * 70)
print("STEP 1: Decompose Time Series into Components")
print("─" * 70)
print("""
  Any time series can be broken down into:
    Signal = Trend + Seasonal + Residual
    
  Understanding these components helps choose the right model.
""")

df = fetch_metric('app_cpu_usage_percent', minutes=120, step='60s')

if df is not None and len(df) >= 30:
    # Set timestamp as index with frequency
    ts = df.set_index('timestamp')['value']
    ts = ts.asfreq('60s', method='ffill')  # Ensure regular frequency

    # Decompose (need at least 2 full seasonal periods)
    # Our app simulates a 24-"hour" cycle in 24 minutes
    # So seasonal_period ≈ 24 samples (1 sample per minute × 24 min cycle)
    seasonal_period = min(24, len(ts) // 3)

    if seasonal_period >= 4:
        try:
            decomposition = seasonal_decompose(ts, model='additive',
                                               period=seasonal_period)

            print(f"\n  Data points: {len(ts)}")
            print(f"  Seasonal period: {seasonal_period} samples")
            print(f"  Trend range: {decomposition.trend.dropna().min():.1f} → "
                  f"{decomposition.trend.dropna().max():.1f}")
            print(f"  Seasonal amplitude: "
                  f"{decomposition.seasonal.max() - decomposition.seasonal.min():.1f}")
            print(f"  Residual std: {decomposition.resid.dropna().std():.2f}")

            # Plot decomposition
            fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)
            decomposition.observed.plot(ax=axes[0], title='Observed')
            decomposition.trend.plot(ax=axes[1], title='Trend')
            decomposition.seasonal.plot(ax=axes[2], title='Seasonal')
            decomposition.resid.plot(ax=axes[3], title='Residual')
            plt.tight_layout()
            plt.savefig('decomposition.png', dpi=100)
            print(f"\n  📊 Decomposition saved to: decomposition.png")
        except Exception as e:
            print(f"  Decomposition failed: {e}")
            print("  Need more data. Let the app run longer.")
    else:
        print(f"  Not enough data for decomposition (need ≥12 points, have {len(ts)})")

else:
    print("  No data available. Run docker-compose for at least 30 minutes.")
    print("  Continuing with synthetic data for demonstration...")

    # Create synthetic data to demonstrate the concept
    np.random.seed(42)
    n = 200
    t = np.arange(n)
    trend = 30 + 0.1 * t
    seasonal = 15 * np.sin(2 * np.pi * t / 24)  # 24-sample period
    noise = np.random.normal(0, 3, n)
    synthetic = trend + seasonal + noise

    timestamps = [datetime.now() - timedelta(minutes=n-i) for i in range(n)]
    df = pd.DataFrame({'timestamp': timestamps, 'value': synthetic})
    ts = df.set_index('timestamp')['value']
    ts = ts.asfreq('60s', method='ffill')
    seasonal_period = 24
    print(f"  Using synthetic data ({n} points) for demonstration.")


# =============================================================================
# STEP 2: Holt-Winters Forecasting
# =============================================================================
print("\n" + "─" * 70)
print("STEP 2: Holt-Winters Forecast")
print("─" * 70)
print("""
  Holt-Winters has two flavors:
  - Additive: seasonal effect is CONSTANT (e.g., +10 every peak)
  - Multiplicative: seasonal effect SCALES (e.g., 2x every peak)
  
  For CPU/latency → usually Additive
  For traffic/revenue → often Multiplicative
""")

if ts is not None and len(ts) >= 2 * seasonal_period:
    try:
        # Fit Holt-Winters model
        model = ExponentialSmoothing(
            ts,
            seasonal_periods=seasonal_period,
            trend='add',          # Additive trend
            seasonal='add',       # Additive seasonality
            use_boxcox=False,
            initialization_method='estimated'
        )
        fitted = model.fit(optimized=True)

        # Print model parameters
        print(f"\n  Model Parameters:")
        print(f"    Smoothing level (α): {fitted.params.get('smoothing_level', 'N/A'):.4f}")
        print(f"    Smoothing trend (β): {fitted.params.get('smoothing_trend', 'N/A'):.4f}")
        print(f"    Smoothing seasonal (γ): {fitted.params.get('smoothing_seasonal', 'N/A'):.4f}")
        print(f"    AIC: {fitted.aic:.2f}")

        # Forecast next 60 samples (1 hour ahead)
        forecast_steps = 60
        forecast = fitted.forecast(forecast_steps)

        # Calculate forecast accuracy on last 20% (hold-out)
        holdout_size = len(ts) // 5
        train = ts[:-holdout_size]
        test = ts[-holdout_size:]

        model_eval = ExponentialSmoothing(
            train,
            seasonal_periods=seasonal_period,
            trend='add',
            seasonal='add',
            initialization_method='estimated'
        )
        fitted_eval = model_eval.fit(optimized=True)
        test_forecast = fitted_eval.forecast(holdout_size)

        mae = np.mean(np.abs(test.values - test_forecast.values))
        mape = np.mean(np.abs((test.values - test_forecast.values) / test.values)) * 100
        rmse = np.sqrt(np.mean((test.values - test_forecast.values) ** 2))

        print(f"\n  Forecast Accuracy (hold-out test):")
        print(f"    MAE:  {mae:.2f}")
        print(f"    MAPE: {mape:.1f}%")
        print(f"    RMSE: {rmse:.2f}")

        # Visualization
        fig, axes = plt.subplots(2, 1, figsize=(14, 10))

        # Full forecast
        ax = axes[0]
        ax.plot(ts.index, ts.values, 'b-', linewidth=0.8, label='Historical')
        ax.plot(fitted.fittedvalues.index, fitted.fittedvalues.values,
                'g-', linewidth=1, alpha=0.7, label='Fitted')
        forecast_index = [ts.index[-1] + timedelta(minutes=i+1)
                          for i in range(forecast_steps)]
        ax.plot(forecast_index, forecast.values, 'r--', linewidth=2, label='Forecast')

        # Simple confidence interval
        residual_std = (ts - fitted.fittedvalues).std()
        upper = forecast.values + 2 * residual_std
        lower = forecast.values - 2 * residual_std
        ax.fill_between(forecast_index, lower, upper, alpha=0.2, color='red',
                        label='95% CI')
        ax.set_title('Holt-Winters Forecast: CPU Usage')
        ax.set_ylabel('CPU %')
        ax.legend()

        # Hold-out validation
        ax = axes[1]
        ax.plot(train.index, train.values, 'b-', linewidth=0.8, label='Train')
        ax.plot(test.index, test.values, 'g-', linewidth=2, label='Actual (test)')
        ax.plot(test.index, test_forecast.values, 'r--', linewidth=2,
                label=f'Forecast (MAPE={mape:.1f}%)')
        ax.set_title('Forecast Validation (Hold-out Test)')
        ax.set_ylabel('CPU %')
        ax.set_xlabel('Time')
        ax.legend()

        plt.tight_layout()
        plt.savefig('holtwinters_forecast.png', dpi=100)
        print(f"\n  📊 Chart saved to: holtwinters_forecast.png")

    except Exception as e:
        print(f"  Error: {e}")
        print("  This usually means not enough data or irregular timestamps.")
        print("  Let the app run for 30+ minutes and try again.")
else:
    print(f"  Need at least {2*seasonal_period} data points. Have {len(ts) if ts is not None else 0}.")
    print("  Let the app run longer.")


# =============================================================================
# COMPARISON: Additive vs Multiplicative
# =============================================================================
print("\n" + "─" * 70)
print("STEP 3: Understanding Additive vs Multiplicative Seasonality")
print("─" * 70)
print("""
  Additive:        value = trend + seasonal + noise
  Multiplicative:  value = trend × seasonal × noise
  
  How to choose:
  - If seasonal fluctuations are CONSTANT regardless of level → Additive
  - If seasonal fluctuations GROW with the level → Multiplicative
  
  Example:
  - CPU oscillates ±10% regardless of base level → Additive
  - Traffic peaks are 3x the trough (300 vs 100, then 3000 vs 1000) → Multiplicative
""")


# =============================================================================
# KEY TAKEAWAYS
# =============================================================================
print("\n" + "=" * 70)
print("  KEY TAKEAWAYS")
print("=" * 70)
print("""
  Holt-Winters is great because:
  ✅ Handles trend + seasonality
  ✅ Adapts to level changes
  ✅ Simple to implement
  ✅ Fast (no heavy computation)
  
  Limitations:
  ❌ Only ONE seasonal period (daily OR weekly, not both)
  ❌ Sensitive to outliers
  ❌ Assumes consistent seasonal pattern
  ❌ Needs at least 2 full seasonal cycles of data
  
  For multiple seasonalities → use Prophet (next exercise!)
""")
