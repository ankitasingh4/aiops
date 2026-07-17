# Topic 1: The "AI" in AIOps — From Data to Decisions

## What is AIOps?

**AIOps = Artificial Intelligence for IT Operations**

It's the practice of using machine learning and data science to automate and improve
IT operations tasks that humans traditionally do manually:

```
Traditional Ops          →    AIOps
──────────────────────────────────────────
Manual threshold alerts  →    Anomaly detection (learns normal behavior)
Reactive firefighting    →    Predictive forecasting (prevents issues)
Human pattern matching   →    Automated correlation (finds root causes)
Static runbooks          →    Adaptive responses (learns from incidents)
```

## The AIOps Pipeline

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  COLLECT │───▶│  STORE   │───▶│ ANALYZE  │───▶│  DETECT  │───▶│   ACT    │
│          │    │          │    │          │    │          │    │          │
│ Metrics  │    │ Time-    │    │ PromQL   │    │ ML Models│    │ Alert    │
│ Logs     │    │ Series   │    │ Stats    │    │ Anomaly  │    │ Auto-    │
│ Traces   │    │ DB       │    │ Baseline │    │ Forecast │    │ Remediate│
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
     ▲                                                                │
     └────────────────── Feedback Loop ───────────────────────────────┘
```

## Why Traditional Monitoring Fails at Scale

### Problem 1: Static Thresholds Don't Work

```
CPU > 80% = ALERT?

But what about:
- A batch job that ALWAYS runs at 90% CPU at 2am (that's normal!)
- A web server that's usually at 60% but dropped to 20% (that's suspicious!)
- A service that gradually went from 30% to 79% over 3 weeks (threshold never fires!)
```

### Problem 2: Alert Fatigue

Organizations with 100+ services can generate **thousands** of alerts daily.
Most are noise. Engineers stop paying attention. Real issues get missed.

### Problem 3: Reactive, Not Proactive

Traditional: Disk is full → Alert → Engineer wakes up → Fixes it (downtime!)
AIOps: Disk growing at 2GB/day, will be full in 5 days → Auto-expand or alert early

## Where AI/ML Helps

| Technique | What It Does | Example |
|-----------|-------------|---------|
| Anomaly Detection | Learns "normal" and flags deviations | CPU pattern changed from its usual rhythm |
| Forecasting | Predicts future values | Memory will be exhausted in 48 hours |
| Correlation | Finds related signals | DB latency spike caused app error spike |
| Clustering | Groups similar incidents | These 50 alerts are all the same root cause |
| NLP | Understands log messages | Extracts error patterns from unstructured logs |

## This Tutorial's Focus

We'll build a practical pipeline:

1. **Prometheus** collects metrics (Topic 2)
2. **PromQL** analyzes them, showing where static rules fail (Topic 3)
3. **Python + scikit-learn** detects anomalies automatically (Topic 4)
4. **Prophet + statsmodels** forecasts future problems (Topic 5)
5. **Grafana** visualizes everything

## Hands-On Exercise

### Exercise 1.1: Start the Stack

```bash
# From the tutorial root directory:
docker-compose up -d

# Verify everything is running:
docker-compose ps
```

You should see 5 services running. Give them 30 seconds to start collecting data.

### Exercise 1.2: Explore the Metrics

1. Open http://localhost:8000/metrics in your browser
2. Find examples of each metric type:
   - **Counter**: Look for `_total` suffix (e.g., `http_requests_total`)
   - **Histogram**: Look for `_bucket` suffix (e.g., `http_request_duration_seconds_bucket`)
   - **Gauge**: Look for values that go up/down (e.g., `active_connections`)
   - **Summary**: Look for `_sum` and `_count` pairs

### Exercise 1.3: See Prometheus in Action

1. Open http://localhost:9090
2. Go to Status → Targets — see what Prometheus is scraping
3. Try a query: `up` — shows which targets are healthy
4. Try: `http_requests_total` — see raw counter values

### Exercise 1.4: First Look at Grafana

1. Open http://localhost:3000 (login: admin/admin)
2. Find the "AIOps Monitoring Overview" dashboard
3. Watch the metrics change in real-time

## Key Concepts to Remember

- **Observability** = Metrics + Logs + Traces (the "three pillars")
- **Metrics** are numeric measurements over time (what we focus on)
- **Time series** = a stream of timestamped values for a specific metric
- **Labels** add dimensions to metrics (method="GET", status="200")
- **Cardinality** = number of unique time series (labels multiply this!)

## Quiz Yourself

1. What's the difference between a Counter and a Gauge?
2. Why do static thresholds cause alert fatigue?
3. Name two ways AI/ML can improve monitoring.
4. What are the three pillars of observability?

---
**Next: Topic 2 →** We'll deep-dive into Prometheus architecture and build custom exporters.
