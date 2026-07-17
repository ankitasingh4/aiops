# Expected Outputs for All Hands-On Exercises

This document shows you exactly what you WOULD see if you ran each exercise.
Read this to understand the outcomes even without running the commands.

---

## TOPIC 1: AIOps Overview — Expected Outputs

---

### Exercise 1.1: Verify Your Stack is Running

**Command:** `docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"`

**Expected Output:**
```
NAMES            STATUS          PORTS
grafana          Up 7 minutes    0.0.0.0:3000->3000/tcp
prometheus       Up 7 minutes    0.0.0.0:9090->9090/tcp
sample-app       Up 7 minutes    0.0.0.0:8000->8000/tcp
alertmanager     Up 7 minutes    0.0.0.0:9093->9093/tcp
node-exporter    Up 7 minutes    0.0.0.0:9100->9100/tcp
```

**What this means:** All 5 services are running and healthy.

---

### Exercise 1.2: See Raw Metrics

**Command:** `curl -s http://localhost:8000/metrics | head -50`

**Expected Output:**
```
# HELP python_gc_objects_collected_total Objects collected during gc
# TYPE python_gc_objects_collected_total counter
python_gc_objects_collected_total{generation="0"} 1523.0
python_gc_objects_collected_total{generation="1"} 203.0
python_gc_objects_collected_total{generation="2"} 0.0
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{endpoint="/api/users",method="GET",status="200"} 342.0
http_requests_total{endpoint="/api/users",method="GET",status="500"} 18.0
http_requests_total{endpoint="/api/orders",method="POST",status="201"} 45.0
http_requests_total{endpoint="/api/health",method="GET",status="200"} 89.0
# HELP app_cpu_usage_percent Simulated CPU usage percentage
# TYPE app_cpu_usage_percent gauge
app_cpu_usage_percent 52.34
# HELP active_connections Number of active connections
# TYPE active_connections gauge
active_connections 87.0
# HELP app_memory_usage_bytes Simulated memory usage in bytes
# TYPE app_memory_usage_bytes gauge
app_memory_usage_bytes 274523648.0
# HELP app_queue_depth Number of items waiting in processing queue
# TYPE app_queue_depth gauge
app_queue_depth 5.0
```

**How to read this:**
- `# HELP` = description of what the metric measures
- `# TYPE counter` = this is a Counter (only goes up)
- `# TYPE gauge` = this is a Gauge (goes up and down)
- `{labels}` = dimensions (method, endpoint, status)
- The number at the end = current value

**Identify the types:**
- Counter: `http_requests_total` (has `_total` suffix, only increases)
- Gauge: `app_cpu_usage_percent` (changes freely — currently 52.34%)
- Gauge: `active_connections` (currently 87 connections)

---

### Exercise 1.3: Query Prometheus

**Command:** `curl -s "http://localhost:9090/api/v1/query?query=app_cpu_usage_percent"`

**Expected Output:**
```json
{
  "status": "success",
  "data": {
    "resultType": "vector",
    "result": [
      {
        "metric": {
          "__name__": "app_cpu_usage_percent",
          "instance": "sample-app:8000",
          "job": "sample-app"
        },
        "value": [1784284900, "52.34"]
      }
    ]
  }
}
```

**How to read this:**
- `"status": "success"` → query worked
- `"resultType": "vector"` → instant vector (one value per series)
- `"value": [1784284900, "52.34"]` → [unix_timestamp, "value"]
- CPU is currently 52.34%
- Prometheus automatically added labels: `instance` and `job`

---

**Command:** `curl -s "http://localhost:9090/api/v1/query?query=up"`

**Expected Output:**
```json
{
  "status": "success",
  "data": {
    "resultType": "vector",
    "result": [
      {"metric": {"job": "prometheus", "instance": "localhost:9090"}, "value": [1784284900, "1"]},
      {"metric": {"job": "node-exporter", "instance": "node-exporter:9100"}, "value": [1784284900, "1"]},
      {"metric": {"job": "sample-app", "instance": "sample-app:8000"}, "value": [1784284900, "1"]}
    ]
  }
}
```

**How to read this:**
- `"1"` = target is UP and healthy
- `"0"` would mean target is DOWN
- All 3 targets show "1" = everything is working

---

### Exercise 1.4: See Labels in Action

**Command:** `curl -s "http://localhost:9090/api/v1/query?query=http_requests_total"`

**Expected Output:**
```json
{
  "data": {
    "result": [
      {"metric": {"method": "GET", "endpoint": "/api/users", "status": "200"}, "value": [1784284900, "342"]},
      {"metric": {"method": "GET", "endpoint": "/api/users", "status": "500"}, "value": [1784284900, "18"]},
      {"metric": {"method": "POST", "endpoint": "/api/orders", "status": "201"}, "value": [1784284900, "45"]},
      {"metric": {"method": "POST", "endpoint": "/api/orders", "status": "500"}, "value": [1784284900, "2"]},
      {"metric": {"method": "GET", "endpoint": "/api/health", "status": "200"}, "value": [1784284900, "89"]}
    ]
  }
}
```

**Key insight:** ONE metric name (`http_requests_total`) but FIVE time series!
Each unique combination of labels creates a separate series:
- GET /api/users with 200 → series #1 (342 successful user requests)
- GET /api/users with 500 → series #2 (18 failed user requests)
- POST /api/orders with 201 → series #3 (45 successful order creations)
- etc.

This is the power of labels — you can filter and aggregate by any dimension.

---

### Exercise 1.7: Watch a Counter Grow

**First check output:**
```
"342"
```

**After 30 seconds:**
```
"371"
```

