# Topic 5: AI-Driven Forecasting for Proactive Operations

---

## PART A: THEORY (Read and Understand First)

---

### 5.1 What is Forecasting and Why Does It Matter?

**Forecasting** = predicting FUTURE values based on HISTORICAL patterns.

```
Anomaly Detection:  "Something is wrong RIGHT NOW"   → React
Forecasting:        "Something WILL be wrong in 3 days" → Prevent
```

**Real-world examples:**

| Prediction | Action | Outcome |
|-----------|--------|---------|
| "Disk will be full in 5 days" | Add storage now | Zero downtime |
| "Memory leak will crash server in 12h" | Restart tonight | No user impact |
| "Traffic spike in 2 hours (Black Friday)" | Scale up now | Smooth experience |
| "SSL cert expires in 7 days" | Auto-renew | No security warnings |
| "Error rate trending up for 3 days" | Investigate root cause | Fix before outage |

**Without forecasting**: React to problems after they cause damage.
**With forecasting**: Prevent problems before users notice.

---

### 5.2 Components of a Time Series

Every time series can be broken down into components:

```
Observed Value = Trend + Seasonality + Residual (Noise)
```

#### Trend
The long-term direction. Going up, down, or flat.
```
Example: User count growing 100 users/day for months
         ───────────────────────╱ (upward trend)
```

#### Seasonality
Repeating patterns at fixed intervals.
```
Example: Traffic peaks at noon, drops at 3am (daily seasonality)

  ╱╲    ╱╲    ╱╲    ╱╲
 ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲    (repeats every 24 hours)
╱    ╲╱    ╲╱    ╲╱    ╲
```

Multiple seasonalities can overlap:
- **Daily**: Peak at noon, low at night
- **Weekly**: Busier on weekdays than weekends
- **Monthly**: Spike at end of month (billing cycles)
- **Yearly**: Holiday shopping season

#### Residual (Noise)
Random variation that can't be explained by trend or seasonality.
This is what anomaly detection looks for!

#### Decomposition Visualization
```
Observed:     ╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲  (what you see)
                    ↓ decompose ↓
Trend:        ───────────────╱──── (gradual increase)
Seasonality:  ∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿ (repeating pattern)
Residual:     ⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓ (random noise)
```

---

### 5.3 Method 1: Linear Regression (Simplest Forecast)

**Idea**: Fit a straight line through the data and extend it into the future.

```
Historical data:        Forecast:
  ●                      
  ● ●                   - - - - → (line extended)
    ● ●                    ↗
      ● ● ●             line of best fit
        ● ●
```

**Math**: `future_value = slope × time + intercept`

**When to use:**
- Disk usage growing at a steady rate
- Consistent user growth
- Any metric with constant rate of change

**When NOT to use:**
- Data with seasonality (daily patterns)
- Data that accelerates or decelerates
- Oscillating metrics (CPU, latency)

**How to know if it's appropriate:**
Check the **R² score** (coefficient of determination):
- R² > 0.8 → Linear model is a good fit
- R² < 0.5 → Data is NOT linear, use a better method

---

### 5.4 Method 2: Exponential Smoothing (Holt-Winters)

**The problem with linear regression**: It can't handle seasonality.

**Holt-Winters** (also called Triple Exponential Smoothing) handles THREE things:
1. **Level** (α) — the base value of the series
2. **Trend** (β) — the direction it's moving
3. **Seasonality** (γ) — the repeating pattern

```
Level:        where the series IS right now (e.g., 50%)
Trend:        which DIRECTION it's going (e.g., +1% per hour)
Seasonality:  the PATTERN that repeats (e.g., +20% at noon, -15% at 3am)
```

**How it works (simplified):**

```
Prediction for time T = Level(T) + Trend(T) + Seasonal(T)

Where:
  Level(T)    = α × actual(T) + (1-α) × previous_level
  Trend(T)    = β × (level(T) - level(T-1)) + (1-β) × previous_trend
  Seasonal(T) = γ × (actual(T) - level(T)) + (1-γ) × previous_seasonal
```

