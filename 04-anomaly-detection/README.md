# Topic 4: AI-Powered Anomaly Detection

## What is Anomaly Detection?

Instead of hardcoding "alert if X > 80%", anomaly detection **learns what normal looks like**
and alerts when behavior deviates from learned patterns.

```
Traditional:  value > threshold → ALERT
AI-based:     value ≠ expected_pattern → ALERT (even if value is "low"!)
```

## Techniques We'll Implement

| Method | Complexity | Best For |
|--------|-----------|----------|
| Z-Score / Statistical | Simple | Stationary data, quick setup |
| Isolation Forest | Medium | Multi-dimensional anomalies |
| DBSCAN Clustering | Medium | Finding unusual patterns |
| Rolling Statistics | Simple | Streaming/real-time detection |
| Autoencoders (bonus) | Advanced | Complex temporal patterns |

## Hands-On Exercises

### Exercise 4.1: Statistical Anomaly Detection (Z-Score)

The simplest approach: flag values that are far from the mean.

```bash
python statistical_detection.py
```

This calculates dynamic thresholds based on rolling statistics.

### Exercise 4.2: Isolation Forest

A tree-based ML algorithm specifically designed for anomaly detection.
It works by: "Anomalies are few and different, so they're easy to isolate."

```bash
python isolation_forest_detector.py
```

### Exercise 4.3: Multi-Metric Correlation

Real anomalies often appear across multiple metrics simultaneously.
A CPU spike alone might be normal, but CPU + latency + error rate all spiking = problem.

```bash
python multi_metric_detector.py
```

### Exercise 4.4: Real-time Detection Pipeline

Connect directly to Prometheus and run continuous detection:

```bash
python realtime_detector.py
```

This runs continuously, checking every 30 seconds for anomalies.

## Key Concepts

### What Makes a Good Anomaly Detector?

1. **Low false positive rate** — Don't cry wolf
2. **Catches real issues** — Don't miss actual problems
3. **Adapts over time** — What's normal changes
4. **Context-aware** — Understands time-of-day, seasonality
5. **Explainable** — Can tell you WHY something is anomalous

### The Contamination Parameter

Most anomaly detection algorithms have a "contamination" parameter:
- `contamination=0.01` → Expect 1% of data to be anomalous
- `contamination=0.05` → Expect 5% of data to be anomalous

Lower = fewer alerts but might miss things. Higher = more sensitive but noisier.

---
**Next: Topic 5 →** Forecasting future values to prevent problems before they happen.