**What this shows:** The counter went from 342 → 371. It ONLY increased (by 29).
Counters never go down. Those 29 new requests happened in 30 seconds.
Rate = 29/30 ≈ 0.97 requests per second.

---

### Exercise 1.8: Watch a Gauge Fluctuate

**Output (three readings 5 seconds apart):**
```
"52.34"
"48.71"
"55.12"
```

**What this shows:** The gauge went DOWN (52→48) then UP (48→55).
Unlike counters, gauges freely fluctuate. This is current CPU usage
changing as the simulated load varies.

---
---

## TOPIC 2: Prometheus & Exporters — Expected Outputs

---

### Exercise 2.1: See What Prometheus is Scraping

**Command:** `curl -s "http://localhost:9090/api/v1/targets" | jq '...'`

**Expected Output:**
```
{
  "job": "prometheus",
  "instance": "localhost:9090",
  "health": "up",
  "lastScrape": "2025-07-17T10:45:12.123Z"
}
{
  "job": "node-exporter",
  "instance": "node-exporter:9100",
  "health": "up",
  "lastScrape": "2025-07-17T10:45:14.456Z"
}
{
  "job": "sample-app",
  "instance": "sample-app:8000",
  "health": "up",
  "lastScrape": "2025-07-17T10:45:11.789Z"
}
```

**What this means:**
- Prometheus is monitoring 3 targets
- All show `"health": "up"` = healthy and responding
- `lastScrape` shows when it was last polled
- If a service crashed, you'd see `"health": "down"`

---

### Exercise 2.3: Explore Node Exporter Metrics

**Command:** `curl -s http://localhost:9100/metrics | wc -l`

**Expected Output:**
```
847
```

**What this means:** Node Exporter exposes ~847 lines of metrics!
That's hundreds of time series about the host machine — CPU per core,
memory breakdown, every filesystem, network interfaces, etc.
All collected automatically with zero configuration.

---

**Command:** `curl -s http://localhost:9100/metrics | grep "node_cpu_seconds"`

**Expected Output (partial):**
```
# HELP node_cpu_seconds_total Seconds the CPUs spent in each mode.
# TYPE node_cpu_seconds_total counter
node_cpu_seconds_total{cpu="0",mode="idle"} 5765.42
node_cpu_seconds_total{cpu="0",mode="system"} 187.31
node_cpu_seconds_total{cpu="0",mode="user"} 423.87
node_cpu_seconds_total{cpu="0",mode="iowait"} 12.05
node_cpu_seconds_total{cpu="1",mode="idle"} 5801.22
node_cpu_seconds_total{cpu="1",mode="system"} 165.44
node_cpu_seconds_total{cpu="1",mode="user"} 398.12
```

**How to read this:**
- Each CPU core (cpu="0", cpu="1") has separate counters
- Each mode shows time SPENT in that state:
  - `idle` = doing nothing (high = good, CPU is free)
  - `user` = running user programs
  - `system` = running kernel operations
  - `iowait` = waiting for disk I/O
- These are COUNTERS (cumulative seconds) → use rate() to get percentage

**To calculate CPU usage:** `100 - (rate(idle) / rate(total)) * 100`

---

**Command:** `curl -s http://localhost:9100/metrics | grep "node_memory_Mem"`

**Expected Output:**
```
node_memory_MemAvailable_bytes 5.24288e+09
node_memory_MemFree_bytes 3.14572e+09
node_memory_MemTotal_bytes 8.589934592e+09
```

**How to read this:**
- Total RAM: 8.59 GB (8589934592 bytes)
- Available: 5.24 GB (what programs can use)
- Free: 3.15 GB (completely unused)
- Memory in use: Total - Available = ~3.35 GB (39% used)

---

### Exercise 2.5: Understand Metric Types in Practice

**Counter behavior (run twice, 30 seconds apart):**
```
--- COUNTER (http_requests_total) ---
First check:
http_requests_total{endpoint="/api/users",method="GET",status="200"} 342.0
http_requests_total{endpoint="/api/orders",method="POST",status="201"} 45.0
http_requests_total{endpoint="/api/health",method="GET",status="200"} 89.0

Waiting 30 seconds...

Second check:
http_requests_total{endpoint="/api/users",method="GET",status="200"} 371.0
http_requests_total{endpoint="/api/orders",method="POST",status="201"} 49.0
http_requests_total{endpoint="/api/health",method="GET",status="200"} 98.0
```

**Observation:** Every value INCREASED. 342→371, 45→49, 89→98. Never goes down.

**Gauge behavior (three checks, 5 seconds apart):**
```
--- GAUGE (active_connections) ---
active_connections 87.0
active_connections 92.0
active_connections 84.0
```

**Observation:** Goes up (87→92) then DOWN (92→84). Gauges fluctuate freely.

---

### Exercise 2.7: See How Labels Create Multiple Time Series

**Command:** Count unique series for http_requests_total

**Expected Output:**
```
5
```

**What this means:** The single metric name `http_requests_total` has 5 unique
time series because of label combinations:
1. GET /api/users 200
2. GET /api/users 500
3. POST /api/orders 201
4. POST /api/orders 500
5. GET /api/health 200

This is "cardinality" = 5. In large systems this can be 100,000+!

---

### Exercise 2.8: Check Scrape Duration

**Expected Output:**
```
"prometheus: 0.004523s"
"node-exporter: 0.012847s"
"sample-app: 0.003201s"
```

**What this means:**
- Prometheus scrapes itself in 4.5ms
- Node Exporter takes 12.8ms (more metrics to collect)
- Our app takes 3.2ms
- All are fast! If any exceeded 10s, Prometheus would timeout.

---
---

## TOPIC 3: PromQL Analysis — Expected Outputs

---

### Exercise 3.1: Basic Queries