The α, β, γ parameters (0 to 1) control how much weight is given to
recent observations vs historical patterns:
- α close to 1 → adapts quickly to new levels
- β close to 1 → follows trend changes quickly
- γ close to 1 → adjusts seasonal pattern quickly

**Additive vs Multiplicative:**
- **Additive**: seasonal effect is a FIXED AMOUNT (CPU ±10% every peak)
- **Multiplicative**: seasonal effect SCALES (traffic is 3× at peak vs trough)

---

### 5.5 Method 3: Facebook Prophet

**Prophet** is Meta's (Facebook's) open-source forecasting tool.

Why it's popular for infrastructure forecasting:

| Capability | Prophet | Holt-Winters | Linear |
|-----------|---------|--------------|--------|
| Multiple seasonalities | ✅ daily+weekly+yearly | ❌ only one | ❌ none |
| Holiday effects | ✅ | ❌ | ❌ |
| Missing data | ✅ handles gracefully | ❌ breaks | ❌ breaks |
| Changepoints | ✅ auto-detected | ❌ | ❌ |
| Outlier handling | ✅ robust | ❌ sensitive | ❌ very sensitive |
| Uncertainty intervals | ✅ built-in | ⚠️ basic | ⚠️ basic |
| Ease of use | ✅ 3 lines of code | ⚠️ moderate | ✅ simple |

**How Prophet works (conceptually):**

```
y(t) = trend(t) + seasonality(t) + holidays(t) + error(t)

Where:
  trend(t)       = piecewise linear or logistic growth with changepoints
  seasonality(t) = Fourier series (flexible repeating patterns)
  holidays(t)    = known special events
  error(t)       = what can't be explained
```

**Changepoints**: Prophet automatically detects when the trend CHANGES:
```
  Before:  growing 5% per week
  Changepoint! (new feature launched)
  After:   growing 15% per week
  
  Prophet detects this and adjusts its model.
```

---

### 5.6 Method 4: ARIMA/SARIMA (For Reference)

**ARIMA** = AutoRegressive Integrated Moving Average

This is a classical statistical method. You might see it mentioned but
Prophet is easier for most infrastructure use cases.

- **AR** (AutoRegressive): future depends on past values
- **I** (Integrated): differencing to make data stationary
- **MA** (Moving Average): future depends on past errors
- **S** (Seasonal): adds seasonal component

Parameters: ARIMA(p,d,q) or SARIMA(p,d,q)(P,D,Q,m)

**When to use ARIMA over Prophet:**
- Short time series (< 2 weeks of data)
- Very regular, stationary data
- Need mathematical rigor/proofs

**When to use Prophet over ARIMA:**
- Multiple seasonalities
- Missing data or irregular spacing
- Non-technical stakeholders need to understand it
- Quick setup without parameter tuning

---

### 5.7 Forecast Accuracy: How Good is the Prediction?

You MUST measure how accurate your forecasts are. Common metrics:

#### MAE (Mean Absolute Error)
```
MAE = average( |actual - predicted| )

If MAE = 5: on average, predictions are off by 5 units.
Lower is better.
```

#### MAPE (Mean Absolute Percentage Error)
```
MAPE = average( |actual - predicted| / actual ) × 100%

If MAPE = 10%: predictions are off by 10% on average.
Lower is better. Under 10% is generally good.
```

#### RMSE (Root Mean Squared Error)
```
RMSE = sqrt( average( (actual - predicted)² ) )

Penalizes large errors more than MAE.
If RMSE is much bigger than MAE, you have some BIG misses.
```

#### How to Measure (Train/Test Split)
```
Historical data: [========================|==========]
                         Training (80%)     Test (20%)

1. Train model on first 80%
2. Predict the last 20%
3. Compare predictions to actual values
4. Calculate MAE, MAPE, RMSE
```

---

### 5.8 Confidence Intervals: Quantifying Uncertainty

