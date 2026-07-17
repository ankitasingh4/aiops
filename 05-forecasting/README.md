# Topic 5: AI-Driven Forecasting for Proactive Operations

## Why Forecast?

Anomaly detection tells you: "Something is wrong NOW."
Forecasting tells you: "Something WILL be wrong in 48 hours."

```
Reactive:    Problem happens → Alert fires → Engineer responds → Downtime
Proactive:   Forecast problem → Alert early → Engineer prevents → Zero downtime
```

## Use Cases for Forecasting in Ops

| What to Forecast | Why | Action |
|-----------------|-----|--------|
| Disk usage | Will fill up in 3 days | Auto-expand or archive |
| Memory growth | Leak will crash in 12h | Restart/fix before crash |
| Request rate | Black Friday spike in 2h | Scale up preemptively |
| Certificate expiry | Expires in 7 days | Auto-renew |
| Error rate trend | Increasing for 3 days | Investigate root cause |

## Techniques We'll Implement

| Method | Complexity | Best For |
|--------|-----------|----------|
| Linear Regression | Simple | Constant growth trends |
| Moving Average (EMA) | Simple | Smoothing + short-term |
| Holt-Winters | Medium | Trend + seasonality |
| Prophet (Facebook) | Medium | Complex seasonality |
| ARIMA/SARIMA | Advanced | Stationary time series |

## Hands-On Exercises

### Exercise 5.1: Linear Trend Forecasting

The simplest forecasting — fit a line and extrapolate.

```bash
python linear_forecast.py
```

### Exercise 5.2: Holt-Winters (Triple Exponential Smoothing)

Handles trend AND seasonality — perfect for metrics with daily/weekly patterns.

```bash
python holtwinters_forecast.py
```

### Exercise 5.3: Facebook Prophet

Industry-standard forecasting that handles:
- Multiple seasonalities (daily + weekly + yearly)
- Holiday effects
- Missing data
- Outliers

```bash
python prophet_forecast.py
```

### Exercise 5.4: Capacity Planning Pipeline

A complete pipeline that:
1. Fetches historical metrics
2. Forecasts future values
3. Identifies when thresholds will be breached
4. Generates capacity planning reports

```bash
python capacity_planner.py
```

## Key Concepts

### Stationarity
A time series is **stationary** if its statistical properties (mean, variance)
don't change over time. Most forecasting methods need stationary data or
handle non-stationarity explicitly.

### Seasonality
Repeating patterns at fixed intervals:
- **Daily**: Traffic peaks at 2pm, drops at 3am
- **Weekly**: Mondays are busier than weekends
- **Monthly**: End-of-month batch processing

### Trend
Long-term direction: steadily increasing memory, growing request rate.

### Decomposition
Any time series = **Trend** + **Seasonality** + **Residual (noise)**

---
**Congratulations!** After this topic, you'll have a complete AIOps toolkit:
collection → analysis → detection → forecasting.
