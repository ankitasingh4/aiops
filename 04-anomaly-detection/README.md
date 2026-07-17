# Topic 4: AI-Powered Anomaly Detection

---

## PART A: THEORY (Read and Understand First)

---

### 4.1 What is an "Anomaly"?

An **anomaly** is a data point that doesn't match the expected pattern.

It's NOT just "a high value." Consider:
- CPU at 90% during a known batch job = **normal** (expected)
- CPU at 90% at 3am when it's usually 10% = **anomaly** (unexpected)
- CPU at 20% during business hours when it's usually 60% = **anomaly** (unexpectedly LOW)

**Key insight**: An anomaly is defined by CONTEXT, not by absolute value.

---

### 4.2 Types of Anomalies

```
┌─────────────────────────────────────────────────────────────┐
│                    TYPES OF ANOMALIES                         │
├─────────────────┬────────────────────┬──────────────────────┤
│  POINT ANOMALY  │ CONTEXTUAL ANOMALY │ COLLECTIVE ANOMALY   │
├─────────────────┼────────────────────┼──────────────────────┤
│ Single unusual  │ Unusual in a       │ A GROUP of points    │
│ data point      │ specific context   │ that together are    │
│                 │ (time, location)   │ unusual              │
├─────────────────┼────────────────────┼──────────────────────┤
│ Example:        │ Example:           │ Example:             │
│ CPU suddenly    │ CPU at 80% is      │ CPU was flat at 50%  │
│ jumps to 99%   │ normal at noon but  │ for 2 hours (no     │
│ for one sample  │ anomalous at 3am   │ variation = stuck?)  │
└─────────────────┴────────────────────┴──────────────────────┘
```

---

### 4.3 How Anomaly Detection Works (Concept)

The general approach:

```
STEP 1: LEARN what "normal" looks like
  → Feed historical data to an algorithm
  → Algorithm builds a model of expected behavior

STEP 2: COMPARE new data to the model
  → Each new data point is scored
  → Points far from "expected" get high anomaly scores

STEP 3: ALERT on anomalies
  → If score exceeds threshold → flag as anomaly
  → Send alert with explanation
```

---

### 4.4 Method 1: Statistical Detection (Z-Score)

**The simplest approach.** Based on basic statistics.

#### What is a Z-Score?

The Z-score tells you: "How many standard deviations is this value from the mean?"

```
Z-Score = (value - mean) / standard_deviation
```

**Interpretation:**
- Z = 0: value equals the mean (perfectly normal)
- Z = 1: value is 1 std above mean (mildly unusual)
- Z = 2: value is 2 std above mean (unusual, ~5% chance if normal)
- Z = 3: value is 3 std above mean (very unusual, ~0.3% chance)

**Example:**
```
Your CPU history: mean = 45%, standard_deviation = 10%

Current CPU = 45% → Z = (45-45)/10 = 0    → Perfectly normal
Current CPU = 55% → Z = (55-45)/10 = 1    → A bit high but OK
Current CPU = 70% → Z = (70-45)/10 = 2.5  → Unusual! Possible anomaly
Current CPU = 85% → Z = (85-45)/10 = 4    → Very anomalous!
```

**Rule:** If |Z| > 2.5, flag as anomaly.

#### Rolling Z-Score (Better!)

Instead of comparing to the ALL-TIME mean, compare to the RECENT mean.
This adapts to trends and patterns.

```
Window = last 20 samples

For each new value:
  1. Calculate mean of last 20 values
  2. Calculate std of last 20 values
  3. Z = (new_value - rolling_mean) / rolling_std
  4. If |Z| > 2.5 → anomaly
```

This is better because:
- If CPU gradually shifts from 40% to 60% over an hour, the rolling mean
  adjusts, so 60% won't be flagged (it's the new normal)
- Only SUDDEN jumps relative to recent behavior get flagged

#### Pros and Cons

| Pros | Cons |
|------|------|
| Very simple to implement | Assumes data follows normal distribution |
| Fast (no training needed) | Doesn't handle seasonality |
| Easy to explain | Global Z-Score fooled by trends |
| Works in real-time | Sensitive to outliers in the window |

---

### 4.5 Method 2: Isolation Forest (ML-Based)

**A real machine learning algorithm** specifically designed for anomaly detection.

#### The Core Idea

"Anomalies are FEW and DIFFERENT. Things that are few and different are
EASY TO ISOLATE."