**CPU query output:**
```
"52.34"
```

**Queue depth output:**
```
"7"
```

**All targets up output:**
```
"prometheus: 1"
"node-exporter: 1"
"sample-app: 1"
```

All targets show "1" = healthy. A crashed service would show "0".

---

### Exercise 3.2: Using rate() on Counters

**Command:** rate(http_requests_total[5m]) — per-second rates

**Expected Output:**
```
"GET /api/users 200: 0.9533 req/s"
"GET /api/users 500: 0.0467 req/s"
"POST /api/orders 201: 0.1267 req/s"
"POST /api/orders 500: 0.0033 req/s"
"GET /api/health 200: 0.2800 req/s"
```

**How to read this:**
- /api/users gets ~0.95 successful GETs per second
- /api/users also gets ~0.05 errors per second (about 5% error rate!)
- /api/orders gets ~0.13 POSTs per second
- Health checks run at 0.28/s

**Total request rate:**
```
"1.4100"
```
The app handles ~1.41 requests per second total.

---

### Exercise 3.3: Calculating Error Rate

**Expected Output:**
```
"4.82"
```

**What this means:** 4.82% of all requests are failing with 5xx errors.
The app simulates a ~5% error rate, so this is expected behavior.

If this suddenly jumped to 20%, that would be an anomaly!

---

### Exercise 3.4: Percentile Latency

**p95 output:**
```
"1.75"
```

**p50 (median) output:**
```
"0.055"
```

**What this means:**
- **Median (p50)**: 50% of requests complete in 55ms — most are fast!
- **95th percentile (p95)**: 5% of requests take longer than 1.75 seconds

This big gap between p50 and p95 shows a "long tail" — most requests
are fast but some are very slow. This is typical of apps with occasional
database timeouts or connection pool exhaustion.

```
Request latency distribution:
  Fast (< 100ms):    ████████████████████████████ 85%
  Medium (< 500ms):  ██ 5%
  Slow (< 2s):       █ 7%
  Very slow (> 2s):  ░ 3%
```

---

### Exercise 3.5: Aggregation

**Grouped by HTTP method:**
```
"GET: 1.28 req/s"
"POST: 0.13 req/s"
```
Reading: GET requests dominate (10x more than POST).

**Grouped by status code:**
```
"200: 1.23 req/s"
"201: 0.13 req/s"
"500: 0.05 req/s"
```
Reading: Most requests succeed (200/201). Only 0.05/s fail (500).

**Grouped by endpoint:**
```
"/api/users: 1.00 req/s"
"/api/health: 0.28 req/s"
"/api/orders: 0.13 req/s"
```
Reading: /api/users is the busiest endpoint.

---

### Exercise 3.6: Using predict_linear()

**Predicted memory in 1 hour:**
```
"278.5"
```

**Current memory:**
```
"262.1"
```

**What this means:**
- Current memory: 262 MB
- Predicted in 1 hour: 278 MB
- Growth rate: about 16 MB per hour
- At this rate, with a 512MB limit: ~15 hours until full

**Limitation:** This is LINEAR extrapolation. It assumes constant growth.
In reality, our app has GC cycles that periodically drop memory. Prophet
would give a better prediction accounting for those cycles.

---

### Exercise 3.7: Static Threshold Limitation

**How often CPU exceeds 50% (static threshold):**
```
1
```
(Currently exceeds → would fire alert)

**How often CPU is > 2σ from mean (dynamic detection):**
```
[]
```
(Empty = currently NOT anomalous)

**The key insight:** Static threshold says "ALERT!" but the dynamic
detection says "this is normal." The CPU might be at 52% but that's
within its normal range. A static threshold doesn't know that.

---

### Exercise 3.8: View Alert Rules

**Expected Output:**
```json
{"name": "HighCpuUsage", "state": "inactive", "query": "100 - (avg by(instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100) > 80"}
{"name": "HighMemoryUsage", "state": "inactive", "query": "(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100 > 85"}
{"name": "DiskSpaceLow", "state": "inactive", "query": "..."}
{"name": "HighErrorRate", "state": "inactive", "query": "..."}
{"name": "HighLatency", "state": "pending", "query": "..."}
{"name": "InstanceDown", "state": "inactive", "query": "up == 0"}
```

**How to read this:**
- `"inactive"` = condition is NOT met (no problem)
- `"pending"` = condition IS met but hasn't lasted long enough yet
- `"firing"` = condition met AND lasted beyond `for` duration → ALERT SENT

In our case, HighLatency might be "pending" because p95 latency is
occasionally above 1s, but it hasn't stayed there for 5 continuous minutes.

---
---

## TOPIC 4: Anomaly Detection — Expected Outputs

---

### Exercise 4.1: Statistical Detection (Python Script)

**Expected Output:**
```
======================================================================
  Statistical Anomaly Detection
======================================================================

──────────────────────────────────────────────────────────────────────
METHOD 1: Z-Score Anomaly Detection
──────────────────────────────────────────────────────────────────────

  Z-Score = (value - mean) / standard_deviation
  If |Z| > 2.5: anomalous.

  Data points: 240
  Mean: 44.82, Std: 14.37
  Anomalies found: 8 (3.3%)

  Top anomalies:
    10:23:45 → CPU=89.1% (Z=3.08)
    10:31:15 → CPU=85.7% (Z=2.84)
    10:42:30 → CPU=12.3% (Z=-2.26)
    10:15:00 → CPU=87.4% (Z=2.96)
    10:38:45 → CPU=83.2% (Z=2.67)

──────────────────────────────────────────────────────────────────────
METHOD 2: Rolling Z-Score (Adaptive Window)
──────────────────────────────────────────────────────────────────────

  Window size: 20 samples
  Rolling anomalies: 5 (2.3%)

  Compare: Simple Z-Score found 8 anomalies
           Rolling Z-Score found 5 anomalies

  Rolling is better because it adapts to the changing pattern!

──────────────────────────────────────────────────────────────────────
METHOD 3: Modified Z-Score (Robust to Outliers)
──────────────────────────────────────────────────────────────────────

  Median: 43.50, MAD: 11.23
  MAD-based anomalies: 6 (2.5%)

  📊 Chart saved to: statistical_anomalies.png
```