A single predicted number is not enough. You need to know HOW SURE the model is.

```
Prediction for tomorrow: CPU = 65%
95% Confidence Interval: [55%, 75%]

Meaning: "We're 95% confident CPU will be between 55% and 75%"
```

**Why this matters for operations:**
```
Forecast: Disk will be full in 10 days
95% CI: Between 7 and 14 days

Action: Plan expansion within 7 days (use the WORST case)
```

Wide confidence interval = model is UNSURE → be more conservative.
Narrow confidence interval = model is CONFIDENT → can be less urgent.

---

### 5.9 Capacity Planning: The Killer Application

**Capacity planning** = predicting when you'll run out of resources.

The pipeline:
```
1. Collect historical resource usage (disk, memory, CPU, connections)
2. Forecast future values using Prophet or Holt-Winters
3. Compare forecasted values to capacity limits
4. Calculate time-to-exhaustion
5. Alert if exhaustion is within action window
```

**Example output:**
```
╔══════════════════════════════════════════════════╗
║  CAPACITY PLANNING REPORT                        ║
╠══════════════════════════════════════════════════╣
║  ✅ CPU Usage:       52% / 100% (healthy)        ║
║  ⚠️  Memory:         410MB / 512MB (80% used)    ║
║     → Will exceed limit in 18 hours              ║
║  ✅ Connections:     89 / 200 (healthy)           ║
║  🚨 Queue Depth:     42 / 50 (84% capacity!)     ║
║     → Will exceed limit in 2 hours               ║
╠══════════════════════════════════════════════════╣
║  ACTIONS:                                        ║
║  🚨 Queue: Scale workers immediately             ║
║  ⚠️  Memory: Plan restart or expansion within 18h║
╚══════════════════════════════════════════════════╝
```

---

### 5.10 Stationarity: A Key Concept

A time series is **stationary** if its statistical properties
(mean, variance) stay constant over time.

```
Stationary:     ∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿   (oscillates around a fixed mean)
Non-stationary: ∿∿∿∿∿╱∿∿∿∿╱∿∿∿╱∿   (mean is changing — has a trend)
```

**Why it matters:**
- Most forecasting methods need stationary data (or handle non-stationarity explicitly)
- Linear regression assumes the trend will continue forever (dangerous!)
- Prophet and ARIMA handle non-stationarity automatically

**How to make data stationary (differencing):**
```
Original:    10, 12, 15, 19, 24, 30
Differenced:  2,  3,  4,  5,  6     (the CHANGES between values)
```

---

### 5.11 Common Pitfalls in Forecasting

| Pitfall | Problem | Solution |
|---------|---------|----------|
| Extrapolating too far | Uncertainty grows with time | Limit forecasts to 1-2 seasonal cycles |
| Ignoring seasonality | Under/overestimates at certain times | Use Prophet or Holt-Winters |
| Training on anomalous data | Model learns the anomaly as "normal" | Clean outliers before training |
| Not validating | No idea if forecasts are accurate | Always use train/test split |
| Assuming constant growth | Growth may accelerate or plateau | Use logistic growth in Prophet |
| Single forecast only | Ignores uncertainty | Always include confidence intervals |

---

### 5.12 Putting It All Together: The Complete AIOps Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│              COMPLETE AIOps MONITORING PIPELINE               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  COLLECT          ANALYZE           DETECT          ACT      │
│  ────────         ───────           ──────          ───      │
│  Prometheus   →   PromQL        →   Isolation   →  Alert    │
│  Exporters        Grafana           Forest         Scale     │
│  Custom metrics   Dashboards        Z-Score        Restart   │
│                                     DBSCAN         Ticket    │
│                                                              │
│                   FORECAST          PLAN                      │
│                   ────────          ────                      │
│                   Prophet       →   Capacity      → Budget   │
│                   Holt-Winters      Reports         Expand   │
│                   Linear            Time-to-full    Migrate  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

### 5.13 Key Vocabulary for This Topic

