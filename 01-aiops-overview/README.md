# Topic 1: The "AI" in AIOps — From Data to Decisions

---

## PART A: THEORY (Read and Understand First)

---

### 1.1 What is "Monitoring" and Why Do We Need It?

Imagine you run a web application (like an online shop). You need to know:
- Is it working right now?
- How fast is it responding to customers?
- Is it about to run out of memory or disk space?
- Did something break at 3am while nobody was watching?

**Monitoring** is the practice of continuously collecting data about your systems
so you can answer these questions without manually checking everything.

Think of it like a car dashboard — you don't open the hood every 5 minutes.
Instead, gauges show you speed, fuel, temperature, and warning lights.

---

### 1.2 What is "Observability"?

Observability is a broader concept. It means: "Can I understand what's happening
INSIDE my system just by looking at its OUTPUTS?"

It has three pillars:

```
┌─────────────────────────────────────────────────────────┐
│              THE THREE PILLARS OF OBSERVABILITY          │
├───────────────┬──────────────────┬──────────────────────┤
│    METRICS    │      LOGS        │       TRACES         │
├───────────────┼──────────────────┼──────────────────────┤
│ Numbers over  │ Text records of  │ The journey of a     │
│ time          │ events           │ single request       │
│               │                  │ through services     │
├───────────────┼──────────────────┼──────────────────────┤
│ "CPU is at    │ "Error: database │ "Request went:       │
│  45% right    │  connection      │  Browser → API →     │
│  now"         │  refused at      │  Database → API →    │
│               │  14:03:22"       │  Browser (took 2s)"  │
├───────────────┼──────────────────┼──────────────────────┤
│ Best for:     │ Best for:        │ Best for:            │
│ Dashboards,   │ Debugging,       │ Finding WHERE a      │
│ Alerts,       │ Understanding    │ request got slow     │
│ Trends        │ WHAT happened    │ in a chain           │
└───────────────┴──────────────────┴──────────────────────┘
```

**In this tutorial, we focus on METRICS** because they're:
- Easy to collect at scale
- Perfect for mathematical analysis (AI/ML)
- Great for dashboards and alerting

---

### 1.3 What is a "Metric"?

A metric is a **number** measured at a specific **point in time**.

Examples:
- "At 14:00:00, CPU usage was 45%"
- "At 14:00:15, there were 120 active users"
- "At 14:00:30, response time was 200 milliseconds"

When you collect these numbers repeatedly (say every 15 seconds), you get a
**time series** — a sequence of values over time:

```
Time        │ CPU %
────────────┼───────
14:00:00    │  45
14:00:15    │  47
14:00:30    │  43
14:00:45    │  51
14:01:00    │  48
14:01:15    │  55    ← starting to go up
14:01:30    │  62    ← something happening?
14:01:45    │  78    ← could be a problem!
```

---

### 1.4 The Four Types of Metrics in Prometheus

