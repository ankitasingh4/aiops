# Topic 3: Basic Analysis with PromQL & The Limits of Manual Thresholds

---

## PART A: THEORY (Read and Understand First)

---

### 3.1 What is PromQL?

**PromQL** = Prometheus Query Language

It's how you ASK QUESTIONS about your metrics data. Think of it like SQL
but for time-series data:

- SQL: "Show me all orders from last week where total > $100"
- PromQL: "Show me the request rate over the last 5 minutes where status is 500"

You use PromQL in:
- Prometheus UI (to explore data)
- Grafana dashboards (to draw charts)
- Alert rules (to define when to fire alerts)

---

### 3.2 PromQL Basics: Selectors

The simplest query is just a metric name:

```promql
app_cpu_usage_percent
```

This returns the CURRENT value of that metric (called an "instant vector").

**Adding label filters:**
```promql
# Only GET requests
http_requests_total{method="GET"}

# Only errors
http_requests_total{status="500"}

# Combine filters (AND logic)
http_requests_total{method="GET", status="200"}

# Regex matching (=~ for match, !~ for not match)
http_requests_total{status=~"5.."}        # Any 5xx status
http_requests_total{endpoint!="/health"}   # Exclude health checks
```

---

### 3.3 Understanding Instant vs Range Vectors

This is a fundamental concept:

#### Instant Vector
Returns ONE value per time series (the latest value):
```promql
app_cpu_usage_percent
→ Result: 45.3 (just the current number)
```

#### Range Vector
Returns MULTIPLE values per time series (all values in a time window):
```promql
app_cpu_usage_percent[5m]
→ Result: [42.1, 43.5, 45.3, 44.8, 46.2, ...] (all values from last 5 minutes)
```

**Why does this matter?**
You can't graph a range vector directly, but you can apply FUNCTIONS to it:
```promql
rate(http_requests_total[5m])   # Calculate the per-second rate from last 5 minutes
avg_over_time(app_cpu_usage_percent[5m])  # Average CPU over last 5 minutes
```

---

### 3.4 The Most Important Function: rate()

Counters only go up, so their raw value isn't useful for "what's happening NOW?"

```
Raw counter values:
  14:00 → 1000
  14:01 → 1015
  14:02 → 1035
  14:03 → 1060
```

What you ACTUALLY want to know: "How many requests per second?"

**rate()** calculates this:
```promql
rate(http_requests_total[5m])
```

This means: "Looking at the last 5 minutes of counter values, what's the
per-second rate of increase?"

```
  Between 14:00 and 14:05: counter went from 1000 to 1300
  Increase = 300 over 300 seconds
  rate = 300/300 = 1 request per second
```

**GOLDEN RULE: Never graph a raw counter. Always use rate() or increase().**

A raw counter just shows an ever-increasing line (useless).
`rate(counter[5m])` shows the actual throughput (useful).

---

### 3.5 Key PromQL Functions

| Function | Input | Output | Use Case |
|----------|-------|--------|----------|
| `rate(counter[duration])` | Range vector | Instant vector | Per-second rate |
| `increase(counter[duration])` | Range vector | Instant vector | Total increase in window |
| `avg_over_time(gauge[duration])` | Range vector | Instant vector | Smoothed average |
| `max_over_time(gauge[duration])` | Range vector | Instant vector | Peak value in window |
| `histogram_quantile(φ, histogram)` | Histogram | Instant vector | Percentile (0.95 = p95) |
| `sum(vector)` | Instant vector | Single value | Total across all series |
| `avg(vector)` | Instant vector | Single value | Average across series |
| `count(vector)` | Instant vector | Single value | Number of series |
| `topk(N, vector)` | Instant vector | Top N series | Find biggest |
| `predict_linear(gauge[duration], seconds)` | Range vector | Instant vector | Linear extrapolation |
| `deriv(gauge[duration])` | Range vector | Instant vector | Rate of change |
| `stddev_over_time(gauge[duration])` | Range vector | Instant vector | Volatility |

