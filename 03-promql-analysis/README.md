# Topic 3: Basic Analysis with PromQL & The Limits of Manual Thresholds

## What is PromQL?

**PromQL** (Prometheus Query Language) is how you ask questions about your metrics.
It's the foundation of all dashboards, alerts, and analysis in Prometheus.

## PromQL Fundamentals

### Instant Vectors (a snapshot in time)

```promql
# Current value of all HTTP request counters
http_requests_total

# Filter by labels
http_requests_total{method="GET", status="200"}

# Regex matching
http_requests_total{status=~"5.."}    # All 5xx errors
http_requests_total{endpoint!="/health"}  # Exclude health checks
```

### Range Vectors (a window of time)

```promql
# All samples from the last 5 minutes
http_requests_total[5m]

# Last 1 hour
http_requests_total[1h]
```

### Key Functions

| Function | What It Does | Example |
|----------|-------------|---------|
| `rate()` | Per-second rate of increase | `rate(http_requests_total[5m])` |
| `irate()` | Instant rate (last 2 points) | `irate(http_requests_total[1m])` |
| `increase()` | Total increase over window | `increase(http_requests_total[1h])` |
| `avg_over_time()` | Average value over window | `avg_over_time(cpu_usage[5m])` |
| `histogram_quantile()` | Calculate percentiles | `histogram_quantile(0.95, rate(...))` |
| `predict_linear()` | Linear prediction | `predict_linear(metric[1h], 3600)` |

## Hands-On Exercises

### Exercise 3.1: Essential Queries

Open Prometheus at http://localhost:9090 and try each query:

```promql
# 1. Request rate (requests per second)
rate(http_requests_total[5m])

# 2. Error rate as a percentage
sum(rate(http_requests_total{status=~"5.."}[5m])) 
/ 
sum(rate(http_requests_total[5m])) * 100

# 3. 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# 4. Top endpoints by request count
topk(5, sum by(endpoint) (rate(http_requests_total[5m])))

# 5. Memory usage percentage
(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100
```

### Exercise 3.2: Aggregation Operators

```promql
# Sum all requests across all labels
sum(rate(http_requests_total[5m]))

# Group by method
sum by(method) (rate(http_requests_total[5m]))

# Group by status code
sum by(status) (rate(http_requests_total[5m]))

# Average CPU across all cores
avg(rate(node_cpu_seconds_total{mode="idle"}[5m]))

# Count unique time series
count(http_requests_total)
```

### Exercise 3.3: Run the Analysis Script

```bash
cd 03-promql-analysis
python promql_analysis.py
```

This script demonstrates querying Prometheus via API and analyzing the results.

## The Limits of Manual Thresholds

### Problem Demonstration

Run the threshold analysis to see why static alerts fail:

```bash
python threshold_problems.py
```

### Why Static Thresholds Fail

#### 1. They Don't Understand Context

```
Rule: CPU > 80% for 5 min → ALERT

Reality:
  Monday 2am: CPU at 85% (batch job running) → False alarm!
  Tuesday 10am: CPU at 85% (same level) → Actually a problem!
  
The SAME value means different things at different times.
```

#### 2. They Miss Slow Degradation

```
Week 1: Response time avg = 100ms
Week 2: Response time avg = 150ms
Week 3: Response time avg = 200ms
Week 4: Response time avg = 250ms

Threshold set at 500ms → Never fires until catastrophic failure!
But the TREND is clearly problematic.
```

#### 3. They Generate Too Much Noise

```
Threshold: Error rate > 1%

Result over 24 hours:
  - Fires 47 times
  - 44 of those lasted < 30 seconds (transient blips)
  - 3 were real problems
  - Engineers now ignore ALL alerts
```

#### 4. They Can't Handle Seasonality

```
Traffic pattern:
  Weekday peak: 10,000 req/s (normal)
  Weekend peak: 3,000 req/s (normal)
  
  If you set threshold at 8,000 → Never alerts on weekends
  If you set threshold at 2,000 → Always alerts on weekdays
  
  There's NO single number that works.
```

### What We Need Instead

| Static Thresholds | Intelligent Detection |
|-------------------|-----------------------|
| One-size-fits-all | Adapts to patterns |
| Manual tuning required | Learns automatically |
| Misses slow changes | Detects gradual drift |
| High false positive rate | Context-aware alerting |
| Reactive | Predictive |

## Prometheus's Built-in "Intelligence"

Prometheus does have some semi-smart functions:

```promql
# Predict where a value will be in 4 hours based on last 1 hour trend
predict_linear(node_filesystem_avail_bytes[1h], 4*3600)

# Rate of change (derivative)
deriv(app_memory_usage_bytes[30m])

# Standard deviation — detect if value is unusual
# Value is > 2 standard deviations from mean
abs(app_cpu_usage_percent - avg_over_time(app_cpu_usage_percent[1h]))
> 2 * stddev_over_time(app_cpu_usage_percent[1h])
```

These help but are limited:
- `predict_linear` only does linear extrapolation (no seasonality)
- `stddev` assumes normal distribution (real data often isn't)
- No learning, no memory of past patterns

This is where real ML comes in → **Topics 4 and 5**!

## Key Takeaways

1. PromQL is powerful for real-time analysis
2. `rate()` is essential for counters — never graph raw counter values
3. Static thresholds work for simple cases but fail for dynamic systems
4. Seasonality, gradual degradation, and context destroy simple rules
5. Prometheus has basic prediction but ML provides much more

---
**Next: Topic 4 →** We'll build ML-powered anomaly detection that actually understands "normal."