Prometheus (the tool we'll use) has exactly 4 metric types:

#### Counter
- **Rule**: Only goes UP. Never decreases. Resets to 0 only on restart.
- **Analogy**: Your car's odometer. It only ever increases.
- **Examples**: Total requests served, total errors, total bytes downloaded
- **Why useful**: By calculating the RATE of increase, you know "how many per second"

```
http_requests_total:   100 → 105 → 112 → 120 → 131
                            +5    +7    +8    +11  (getting busier!)
```

#### Gauge
- **Rule**: Goes UP and DOWN. A snapshot of current state.
- **Analogy**: Your car's speedometer. Changes freely.
- **Examples**: Current CPU %, current temperature, active connections, queue size

```
active_connections:    50 → 53 → 48 → 45 → 60 → 55
                          (fluctuates naturally)
```

#### Histogram
- **Rule**: Counts observations and puts them into "buckets" (ranges)
- **Analogy**: Sorting exam scores into grade brackets (A, B, C, D, F)
- **Examples**: Response time distribution — how many requests took <100ms, <200ms, <500ms, etc.
- **Why useful**: Tells you not just the average, but the DISTRIBUTION

```
Response times:
  < 50ms:   ████████████ (60 requests) — most are fast!
  < 100ms:  ████████████████ (80 requests)
  < 500ms:  ██████████████████ (90 requests)
  < 1000ms: ███████████████████ (95 requests)
  < 5000ms: ████████████████████ (100 requests) — 5 were very slow
```

#### Summary
- **Rule**: Similar to histogram but calculates percentiles directly
- **Analogy**: "The 95th percentile student scored 88/100"
- **Examples**: Request sizes, payload lengths
- **When to use**: When you need exact quantiles and don't need to aggregate across instances

---

### 1.5 What are "Labels"?

Labels add **dimensions** to metrics. Instead of one number, you get many
related numbers organized by categories.

Without labels:
```
http_requests_total = 5000    (total requests... but to which endpoint? What status?)
```

With labels:
```
http_requests_total{method="GET", endpoint="/api/users", status="200"} = 3000
http_requests_total{method="GET", endpoint="/api/users", status="500"} = 50
http_requests_total{method="POST", endpoint="/api/orders", status="201"} = 1500
http_requests_total{method="POST", endpoint="/api/orders", status="500"} = 30
```

Now you can ask: "How many errors on the orders endpoint?" → Filter by endpoint + status!

**Warning about cardinality**: Each unique label combination creates a SEPARATE time series.
If you add a label like `user_id="..."` with millions of users, you create millions of
time series and Prometheus will run out of memory. Only use labels with LOW cardinality
(a few dozen values, not thousands).

---

### 1.6 What is "Traditional Monitoring" and Why Does It Fail?

Traditional monitoring uses **static thresholds** — fixed numbers that trigger alerts:

```
IF cpu > 80% FOR 5 minutes → SEND ALERT
IF disk_usage > 90% → SEND ALERT
IF error_rate > 5% → SEND ALERT
```

This seems logical but fails in real life:

#### Problem 1: No Context

```
Monday 2am:  CPU = 85%  →  Alert fires!
  But... a batch job ALWAYS runs at 85% at 2am. This is normal.
  Result: False alarm. Engineer wakes up for nothing.

Tuesday 3pm: CPU = 85%  →  Alert fires!
  This time it's ACTUALLY a problem — unusual for this time.
  But the engineer ignores it because last night's alert was false.
```

#### Problem 2: Alert Fatigue

When you set thresholds too tight, metrics oscillate around them:
```
CPU: 79% → 81% → 78% → 82% → 79% → 80% → 81% ...
Alert: OFF → ON → OFF → ON → OFF → ON → ON ...
```

The engineer gets 50 alerts in an hour. All noise. They start ignoring ALL alerts.
Then a REAL problem happens and nobody notices.

#### Problem 3: Misses Slow Degradation

```
Week 1: Response time = 100ms   (threshold at 500ms → no alert)
Week 2: Response time = 150ms   (still under 500ms → no alert)
Week 3: Response time = 250ms   (still under 500ms → no alert)
Week 4: Response time = 400ms   (still under 500ms → no alert)
Week 5: Response time = 600ms   (FINALLY alerts → but users suffered for weeks!)
```

A human looking at a graph would see the upward TREND weeks ago.
A static threshold only fires when it's already too late.

#### Problem 4: Seasonality

Traffic follows patterns (more during business hours, less at night):
```
Normal weekday: 10,000 requests/second at 2pm
Normal weekend: 2,000 requests/second at 2pm

If threshold = 8,000 → never alerts on weekends (even if 5,000 IS unusual)
If threshold = 3,000 → always alerts on weekdays (even though it's normal)
```

No single number works for all situations.

---

### 1.7 What is AIOps?

**AIOps = Artificial Intelligence for IT Operations**

Instead of humans manually setting thresholds and interpreting data,
we use machine learning to:

| Problem | Traditional Fix | AIOps Fix |
|---------|----------------|-----------|
| "What's normal?" | Human guesses a threshold | ML LEARNS normal from historical data |
| "Is this unusual?" | value > hardcoded_number | ML compares to learned pattern |
| "Will we run out of space?" | Human checks weekly | ML forecasts and alerts days ahead |
| "These 100 alerts are related" | Human correlates manually | ML clusters them automatically |
| "Night traffic is different" | Separate rules per time | ML learns seasonality automatically |

---

### 1.8 The AIOps Pipeline (What We're Building)

```
STEP 1: COLLECT
  Prometheus scrapes metrics from your apps every 15 seconds.
  Node Exporter gives you CPU, memory, disk, network.
  Your app gives you request counts, latency, errors.

STEP 2: STORE
  Prometheus stores all this as time-series data.
  Keeps weeks or months of history.

STEP 3: ANALYZE (Basic)
  PromQL lets you query: "What's the request rate?"
  Grafana shows dashboards.
  Basic alert rules fire on thresholds.

STEP 4: DETECT (AI)
  Python + scikit-learn learns what "normal" looks like.
  Isolation Forest detects anomalies automatically.
  No more manual thresholds!

STEP 5: FORECAST (AI)
  Prophet predicts future metric values.
  "Memory will be full in 3 days" → alert NOW, fix before crash.
```

---

### 1.9 Tools We'll Use (and Why)

| Tool | Role | Why This One |
|------|------|-------------|
| **Prometheus** | Collects & stores metrics | Industry standard, free, huge ecosystem |
| **Grafana** | Visualizes metrics | Beautiful dashboards, works with everything |
| **Node Exporter** | Exposes OS metrics | Built for Prometheus, zero config |
| **Python** | ML/AI scripts | Best ML ecosystem (scikit-learn, Prophet) |
| **scikit-learn** | Anomaly detection | Simple API, production-ready algorithms |
| **Prophet** | Forecasting | Handles seasonality, holidays, easy to use |
| **Docker** | Runs everything | Consistent environment, one command setup |

---

### 1.10 Key Vocabulary

| Term | Meaning |
|------|---------|
| **Time series** | A sequence of (timestamp, value) pairs |
| **Scrape** | Prometheus pulling metrics from a target |
| **Target** | Any service that exposes metrics for Prometheus to scrape |
| **Exporter** | A translator that converts another system's metrics into Prometheus format |
| **PromQL** | Prometheus Query Language — how you ask questions about data |
| **Dashboard** | A visual display of multiple metrics (in Grafana) |
| **Alert rule** | A condition that triggers a notification |
| **Anomaly** | A data point that doesn't match the expected pattern |
| **Forecast** | A prediction of future values based on historical patterns |
| **Seasonality** | Repeating patterns (daily, weekly, yearly) |
| **Cardinality** | The number of unique time series (label combinations) |

---
---

## PART B: HANDS-ON EXERCISES

Now that you understand the concepts, let's see them in action!

---

### Exercise 1.1: Verify Your Stack is Running

In your playground terminal:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

You should see 5 containers all showing "Up".

---

### Exercise 1.2: See Raw Metrics

Run this to see what Prometheus-format metrics look like:
```bash
curl -s http://localhost:8000/metrics | head -50
```

**What to look for:**
- Lines starting with `# HELP` = description of the metric
- Lines starting with `# TYPE` = whether it's counter, gauge, histogram, or summary
- Lines with `{labels}` = the actual metric values

**Try to identify:**
- Find a **Counter** (hint: look for `_total` in the name)
- Find a **Gauge** (hint: look for `app_cpu_usage_percent`)
- Find a **Histogram** (hint: look for `_bucket`)

---

### Exercise 1.3: Query Prometheus

```bash
# What's the current CPU usage?
curl -s "http://localhost:9090/api/v1/query?query=app_cpu_usage_percent" | jq .data.result[0].value[1]

# If jq not installed, just see the full response:
curl -s "http://localhost:9090/api/v1/query?query=app_cpu_usage_percent"

# How many requests have been made total?
curl -s "http://localhost:9090/api/v1/query?query=http_requests_total"

# Are all targets healthy? (1 = up, 0 = down)
curl -s "http://localhost:9090/api/v1/query?query=up"
```

---

### Exercise 1.4: See Labels in Action

```bash
# All request counts (notice how labels create MULTIPLE time series from ONE metric name)
curl -s "http://localhost:9090/api/v1/query?query=http_requests_total" | jq '.data.result[] | {labels: .metric, value: .value[1]}'

# Filter: only GET requests
curl -s 'http://localhost:9090/api/v1/query?query=http_requests_total{method="GET"}'

# Filter: only errors (status 500)
curl -s 'http://localhost:9090/api/v1/query?query=http_requests_total{status="500"}'
```

---

### Exercise 1.5: See Prometheus Targets

```bash
# What is Prometheus monitoring?
curl -s "http://localhost:9090/api/v1/targets" | jq '.data.activeTargets[] | {job: .labels.job, health: .health, url: .scrapeUrl}'
```

You should see 3 targets: prometheus itself, node-exporter, and sample-app.

---

### Exercise 1.6: Access Grafana

If port 3000 is accessible in your browser:
1. Login with `admin` / `admin`
2. Skip the password change
3. Look for the "AIOps Tutorial" folder in Dashboards
4. Open the "AIOps Monitoring Overview" dashboard
5. Watch the metrics update in real-time

If you can't access it in browser, verify it's working:
```bash
curl -s -u admin:admin http://localhost:3000/api/search | jq '.[].title'
```

---

### Exercise 1.7: Watch a Counter Grow

Run this twice with 30 seconds between:
```bash
echo "=== First check ===" 
curl -s "http://localhost:9090/api/v1/query?query=http_requests_total" | jq '.data.result[0].value[1]'
echo "Wait 30 seconds..."
sleep 30
echo "=== Second check ==="
curl -s "http://localhost:9090/api/v1/query?query=http_requests_total" | jq '.data.result[0].value[1]'
```

Notice: the counter ONLY went up! That's what counters do.

---

### Exercise 1.8: Watch a Gauge Fluctuate

```bash
# Run this a few times — see the value change up AND down
curl -s "http://localhost:9090/api/v1/query?query=app_cpu_usage_percent" | jq '.data.result[0].value[1]'
sleep 5
curl -s "http://localhost:9090/api/v1/query?query=app_cpu_usage_percent" | jq '.data.result[0].value[1]'
sleep 5
curl -s "http://localhost:9090/api/v1/query?query=app_cpu_usage_percent" | jq '.data.result[0].value[1]'
```

The CPU gauge goes up AND down — unlike the counter.

---

## Quiz Answers

1. **Counter vs Gauge**: Counter only increases (like an odometer). Gauge goes up and down (like a speedometer).
2. **Alert fatigue**: Static thresholds fire too often on normal fluctuations, engineers ignore all alerts, miss real problems.
3. **AI/ML improvements**: (any two) Anomaly detection, forecasting, correlation, clustering, NLP on logs.
4. **Three pillars**: Metrics, Logs, Traces.

---

**✅ Topic 1 Complete! Next: Topic 2** → Deep dive into how Prometheus collects data and how to build exporters.