---

### 3.6 Aggregation Operators

These combine multiple time series into fewer time series:

```promql
# Sum ALL request rates into one number
sum(rate(http_requests_total[5m]))
→ Result: 5.2 (total requests/second across ALL endpoints)

# Sum grouped by method (one result per method)
sum by(method) (rate(http_requests_total[5m]))
→ GET: 4.1
→ POST: 1.1

# Sum grouped by status
sum by(status) (rate(http_requests_total[5m]))
→ 200: 4.5
→ 201: 0.5
→ 500: 0.2

# Average CPU across all instances
avg(app_cpu_usage_percent)
```

The pattern is: `AGGREGATION by(label) (expression)`

---

### 3.7 Calculating Useful Things

#### Error Rate (as a percentage):
```promql
# errors / total * 100
sum(rate(http_requests_total{status=~"5.."}[5m])) 
/ 
sum(rate(http_requests_total[5m])) 
* 100
```

Reading this: "Sum up the rate of 5xx errors, divide by total rate, multiply by 100"

#### 95th Percentile Latency:
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

Reading this: "95% of requests completed faster than X seconds"

#### Memory Usage Percentage:
```promql
(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100
```

Reading this: "What percentage of total memory is in use?"

#### Disk Will Be Full In N Hours:
```promql
predict_linear(node_filesystem_avail_bytes[1h], 4*3600) < 0
```

Reading this: "Based on the last 1 hour trend, will available disk hit 0 within 4 hours?"

---

### 3.8 Alert Rules in Prometheus

Alert rules are PromQL expressions that Prometheus evaluates periodically:

```yaml
groups:
  - name: basic_alerts
    rules:
      - alert: HighCpuUsage                    # Name of the alert
        expr: app_cpu_usage_percent > 80       # PromQL condition
        for: 5m                                # Must be true for 5 min
        labels:
          severity: warning                    # Metadata
        annotations:
          summary: "CPU is high: {{ $value }}%"  # Human message
```

**How it works:**
1. Every 15s (evaluation_interval), Prometheus runs the PromQL expression
2. If true, starts a timer
3. If still true after `for` duration → fires alert to Alertmanager
4. Alertmanager routes it (Slack, email, PagerDuty)

---

### 3.9 WHY Static Thresholds Fail (The Core Problem)

Now that you understand PromQL and alert rules, let's see why the traditional
approach breaks down:

#### Failure 1: Fixed Numbers vs Dynamic Reality

```
Alert: cpu > 80%

Your app's NORMAL behavior:
  Weekday daytime:  CPU 50-75% (normal business traffic)
  Weekday night:    CPU 10-25% (quiet period)
  Weekend:          CPU 20-40% (moderate)
  Monthly batch:    CPU 85-95% every 1st of month (normal!)

If threshold = 80%:
  → Fires every month during the normal batch job (FALSE POSITIVE)
  → Never fires if night CPU suddenly jumps to 60% (MISSED - that's abnormal for night!)
```

#### Failure 2: Flapping

When a value oscillates near the threshold:
```
Threshold = 70%
CPU values: 69, 71, 68, 72, 70, 71, 69, 73, 68, 72...

Alert state: OFF, ON, OFF, ON, OFF, ON, OFF, ON, OFF, ON...

Engineer receives: 10 alerts in 10 minutes. All meaningless noise.
```

#### Failure 3: The Boiling Frog

Gradual degradation that never crosses the threshold:
```
Month 1: avg response time = 100ms (threshold: 500ms)
Month 2: avg response time = 150ms
Month 3: avg response time = 200ms
Month 4: avg response time = 300ms   ← users complaining but no alert!
Month 5: avg response time = 500ms   ← ALERT! But far too late.
```

#### Failure 4: Different Normals at Different Times