**What the chart would show:**
```
┌─────────────────────────────────────────────────────┐
│ Method 1: Simple Z-Score                            │
│                                                     │
│  80%─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ RED DASHED LINE ─ ─  │
│       ╱╲      ×          ╱╲                         │
│      ╱  ╲    ╱ ╲        ╱  ╲     × = anomaly       │
│  50%╱    ╲  ╱   ╲      ╱    ╲                      │
│    ╱      ╲╱     ╲    ╱      ╲                      │
│  20%               ╲  ╱        ╲                    │
│                  ×   ╲╱                              │
│  10%─ ─ ─ ─ ─ ─ ─ RED DASHED LINE ─ ─ ─ ─ ─ ─ ─  │
├─────────────────────────────────────────────────────┤
│ Method 2: Rolling Z-Score (BETTER)                  │
│                                                     │
│      ╱╲ ░░░░░░ GREEN BAND (dynamic ±2.5σ) ░░░░░░░ │
│     ╱  ╲░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│  ──╱────╲──GREEN LINE (rolling mean)───────────── │
│   ╱  ×   ╲░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│  ╱        ╲░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│                                                     │
│  × = points OUTSIDE the green band (true anomalies) │
│  Band MOVES with the data (adapts to trend!)        │
└─────────────────────────────────────────────────────┘
```

**Key insight:** Method 2 (Rolling) has fewer anomalies because it adapts.
A CPU peak during "simulated day" is EXPECTED and won't trigger. Only
unexpected deviations from RECENT behavior get flagged.

---

### Exercise 4.2: Isolation Forest Detection

**Expected Output:**
```
======================================================================
  Isolation Forest Anomaly Detection
======================================================================

──────────────────────────────────────────────────────────────────────
PART 1: Single-Metric Isolation Forest
──────────────────────────────────────────────────────────────────────

  Algorithm: Isolation Forest
  Features used: ['value', 'rate_of_change', 'deviation_from_rolling']
  Data points: 240
  Anomalies detected: 12 (5.0%)

  Anomaly Score Range: [-0.182, 0.253]
  (More negative = more anomalous)

  Top 5 most anomalous points:
    10:23:45 → CPU=89.1%, Change=+22.3%, Score=-0.182
    10:42:30 → CPU=12.3%, Change=-18.7%, Score=-0.165
    10:31:15 → CPU=85.7%, Change=+15.4%, Score=-0.148
    10:55:00 → CPU=78.2%, Change=+19.1%, Score=-0.131
    10:18:30 → CPU=91.0%, Change=+24.6%, Score=-0.127

  📊 Chart saved to: isolation_forest_results.png
```

**What the chart would show:**
```
┌─────────────────────────────────────────────────────┐
│ Plot 1: CPU with Anomalies Marked                    │
│                                                      │
│  90%      ×                 ×                        │
│  70%    ╱   ╲             ╱  ╲                      │
│  50%  ╱╱     ╲    ╱╲    ╱    ╲╲    ╱╲              │
│  30% ╱        ╲  ╱  ╲  ╱      ╲╲  ╱  ╲            │
│  10%            ╲╱    ╲╱        ╲╲╱    ╲            │
│                  ×                                   │
│  × = Red dots (anomalies found by Isolation Forest)  │
├─────────────────────────────────────────────────────┤
│ Plot 2: Anomaly Scores                               │
│                                                      │
│  +0.2 ──────────────────────────────────────────    │
│   0.0 ─────── ORANGE DASHED (decision boundary) ── │
│  -0.1     ▼        ▼             ▼                  │
│  -0.2   █████    ████          ████  (red zones)    │
│                                                      │
│  Points BELOW 0 = flagged as anomalous               │
│  More negative = MORE anomalous                      │
├─────────────────────────────────────────────────────┤
│ Plot 3: Rate of Change                               │
│                                                      │
│  +25%    ×                                           │
│  +10%  ╱  ╲         ╱╲                              │
│    0% ─╱────╲──────╱──╲──────────────               │
│  -10%        ╲    ╱    ╲                            │
│  -20%         ╲  ╱      ×                            │
│                                                      │
│  Anomalies cluster where rate of change is SUDDEN    │
└─────────────────────────────────────────────────────┘
```

**Key insight:** Isolation Forest detects anomalies based on MULTIPLE features
(value + rate_of_change + deviation). A value of 85% might be normal during
a gradual climb, but anomalous if it happened in a sudden +20% jump.

---

### Exercise 4.3: Multi-Metric Correlation