| Term | Meaning |
|------|---------|
| **Forecast** | Prediction of future values |
| **Trend** | Long-term direction (up, down, flat) |
| **Seasonality** | Repeating pattern (daily, weekly, yearly) |
| **Residual** | Random noise after removing trend and seasonality |
| **Stationarity** | Statistical properties don't change over time |
| **Changepoint** | Point where the trend changes direction or rate |
| **Confidence interval** | Range where the true value likely falls |
| **MAE/MAPE/RMSE** | Forecast accuracy measurements |
| **Decomposition** | Breaking series into trend + seasonality + noise |
| **Capacity planning** | Predicting when resources will be exhausted |
| **Extrapolation** | Extending a pattern beyond known data |

---
---

## PART B: HANDS-ON EXERCISES

---

### Exercise 5.1: Linear Forecast

On your local machine (with Python):
```bash
cd 05-forecasting
python linear_forecast.py
```

This will:
- Fetch memory data from Prometheus
- Fit a linear model
- Predict when memory will hit 500MB
- Show you the R² score (is linear appropriate?)
- Save a chart with the forecast

---

### Exercise 5.2: Holt-Winters Forecast

```bash
python holtwinters_forecast.py
```

This demonstrates:
- Time series decomposition (trend + seasonal + residual)
- Fitting a Holt-Winters model
- Forecasting with seasonality
- Measuring accuracy (MAPE)

---

### Exercise 5.3: Prophet Forecast

```bash
python prophet_forecast.py
```

This is the most powerful:
- Automatic seasonality detection
- Changepoint detection
- Confidence intervals
- Using Prophet as anomaly detector (points outside CI)
- Capacity breach prediction

---

### Exercise 5.4: Capacity Planning Pipeline

```bash
python capacity_planner.py
```

This generates a full capacity report:
- Analyzes CPU, memory, queue, connections
- Forecasts each resource
- Calculates time-to-exhaustion
- Generates recommendations

---

### Exercise 5.5: Prometheus-Only Forecasting (No Python Needed)

Even without Python, you can do simple forecasting in Prometheus:

```bash
# Predict memory in 1 hour (linear extrapolation)
curl -s 'http://localhost:9090/api/v1/query?query=predict_linear(app_memory_usage_bytes[30m],3600)/1024/1024' | jq '.data.result[0].value[1]'

# Current memory for comparison
curl -s 'http://localhost:9090/api/v1/query?query=app_memory_usage_bytes/1024/1024' | jq '.data.result[0].value[1]'

# Rate of memory growth (bytes per second)
curl -s 'http://localhost:9090/api/v1/query?query=deriv(app_memory_usage_bytes[30m])' | jq '.data.result[0].value[1]'

# Will any filesystem be full within 4 hours?
curl -s 'http://localhost:9090/api/v1/query?query=predict_linear(node_filesystem_avail_bytes[1h],4*3600)<0' | jq '.data.result'
```

---

## Course Summary

Congratulations! You now understand the complete AIOps pipeline:

```
Topic 1: WHY we need AI in operations (problems with traditional monitoring)
Topic 2: HOW to collect data (Prometheus, exporters, instrumentation)
Topic 3: HOW to analyze data (PromQL) and why static rules break
Topic 4: HOW to detect anomalies (Z-Score, Isolation Forest, multi-metric)
Topic 5: HOW to forecast and prevent (Linear, Holt-Winters, Prophet)
```

### What to Learn Next

1. **Production deployment**: Running anomaly detection as a service
2. **Alert routing**: Integrating with PagerDuty, Slack, OpsGenie
3. **Root cause analysis**: Correlating anomalies across services
4. **Auto-remediation**: Automatically fixing predicted problems
5. **Log anomaly detection**: Applying ML to unstructured log data
6. **Distributed tracing**: Using traces for performance analysis

---

**✅ All 5 Topics Complete! You now have the theoretical knowledge AND hands-on experience
to implement AI-powered monitoring in real infrastructure.**