```
10am weekday: 5000 req/s is normal
3am weekday:  100 req/s is normal
10am weekend: 2000 req/s is normal

A drop from 5000 to 100 at 10am = DISASTER (site down!)
A drop from 100 to 50 at 3am = NORMAL (traffic naturally low)

Same direction (drop), same values, OPPOSITE meanings depending on WHEN.
No single threshold handles this.
```

---

### 3.10 Prometheus's Built-in "Smart" Functions

Prometheus has some functions that go beyond simple thresholds:

#### predict_linear() — Simple Forecasting
```promql
# Where will disk be in 4 hours based on last 1 hour trend?
predict_linear(node_filesystem_avail_bytes[1h], 4*3600)
```
Limitation: Only does LINEAR extrapolation. Can't handle curves or seasonality.

#### deriv() — Rate of Change
```promql
# Is memory growing? How fast?
deriv(app_memory_usage_bytes[30m])
```
Limitation: Noisy, hard to set a good threshold on the derivative.

#### stddev_over_time() — Detect Unusual Volatility
```promql
# Is the metric more volatile than usual?
stddev_over_time(app_cpu_usage_percent[1h])
```
Limitation: Assumes normal distribution, doesn't learn patterns.

#### Z-Score-like Detection in PromQL
```promql
# Value is more than 2 standard deviations from recent mean
abs(app_cpu_usage_percent - avg_over_time(app_cpu_usage_percent[1h]))
> 2 * stddev_over_time(app_cpu_usage_percent[1h])
```
Limitation: Short memory, no seasonality awareness, no ML.

**These help but are LIMITED — real ML does much better (Topics 4 & 5).**

---

### 3.11 What We Need: Intelligent Detection

| Capability | Static Thresholds | What AI Provides |
|-----------|-------------------|------------------|
| Understands time-of-day | ❌ | ✅ Learns daily patterns |
| Adapts to trends | ❌ | ✅ Baseline shifts automatically |
| Detects slow degradation | ❌ | ✅ Trend analysis |
| Low false positives | ❌ | ✅ Context-aware |
| Predicts future problems | ❌ | ✅ Forecasting models |
| Correlates multiple signals | ❌ | ✅ Multi-metric analysis |

This is exactly what we'll build in Topics 4 and 5.

---

### 3.12 Key Vocabulary for This Topic

| Term | Meaning |
|------|---------|
| **Instant vector** | One value per time series at one point in time |
| **Range vector** | Multiple values per time series over a time window |
| **rate()** | Per-second increase rate of a counter |
| **Aggregation** | Combining multiple series (sum, avg, count) |
| **Percentile (p95)** | 95% of values are below this number |
| **Alert rule** | PromQL expression that triggers notifications |
| **Flapping** | Alert rapidly switching between ON and OFF |
| **False positive** | Alert that fires when nothing is actually wrong |
| **False negative** | Alert that doesn't fire when something IS wrong |

---
---

## PART B: HANDS-ON EXERCISES

---

### Exercise 3.1: Basic Queries

```bash
# Current CPU
curl -s "http://localhost:9090/api/v1/query?query=app_cpu_usage_percent" | jq '.data.result[0].value[1]'

# Current queue depth
curl -s "http://localhost:9090/api/v1/query?query=app_queue_depth" | jq '.data.result[0].value[1]'

# All targets up?
curl -s "http://localhost:9090/api/v1/query?query=up" | jq '.data.result[] | "\(.metric.job): \(.value[1])"'
```

---

### Exercise 3.2: Using rate() on Counters

```bash
# Request rate (requests per second) over last 5 minutes
curl -s 'http://localhost:9090/api/v1/query?query=rate(http_requests_total[5m])' | jq '.data.result[] | "\(.metric.method) \(.metric.endpoint) \(.metric.status): \(.value[1]) req/s"'

# Total request rate (sum all endpoints)
curl -s 'http://localhost:9090/api/v1/query?query=sum(rate(http_requests_total[5m]))' | jq '.data.result[0].value[1]'
```

---

### Exercise 3.3: Calculating Error Rate