**Expected Output:**
```
======================================================================
  Multi-Metric Correlation Anomaly Detection
======================================================================

Fetching metrics from Prometheus...
  Fetched 120 data points across 7 metrics

──────────────────────────────────────────────────────────────────────
STEP 1: Metric Correlation Matrix
──────────────────────────────────────────────────────────────────────

  Correlation Matrix:
                cpu  memory_mb  queue  connections  request_rate  error_rate  latency
  cpu          1.00      0.12   0.72         0.89         0.45        0.34     0.28
  memory_mb    0.12      1.00   0.05         0.08         0.03        0.01     0.02
  queue        0.72      0.05   1.00         0.68         0.31        0.55     0.61
  connections  0.89      0.08   0.68         1.00         0.52        0.29     0.25
  request_rate 0.45      0.03   0.31         0.52         1.00        0.15     0.12
  error_rate   0.34      0.01   0.55         0.29         0.15        1.00     0.78
  latency      0.28      0.02   0.61         0.25         0.12        0.78     1.00

  Strong correlations (|r| > 0.5):
    cpu             ↔ connections     : r=+0.89 ↑↑
    cpu             ↔ queue           : r=+0.72 ↑↑
    queue           ↔ connections     : r=+0.68 ↑↑
    queue           ↔ latency         : r=+0.61 ↑↑
    error_rate      ↔ latency         : r=+0.78 ↑↑
    error_rate      ↔ queue           : r=+0.55 ↑↑
    connections     ↔ request_rate    : r=+0.52 ↑↑
```

**What the correlation matrix tells you:**
- CPU and connections are strongly correlated (0.89) — more connections = more CPU
- Error rate and latency are strongly correlated (0.78) — slow responses cause errors
- Queue depth correlates with latency (0.61) — backed up queue = slow responses
- Memory is INDEPENDENT of everything (0.01-0.12) — it grows on its own (memory leak!)

**This reveals the causal chain:**
```
More connections → Higher CPU → Deeper queue → Higher latency → More errors
(Memory grows independently — it's a leak, not load-related)
```

**Multi-metric anomaly detection output (continued):**
```
──────────────────────────────────────────────────────────────────────
STEP 2: Multi-Metric Isolation Forest
──────────────────────────────────────────────────────────────────────

  Metrics used: ['cpu', 'memory_mb', 'queue', 'connections', 'request_rate', 'error_rate', 'latency']
  Multi-metric anomalies: 4 (3.3%)

  These are points where the COMBINATION of metrics is unusual,
  even if individual metrics might look normal!

──────────────────────────────────────────────────────────────────────
STEP 3: Anomaly Explanation (WHY is it anomalous?)
──────────────────────────────────────────────────────────────────────

  Anomaly #1 at 10:31:22 (score: -0.142)
    Contributing factors:
      latency_p95    : HIGH (z=+3.8, value=4.2s)
      error_rate     : HIGH (z=+3.1, value=18.5%)
      queue_depth    : HIGH (z=+2.7, value=38)

  Anomaly #2 at 10:45:07 (score: -0.128)
    Contributing factors:
      cpu            : LOW (z=-2.9, value=8.2%)
      connections    : LOW (z=-2.4, value=12)
      request_rate   : LOW (z=-2.1, value=0.1 req/s)

  Anomaly #3 at 10:52:30 (score: -0.115)
    Contributing factors:
      memory_mb      : HIGH (z=+3.2, value=485MB)
      queue_depth    : HIGH (z=+2.5, value=35)
      latency_p95    : HIGH (z=+2.2, value=3.1s)
```

**What the explanations tell you:**
- Anomaly #1: Classic overload — latency + errors + queue all spiked together
- Anomaly #2: Opposite problem — everything dropped (possible network issue or restart)
- Anomaly #3: Memory near capacity, causing cascading slowness

**Without multi-metric detection:** CPU=8% alone doesn't trigger a single-metric alert.
But CPU=8% + connections=12 + requests=0.1/s TOGETHER scream "something is broken!"

---

### Exercise 4.4: Real-Time Detection (Live)

**Expected Output (running for 5 minutes):**
```
═══════════════════════════════════════════════════════════════════════
  Real-Time Anomaly Detection RUNNING
  Monitoring: ['cpu', 'memory_mb', 'queue', 'connections']
  Check interval: 30s
  Training window: 200 samples
═══════════════════════════════════════════════════════════════════════

  Collecting initial training data...

  [10:00:00] 📊 Collecting data... (1/30 samples)
  [10:00:30] 📊 Collecting data... (2/30 samples)
  [10:01:00] 📊 Collecting data... (3/30 samples)
  ...
  [10:14:30] 📊 Collecting data... (30/30 samples)
  [10:15:00] 🔄 Model retrained on 30 samples
  [10:15:00] ✅ Normal (score: +0.142) │ cpu=48 | memory_mb=265 | queue=6 | connections=85
  [10:15:30] ✅ Normal (score: +0.128) │ cpu=51 | memory_mb=266 | queue=5 | connections=91
  [10:16:00] ✅ Normal (score: +0.115) │ cpu=45 | memory_mb=266 | queue=7 | connections=82
  [10:16:30] ✅ Normal (score: +0.098) │ cpu=55 | memory_mb=267 | queue=4 | connections=95
  [10:17:00] ✅ Normal (score: +0.134) │ cpu=42 | memory_mb=267 | queue=6 | connections=78

  [10:17:30] 🚨 ANOMALY DETECTED (score: -0.152)
    Values: cpu=82.1, memory_mb=268.4, queue=35.0, connections=145.0
    Reason: cpu=82.1 (HIGH, z=+2.8) | queue=35.0 (HIGH, z=+3.1) | connections=145.0 (HIGH, z=+2.4)

  [10:18:00] ✅ Normal (score: +0.067) │ cpu=62 | memory_mb=268 | queue=12 | connections=110
  [10:18:30] ✅ Normal (score: +0.112) │ cpu=53 | memory_mb=269 | queue=7 | connections=92
  ...

═══════════════════════════════════════════════════════════════════════
  Detection stopped.
  Total checks: 45
  Total anomalies: 3
  Anomaly rate: 6.7%
═══════════════════════════════════════════════════════════════════════
```

**What this shows:**
1. First ~15 minutes: LEARNING phase (collects 30 samples to understand "normal")
2. After training: DETECTION phase — scores each new reading
3. Most readings are ✅ Normal with positive scores
4. Occasionally 🚨 ANOMALY when the combination is unusual
5. Each anomaly comes with an EXPLANATION of which metrics are off