Imagine you have a room of people:
- 99 people are wearing blue shirts
- 1 person is wearing a red shirt with a top hat

You can describe/isolate the odd person in ONE sentence:
"The person with the red shirt." (Easy to isolate = anomaly)

To describe a normal person you need many details:
"The person with the blue shirt, brown hair, standing in row 3, seat 5..."
(Hard to isolate = normal)

#### How It Works (Simplified)

1. Build random decision trees that split data with random features and thresholds
2. Anomalies need FEWER splits to be isolated (shorter path in tree)
3. Normal points need MANY splits (deeper in the tree)
4. Average the path length across many trees
5. Short average path = anomaly

```
         Random Tree
            │
      ┌─────┴─────┐
    CPU>60?       CPU≤60?
      │             │
    ┌─┴──┐      ┌──┴────┐
  Mem>4GB Mem≤4GB  ... (deeper)
    │
  ISOLATED!    ← Only 2 splits needed = likely anomaly
  (this point)
```

#### Why Isolation Forest is Great for AIOps

- **No distribution assumption**: Works even if your data isn't normal/Gaussian
- **Multi-dimensional**: Can detect anomalies across MULTIPLE metrics simultaneously
- **Fast**: O(n log n) training time
- **Handles high-dimensional data**: Works even with 50+ features

#### Key Parameters

| Parameter | What It Does | Typical Value |
|-----------|-------------|---------------|
| `n_estimators` | Number of trees | 100-200 |
| `contamination` | Expected fraction of anomalies | 0.01-0.10 |
| `max_samples` | Samples per tree | 'auto' (256) |

**Contamination is the most important to tune:**
- 0.01 = "I expect only 1% of data to be anomalous" (strict, fewer alerts)
- 0.10 = "I expect 10% to be anomalous" (sensitive, more alerts)

---

### 4.6 Method 3: DBSCAN Clustering

**Another approach: Find groups, and anything that doesn't belong to a group is anomalous.**

DBSCAN (Density-Based Spatial Clustering) works by:
1. Find dense regions of data points (clusters)
2. Points in dense regions = normal
3. Points NOT in any dense region = noise = anomalies

```
    ●●●●●●         ●●●●
    ●●●●●●●        ●●●●●
    ●●●●●●         ●●●●
    (cluster 1)     (cluster 2)
    
              ×         ×
           (noise - anomalies!)
```

**When to use DBSCAN vs Isolation Forest:**
- DBSCAN: When you want to find GROUPS of normal behavior and outliers
- Isolation Forest: When you just want to score each point's "weirdness"

---

### 4.7 Multi-Metric Detection (The Real Power)

**Single metric detection has a BIG limitation:**
- CPU = 60% → is that unusual? Hard to say alone.

**Multi-metric detection is much more powerful:**
- CPU = 60% AND Latency = 5s AND Errors = 20% → CLEARLY a problem!
- CPU = 60% AND Latency = 100ms AND Errors = 0.1% → Totally fine!

The COMBINATION tells the story.

```
Normal state:           Anomalous state:
  CPU: 50%               CPU: 60%        ← only slightly high
  Latency: 200ms        Latency: 3000ms  ← way too high
  Errors: 1%            Errors: 15%      ← way too high
  Queue: 5              Queue: 50        ← way too high
  
  Individually, CPU=60% is fine.
  But TOGETHER with the other metrics, it paints a clear picture.
```

**How to implement:**
Feed ALL metrics as features into Isolation Forest. The algorithm finds
data points where the COMBINATION of values is unusual, even if individual
values look OK.

---

### 4.8 Feature Engineering for Anomaly Detection

Raw metric values alone aren't always the best input. We can create
**derived features** that make anomalies easier to spot:

| Feature | Formula | What It Captures |
|---------|---------|-----------------|
| Raw value | `value` | Current state |
| Rate of change | `value - previous_value` | Sudden jumps |
| Rolling mean | `mean(last N values)` | Recent trend |
| Deviation from rolling mean | `value - rolling_mean` | Surprise vs recent |
| Hour of day | `timestamp.hour` | Time context |
| Day of week | `timestamp.weekday` | Weekly patterns |
| Volatility | `std(last N values)` | Stability |

Adding these features helps the model understand CONTEXT.

---

### 4.9 The Contamination Trade-off

```
Low contamination (0.01):
  "Be very strict — only flag the MOST unusual points"
  → Fewer alerts
  → Might miss some real anomalies (false negatives)
  → Good for: paging engineers at 3am

High contamination (0.10):
  "Be sensitive — flag anything moderately unusual"
  → More alerts
  → Might flag normal variations (false positives)
  → Good for: daily review dashboards
```