```bash
# Error rate as percentage
curl -s 'http://localhost:9090/api/v1/query?query=sum(rate(http_requests_total{status=~"5.."}[5m]))/sum(rate(http_requests_total[5m]))*100' | jq '.data.result[0].value[1]'
```

If the result is "NaN" it means no requests yet — wait a minute and retry.

---

### Exercise 3.4: Percentile Latency

```bash
# 95th percentile response time (95% of requests are faster than this)
curl -s 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(http_request_duration_seconds_bucket[5m]))' | jq '.data.result[0].value[1]'

# 50th percentile (median)
curl -s 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.50,rate(http_request_duration_seconds_bucket[5m]))' | jq '.data.result[0].value[1]'
```

Notice: p95 is much higher than p50. This means most requests are fast but some are very slow.

---

### Exercise 3.5: Aggregation

```bash
# Group request rate by HTTP method
curl -s 'http://localhost:9090/api/v1/query?query=sum by(method)(rate(http_requests_total[5m]))' | jq '.data.result[] | "\(.metric.method): \(.value[1]) req/s"'

# Group by status code
curl -s 'http://localhost:9090/api/v1/query?query=sum by(status)(rate(http_requests_total[5m]))' | jq '.data.result[] | "\(.metric.status): \(.value[1]) req/s"'

# Group by endpoint
curl -s 'http://localhost:9090/api/v1/query?query=sum by(endpoint)(rate(http_requests_total[5m]))' | jq '.data.result[] | "\(.metric.endpoint): \(.value[1]) req/s"'
```

---

### Exercise 3.6: Using predict_linear()

```bash
# Predict memory in 1 hour based on last 30 minutes trend
curl -s 'http://localhost:9090/api/v1/query?query=predict_linear(app_memory_usage_bytes[30m],3600)/1024/1024' | jq '.data.result[0].value[1]'
```

This shows predicted memory in MB one hour from now. Compare with current:
```bash
curl -s 'http://localhost:9090/api/v1/query?query=app_memory_usage_bytes/1024/1024' | jq '.data.result[0].value[1]'
```

---

### Exercise 3.7: See the Limitation of Static Thresholds

```bash
# Check: how often does CPU exceed 50%?
# (In a real system with seasonality, this fires ALL the time during peaks)
curl -s 'http://localhost:9090/api/v1/query?query=app_cpu_usage_percent>50' | jq '.data.result | length'

# vs how often does CPU deviate more than 2 standard deviations from its mean?
# (This is more "intelligent" - only fires on TRUE anomalies)
curl -s 'http://localhost:9090/api/v1/query?query=abs(app_cpu_usage_percent-avg_over_time(app_cpu_usage_percent[30m]))>2*stddev_over_time(app_cpu_usage_percent[30m])' | jq '.data.result | length'
```

---

### Exercise 3.8: View Active Alert Rules

```bash
# See what alert rules are configured
curl -s "http://localhost:9090/api/v1/rules" | jq '.data.groups[].rules[] | {name: .name, state: .state, query: .query}'

# See currently firing alerts
curl -s "http://localhost:9090/api/v1/alerts" | jq '.data.alerts[] | {alert: .labels.alertname, state: .state, value: .value}'
```

---

## Summary: The Gap That AI Fills

After this topic, you can see that PromQL is **powerful for real-time analysis** but
**limited for intelligent detection**:

```
What PromQL CAN do:                     What it CANNOT do:
✅ Calculate rates and percentiles       ❌ Learn patterns over weeks
✅ Basic statistical measures            ❌ Handle multiple seasonalities
✅ Simple linear prediction              ❌ Detect subtle multi-metric anomalies
✅ Threshold-based alerts                ❌ Adapt thresholds automatically
✅ Aggregate and filter                  ❌ Predict non-linear trends
```

**Topics 4 and 5 fill this gap with real machine learning.**

---

**✅ Topic 3 Complete! Next: Topic 4** → Building ML-powered anomaly detection that actually understands "normal."