---

### Exercise 4.5: Manual PromQL Anomaly Detection (No Python)

**Command:** Check if CPU is > 2σ from recent mean

**If currently NORMAL:**
```json
{
  "data": {
    "result": []
  }
}
```
Empty result = current value is within 2 standard deviations of recent mean = NORMAL.

**If currently ANOMALOUS:**
```json
{
  "data": {
    "result": [
      {
        "metric": {"__name__": "app_cpu_usage_percent", "instance": "sample-app:8000"},
        "value": [1784285000, "87.3"]
      }
    ]
  }
}
```
Non-empty result = current value IS anomalous (87.3% is far from recent average).

---
---

## TOPIC 5: Forecasting — Expected Outputs

---

### Exercise 5.1: Linear Forecast

**Expected Output:**
```
======================================================================
  Linear Trend Forecasting
======================================================================

──────────────────────────────────────────────────────────────────────
FORECAST 1: Memory Usage (Linear Trend)
──────────────────────────────────────────────────────────────────────

  Historical data: 120 points over 60 minutes
  Current memory: 274.5 MB
  Growth rate: 8.42 MB/hour (202.1 MB/day)
  R² score: 0.3421 (1.0 = perfect linear fit)

  ⚠️  At current rate, memory will reach 500MB in:
     26.8 hours (2025-07-18 13:15)

──────────────────────────────────────────────────────────────────────
FORECAST 2: Request Rate with Confidence Intervals
──────────────────────────────────────────────────────────────────────

  R² = 0.0823
  ⚠️  Low R² means the data is NOT linear!
  Linear regression is a POOR fit for this metric.
  This metric likely has seasonality → use Holt-Winters or Prophet instead.

  📊 Charts saved to: linear_forecast_memory.png, linear_forecast_requests.png
```

**What the memory chart would show:**
```
┌───────────────────────────────────────────────────────────────┐
│  Memory Usage: Linear Forecast                                 │
│                                                                │
│  500MB ─ ─ ─ ─ ─ ORANGE DASHED (threshold) ─ ─ ─ ─ ─ ─ ─ ─ │
│                                          ╱ ░░░ (±2 RMSE)     │
│  400MB                               ╱╱░░░░░░                │
│                                    ╱╱░░░░░░░░  RED DASHED     │
│  300MB                          ╱╱░░░░░░░░░░  (forecast)     │
│         ●●●●●●●●●●●●●●●●●●●╱╱░░░░░░░░░░░░                  │
│  250MB  ●  BLUE SOLID  ●●●╱╱░░░░░░░░░░░░░░                  │
│         (historical)    ╱╱                                    │
│  200MB               ╱╱                                       │
│                                                                │
│  ───────────────┼────────────────────────────────── Time ───▶ │
│              NOW           +1h          +2h                    │
└───────────────────────────────────────────────────────────────┘
```

**Key insights:**
- R² = 0.34 for memory → linear model is a MODERATE fit (memory has GC cycles)
- R² = 0.08 for request rate → linear model is TERRIBLE (requests are seasonal!)
- Linear forecast says 26.8 hours to fill — but this ignores GC events that drop memory

---

### Exercise 5.2: Holt-Winters Forecast

**Expected Output:**
```
======================================================================
  Holt-Winters Forecasting (Triple Exponential Smoothing)
======================================================================

──────────────────────────────────────────────────────────────────────
STEP 1: Decompose Time Series into Components
──────────────────────────────────────────────────────────────────────

  Data points: 120
  Seasonal period: 24 samples
  Trend range: 32.1 → 38.5
  Seasonal amplitude: 28.4
  Residual std: 4.82

──────────────────────────────────────────────────────────────────────
STEP 2: Holt-Winters Forecast
──────────────────────────────────────────────────────────────────────

  Model Parameters:
    Smoothing level (α): 0.4521
    Smoothing trend (β): 0.0234
    Smoothing seasonal (γ): 0.3187
    AIC: 892.34

  Forecast Accuracy (hold-out test):
    MAE:  4.32
    MAPE: 9.8%
    RMSE: 5.67

  📊 Chart saved to: holtwinters_forecast.png
```

**What the decomposition chart would show:**
```
┌───────────────────────────────────────────────────────────┐
│ Observed (raw data):                                       │
│    ╱╲    ╱╲    ╱╲    ╱╲    ╱╲   (oscillating)            │
│   ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲  ╱                             │
│  ╱    ╲╱    ╲╱    ╲╱    ╲╱                                │
├───────────────────────────────────────────────────────────┤
│ Trend (extracted):                                         │
│  ────────────────────────╱─── (slight upward)             │
├───────────────────────────────────────────────────────────┤
│ Seasonal (extracted):                                      │
│    ∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿ (repeating wave, period=24)    │
├───────────────────────────────────────────────────────────┤
│ Residual (noise):                                          │
│  ⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓⁓ (random, small amplitude)     │
└───────────────────────────────────────────────────────────┘
```

**What the forecast chart would show:**
```
┌───────────────────────────────────────────────────────────┐
│                                                            │
│         Historical          │      Forecast               │
│    ╱╲    ╱╲    ╱╲    ╱╲    │   ╱╲    ╱╲    ╱╲           │
│   ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲  │  ╱░░╲░░╱░░╲░░╱░░╲          │
│  ╱    ╲╱    ╲╱    ╲╱    ╲  │ ╱░░░░╲╱░░░░╲╱░░░░╲         │
│  BLUE SOLID              │  │RED DASHED + RED SHADING     │
│                          │  │(forecast + confidence)       │
│                        NOW  │                              │
└───────────────────────────────────────────────────────────┘
```