**Start with 0.05 (5%) and adjust based on results.**

---

### 4.10 Retraining: Models Must Adapt

"Normal" changes over time:
- Your app gets new features (more CPU usage becomes normal)
- User growth (more traffic becomes normal)
- Infrastructure changes (new server, different patterns)

**Solution: Retrain periodically**
- Retrain every week with the latest data
- Or use a **sliding window**: always train on the most recent N hours
- In our tutorial, we retrain every 50 new samples

---

### 4.11 Anomaly Explanation: WHY is it Anomalous?

Detecting an anomaly isn't enough. Engineers need to know WHY.

For each anomaly, we calculate which metrics contributed most:
```
🚨 ANOMALY DETECTED at 14:03:22 (score: -0.15)

Contributing factors:
  latency_p95:  VERY HIGH (z=+4.2, value=3.5s, normal=0.2s)
  error_rate:   HIGH (z=+3.1, value=12%, normal=2%)
  queue_depth:  ELEVATED (z=+2.5, value=45, normal=8)
  cpu:          NORMAL (z=+0.3, value=52%)
  
Likely cause: Backend degradation (high latency → errors → queue backup)
```

This helps engineers triage faster.

---

### 4.12 Summary: Choosing the Right Method

| Scenario | Best Method | Why |
|----------|------------|-----|
| Quick setup, single metric | Z-Score (Rolling) | Simple, no training |
| Complex patterns, multi-metric | Isolation Forest | Handles non-linear |
| Finding clusters of behavior | DBSCAN | Groups similar patterns |
| Real-time streaming detection | Rolling Z + Isolation Forest | Fast updates |
| Rare, extreme outliers | Z-Score with high threshold | Catches only extremes |

---
---

## PART B: HANDS-ON EXERCISES

---

### Exercise 4.1: See Statistical Detection in Action

This requires Python. If you're in the Docker playground without Python,
you can run this on your local machine pointing at the playground's Prometheus.

On your **local Windows machine** (where Python is installed):

```bash
cd c:\Users\esiannk\Downloads\2026\IDUN-198190-new\aiops-monitoring-tutorial\04-anomaly-detection
pip install prometheus-api-client pandas numpy scikit-learn matplotlib
python statistical_detection.py
```

If running locally, make sure Docker is running the stack locally too,
or change the Prometheus URL in the script to point at your playground.

---

### Exercise 4.2: Isolation Forest Detection

```bash
python isolation_forest_detector.py
```

This will:
1. Fetch CPU data from Prometheus
2. Train an Isolation Forest model
3. Score each data point
4. Show you which points are anomalous and WHY
5. Save a chart showing the results

---

### Exercise 4.3: Multi-Metric Correlation

```bash
python multi_metric_detector.py
```

This fetches CPU, memory, queue depth, connections, request rate, error rate,
and latency — then finds points where the COMBINATION is unusual.

---

### Exercise 4.4: Real-Time Detection (Live!)

```bash
python realtime_detector.py
```

This runs continuously:
- Collects metrics every 30 seconds
- After 30 samples, starts detecting anomalies
- Retrains every 50 samples
- Shows live alerts with explanations

Press Ctrl+C to stop.

---

### Exercise 4.5: Manual Exploration (No Python Needed)

Even without Python, you can see basic anomaly detection in Prometheus:

```bash
# Simple Z-Score-like detection in PromQL:
# "Is current CPU more than 2 standard deviations from recent mean?"
curl -s 'http://localhost:9090/api/v1/query?query=abs(app_cpu_usage_percent-avg_over_time(app_cpu_usage_percent[30m]))>2*stddev_over_time(app_cpu_usage_percent[30m])' | jq '.data.result'

# If result is empty [] → current value is normal
# If result has data → current value is anomalous
```

---

## Key Takeaways

1. Anomalies are about CONTEXT, not absolute values
2. Z-Score is simple but limited — good for quick checks
3. Isolation Forest handles complex, multi-dimensional patterns
4. Multi-metric detection catches problems single-metric misses
5. Feature engineering (rate of change, time-of-day) improves detection
6. Models need periodic retraining as "normal" evolves
7. Always explain WHY something is anomalous (not just that it IS)

---

**✅ Topic 4 Complete! Next: Topic 5** → Forecasting future values to PREVENT problems before they happen.