**Key insight:** Unlike linear regression, Holt-Winters REPRODUCES the
seasonal pattern in the forecast! It predicts the oscillation will continue,
not just a straight line. MAPE of 9.8% means predictions are ~10% off on average.

---

### Exercise 5.3: Prophet Forecast

**Expected Output:**
```
======================================================================
  Facebook Prophet Forecasting for Infrastructure Metrics
======================================================================

──────────────────────────────────────────────────────────────────────
STEP 1: Preparing Data for Prophet
──────────────────────────────────────────────────────────────────────

  Data shape: (500, 2)
  Time range: 2025-07-17 02:00 → 2025-07-17 10:20
  Value range: 8.2 → 91.4

──────────────────────────────────────────────────────────────────────
STEP 2: Training Prophet Model
──────────────────────────────────────────────────────────────────────

  Training Prophet... (this may take a moment)
  ✅ Model trained!

  Detected 5 trend changepoints
  Last changepoint: 2025-07-17 09:42:00

──────────────────────────────────────────────────────────────────────
STEP 3: Generating Forecast
──────────────────────────────────────────────────────────────────────

  Forecast horizon: 120 minutes (2.0 hours)
  Forecast points: 120

  Forecasted values (next 2 hours):
    Min: 18.3
    Max: 72.8
    Mean: 44.6
    Uncertainty range: [5.1, 88.4]

──────────────────────────────────────────────────────────────────────
STEP 4: Prophet as Anomaly Detector
──────────────────────────────────────────────────────────────────────

  Historical anomalies (outside 95% CI): 12 / 500 (2.4%)

──────────────────────────────────────────────────────────────────────
STEP 5: Forecast Components
──────────────────────────────────────────────────────────────────────

  trend     : range [33.21, 39.87], amplitude=6.66
  daily     : range [-14.52, 15.23], amplitude=29.75
  weekly    : range [-3.41, 4.12], amplitude=7.53

──────────────────────────────────────────────────────────────────────
STEP 6: Capacity Planning - When Will We Hit Limits?
──────────────────────────────────────────────────────────────────────

  ⚠️  CAPACITY WARNING:
     Metric may exceed 80% within 45 minutes
     First potential breach: 11:05
     Predicted value: 68.2% (CI: [52.1, 84.3])

  📊 Charts saved to: prophet_forecast.png
```

**What the Prophet chart would show:**
```
┌───────────────────────────────────────────────────────────────────┐
│ Plot 1: Prophet Forecast with Confidence Intervals                 │
│                                                                    │
│  90% │         ×                    ░░░░░╱╲░░░░░                  │
│      │    ╱╲  ╱ ╲    ╱╲         ░░╱░░░╱░░╲░░░╲░░░                │
│  60% │   ╱  ╲╱   ╲  ╱  ╲      ░╱░░░╱░░░░░╲░░░╲░░                │
│      │  ╱        ╲╲╱    ╲   ░╱░░╱░░░░░░░░░╲░░░╲░                │
│  30% │ ╱          ╲      ╲ ╱░╱░░░░░░░░░░░░░╲░░░╲                │
│      │╱                    ╳░░░░░░░░░░░░░░░░░╲░░░                │
│  10% │                   ░░░░░░░░░░░░░░░░░░░░░░░░                │
│      ├──────────────────┼────────────────────────── Time ──▶     │
│      │    Historical    │NOW│      Forecast                       │
│      │                  │   │                                     │
│  BLUE dots = actual data                                          │
│  RED line = Prophet's prediction                                  │
│  PINK shading = 95% confidence interval                           │
│  × = anomalies (actual points outside the CI)                     │
├───────────────────────────────────────────────────────────────────┤
│ Plot 2: Trend + Changepoints                                       │
│                                                                    │
│  40% │                    ╱──────── (trend increases)              │
│  35% │──────────────────╱    ▲ = changepoint detected             │
│  33% │                 ╱                                           │
│      │ Orange vertical lines mark where trend changed              │
├───────────────────────────────────────────────────────────────────┤
│ Plot 3: Seasonal Components                                        │
│                                                                    │
│  +15% │    ╱╲         PURPLE = daily seasonality                  │
│    0% │───╱──╲────────── peaks at "noon", drops at "night"        │
│  -15% │  ╱    ╲╱                                                  │
│       │                                                            │
│   +4% │  ╱╲   ORANGE = weekly seasonality (smaller effect)        │
│    0% │─╱──╲───────                                               │
│   -3% │╱    ╲╱                                                    │
└───────────────────────────────────────────────────────────────────┘
```

**Key insights from Prophet:**
1. It automatically found the daily seasonal pattern (±15% amplitude)
2. It detected 5 changepoints where the trend shifted
3. The confidence interval WIDENS into the future (less certain further out)
4. 2.4% of historical points were anomalies (outside the CI)
5. It predicts a potential capacity breach in 45 minutes

---

### Exercise 5.4: Capacity Planning Pipeline

**Expected Output:**
```
======================================================================
  CAPACITY PLANNING PIPELINE
  Analyzing infrastructure resources...
======================================================================

  Analyzing: CPU Usage...
  Analyzing: Memory...
  Analyzing: Queue Depth...
  Analyzing: Connections...


╔════════════════════════════════════════════════════════════════════════╗
║  CAPACITY PLANNING REPORT                                             ║
║  Generated: 2025-07-17 10:45:23                                       ║
╠════════════════════════════════════════════════════════════════════════╣
║  ✅ CPU Usage           │ 52.3/100.0 % (52.3%)                        ║
║     Growth: ↑ 2.14 %/hour                                            ║
║                                                                       ║
║  ⚠️  Memory              │ 274.5/512.0 MB (53.6%)                      ║
║     Growth: ↑ 8.42 MB/hour                                           ║
║     ⏰ Critical in: 25.3 hours                                        ║
║                                                                       ║
║  ✅ Queue Depth          │ 7.0/50.0 items (14.0%)                     ║
║     Growth: ↑ 0.34 items/hour                                         ║
║                                                                       ║
║  ✅ Connections          │ 89.0/200.0 conns (44.5%)                   ║
║     Growth: ↑ 1.23 conns/hour                                         ║
║                                                                       ║
╠════════════════════════════════════════════════════════════════════════╣
║  RECOMMENDATIONS:                                                     ║
║  ⚠️  Memory: Plan expansion within 24h                                 ║
║  ✅ All other resources healthy. No action needed.                     ║
╚════════════════════════════════════════════════════════════════════════╝

  📊 Capacity chart saved to: capacity_report.png
```

**What the capacity chart would show:**
```
┌───────────────────────────────────────────────────────────────────┐
│ CPU Usage [OK] - 52.3% used                                       │
│  100% ─── RED LINE (capacity) ─────────────────────────────────── │
│   80% ─── ORANGE DASHED (warning 80%) ────── ─ ─ ─ ─ ─ ─ ─ ─ ── │
│   52% ●●●●●●●●●●●●●●●●●●●●── ─ ─ ─ (forecast, won't hit limit) │
│      ├────────── Historical ──────┼──── Forecast ────────────────▶│
├───────────────────────────────────────────────────────────────────┤
│ Memory [WARNING] - 53.6% used                                     │
│  512MB ─── RED LINE (capacity) ───────────────────────────╱─────  │
│  410MB ─── ORANGE DASHED (warning 80%) ──────────── ╱╱ ─ ─ ─ ─── │
│  275MB ●●●●●●●●●●●●●●●●●●●●●╱╱╱╱╱╱╱╱╱╱╱╱  RED FORECAST LINE   │
│      ├────────── Historical ──────┼──── Forecast ──────┼─────────▶│
│                                 NOW               BREACH in 25h   │
├───────────────────────────────────────────────────────────────────┤
│ Queue Depth [OK] - 14.0% used                                     │
│   50  ─── RED LINE (capacity) ─────────────────────────────────── │
│    7  ●●●●●●●●●●●●●●●●●●●●── ─ ─ ─ (safe, well below limit)    │
├───────────────────────────────────────────────────────────────────┤
│ Connections [OK] - 44.5% used                                     │
│  200  ─── RED LINE (capacity) ─────────────────────────────────── │
│   89  ●●●●●●●●●●●●●●●●●●●●── ─ ─ ─ (growing slowly, safe)      │
└───────────────────────────────────────────────────────────────────┘
```

**How an SRE team would use this report:**
1. CPU: Green, no action needed
2. Memory: ⚠️ Will hit critical in ~25 hours → schedule a restart or fix the memory leak
3. Queue: Green, plenty of headroom
4. Connections: Green, growing slowly but won't hit limit soon

**In production, this would run as a cron job every 6 hours and post to Slack.**

---

### Exercise 5.5: Prometheus-Only Forecasting (No Python)

**Command:** `predict_linear(app_memory_usage_bytes[30m], 3600) / 1024 / 1024`

**Expected Output:**
```
"285.7"
```

**Command:** Current memory for comparison

**Expected Output:**
```
"274.5"
```

**What this tells you:**
- Current: 274.5 MB
- Predicted in 1 hour: 285.7 MB  
- Difference: +11.2 MB growth expected in next hour
- This is Prometheus's BUILT-IN linear prediction (limited but useful)

**Command:** Rate of memory growth

**Expected Output:**
```
"3127.45"
```

**What this means:** Memory is growing at ~3127 bytes/second = ~11.3 MB/hour.
At this rate: (512 - 274.5) / 11.3 = ~21 hours until 512MB limit.

**Command:** Will filesystem be full within 4 hours?

**Expected Output:**
```
[]
```

Empty result = NO, no filesystem will be full in 4 hours. Safe!

If it returned data, it would mean a filesystem IS predicted to fill up — urgent action needed.

---
---

## SUMMARY: What You Learned From All Outputs

```
Topic 1: You can see metrics flowing (counters going up, gauges fluctuating)
         and query them through Prometheus. All 5 services work together.

Topic 2: Node Exporter gives 800+ OS metrics automatically.
         Labels multiply one metric into many time series.
         Scraping takes milliseconds.

Topic 3: rate() turns useless counters into useful "per second" rates.
         Error rate = 4.82%, p95 latency = 1.75s.
         Static thresholds fire when they shouldn't (false positives)
         and miss what they should catch (gradual degradation).

Topic 4: Statistical Z-Score finds 8 anomalies, Rolling Z finds 5 (better!).
         Isolation Forest uses multiple features (value + change + deviation).
         Multi-metric detection finds problems invisible to single-metric.
         Real-time detector runs continuously with explanations.

Topic 5: Linear forecast predicts memory full in 25h (but R²=0.34, mediocre fit).
         Holt-Winters captures seasonality (MAPE 9.8%).
         Prophet handles multiple seasonalities + changepoints + uncertainty.
         Capacity planner gives actionable "time to critical" for each resource.
```

**The progression:**
```
Static threshold: "CPU > 80% → alert"              (dumb, noisy)
Statistical:      "CPU > 2σ from recent mean"       (better, adapts)
Isolation Forest: "This combination is unusual"     (smart, multi-metric)
Prophet forecast: "CPU will exceed 80% in 45 min"   (proactive, prevents)
```

**This is the evolution from traditional monitoring to AIOps.**
