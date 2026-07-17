# Topic 2: Collecting the Data Fuel — Prometheus & Exporters

---

## PART A: THEORY (Read and Understand First)

---

### 2.1 What is Prometheus? (The Big Picture)

Prometheus is a **monitoring system** that:
1. **Scrapes** (pulls) numeric data from your applications
2. **Stores** that data as time series
3. **Queries** the data using its own language (PromQL)
4. **Alerts** when conditions are met

Think of it as: "A robot that visits all your services every 15 seconds,
asks 'How are you doing?', writes down the answer, and keeps a record going
back weeks or months."

---

### 2.2 Pull vs Push: How Prometheus Collects Data

There are two approaches to collecting metrics:

#### Push Model (used by DataDog, CloudWatch, StatsD)
```
Your App → sends data → Monitoring Server

"Hey server, my CPU is 45%!"
"Hey server, I got 10 requests!"
```

- App must know WHERE to send data
- If the monitoring server is down, data is lost
- Hard to know if an app crashed (it just stops sending)

#### Pull Model (used by Prometheus) ✅
```
Prometheus → asks your app → gets data

"Hey app, give me your metrics!"
"Here you go: cpu=45%, requests=10"
```

- App just serves metrics on an HTTP endpoint (like a web page)
- Prometheus decides WHAT and WHEN to scrape
- If an app stops responding, Prometheus knows immediately (it's "down")
- Simple: your app just needs one HTTP endpoint

**In simple terms**: Your app serves a "status page" with numbers.
Prometheus visits that page regularly and records the numbers.

---

### 2.3 What Does the /metrics Endpoint Look Like?

Every service monitored by Prometheus exposes an HTTP endpoint (usually `/metrics`)
that returns plain text in a specific format:

```
# HELP http_requests_total Total number of HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/users",status="200"} 3847
http_requests_total{method="POST",endpoint="/api/orders",status="201"} 512

# HELP app_cpu_usage_percent Current CPU usage
# TYPE app_cpu_usage_percent gauge
app_cpu_usage_percent 45.3

# HELP http_request_duration_seconds Response time distribution
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.1"} 3200
http_request_duration_seconds_bucket{le="0.5"} 3700
http_request_duration_seconds_bucket{le="1.0"} 3850
http_request_duration_seconds_bucket{le="+Inf"} 3900
http_request_duration_seconds_count 3900
http_request_duration_seconds_sum 487.5
```

**Format rules:**
- `# HELP` = human-readable description
- `# TYPE` = counter, gauge, histogram, or summary
- `metric_name{label="value"} number` = the actual data
- One line per time series

---

### 2.4 What is an "Exporter"?

Not every system can be modified to serve `/metrics`. Think about:
- Linux kernel (you can't change its code)
- MySQL database (it has its own monitoring commands)
- Network switches (they speak SNMP, not HTTP)

An **exporter** is a small program that:
1. Connects to some system
2. Reads its metrics (in whatever format that system uses)
3. Translates them into Prometheus format
4. Serves them on `/metrics`

```
┌──────────┐         ┌─────────────┐         ┌────────────┐
│  Linux   │ ──────▶ │   Node      │ ──────▶ │ Prometheus │
│  Kernel  │ (reads  │  Exporter   │ (serves  │            │
│          │  /proc) │             │ /metrics)│            │
└──────────┘         └─────────────┘         └────────────┘

┌──────────┐         ┌─────────────┐         ┌────────────┐
│  MySQL   │ ──────▶ │   MySQL     │ ──────▶ │ Prometheus │
│ Database │ (SQL    │  Exporter   │ (serves  │            │
│          │ queries)│             │ /metrics)│            │
└──────────┘         └─────────────┘         └────────────┘
```

**Common exporters:**
| Exporter | What It Monitors | Metrics You Get |
|----------|-----------------|-----------------|
| Node Exporter | Linux/Unix OS | CPU, memory, disk, network |
| Windows Exporter | Windows OS | Same but for Windows |
| MySQL Exporter | MySQL database | Queries/sec, connections, slow queries |
| Blackbox Exporter | Any URL | Is it up? Response time? SSL expiry? |
| cAdvisor | Docker containers | Container CPU, memory, network |

---

### 2.5 Node Exporter: Your First Exporter (In Detail)

Node Exporter is one of the most important exporters. It reads data from
Linux's `/proc` and `/sys` filesystems to give you:

**CPU Metrics:**
```
node_cpu_seconds_total{cpu="0", mode="user"}    → Time spent running user programs
node_cpu_seconds_total{cpu="0", mode="system"}  → Time spent in kernel
node_cpu_seconds_total{cpu="0", mode="idle"}    → Time doing nothing
node_cpu_seconds_total{cpu="0", mode="iowait"}  → Time waiting for disk
```

To get "CPU usage %", you calculate: `100 - (idle / total) * 100`

**Memory Metrics:**
```
node_memory_MemTotal_bytes      → Total RAM (e.g., 16GB)
node_memory_MemAvailable_bytes  → RAM available for programs
node_memory_MemFree_bytes       → Completely unused RAM
node_memory_Buffers_bytes       → RAM used for disk caching
```

**Disk Metrics:**
```
node_filesystem_size_bytes{mountpoint="/"}      → Total disk size
node_filesystem_avail_bytes{mountpoint="/"}     → Available disk space
node_disk_read_bytes_total                      → Total bytes read from disk
node_disk_written_bytes_total                   → Total bytes written to disk
```

**Network Metrics:**
```
node_network_receive_bytes_total{device="eth0"}   → Bytes received
node_network_transmit_bytes_total{device="eth0"}  → Bytes sent
```

---

### 2.6 How Prometheus Knows What to Scrape: Configuration

Prometheus reads a YAML configuration file that tells it:
- How often to scrape (e.g., every 15 seconds)
- WHERE to scrape (list of targets)
- Any special rules

```yaml
global:
  scrape_interval: 15s    # Visit targets every 15 seconds

scrape_configs:
  - job_name: 'my-app'           # Friendly name
    static_configs:
      - targets: ['app:8000']    # hostname:port to scrape

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
```

**Key concepts:**
- **job_name**: A label automatically added to all metrics from this target
- **targets**: List of hostname:port pairs
- **scrape_interval**: Can be set globally or per-job
- **metrics_path**: Defaults to `/metrics` but can be changed

---

### 2.7 Service Discovery: Finding Targets Automatically

In the config above, we hardcoded the targets. But in real production with
100+ services that come and go, you can't manually update a file.

**Service Discovery** lets Prometheus find targets automatically:

| Method | How It Works | Used In |
|--------|-------------|---------|
| `kubernetes_sd` | Reads Kubernetes API for pods | Kubernetes clusters |
| `consul_sd` | Reads Consul service registry | Consul-based infrastructure |
| `dns_sd` | DNS SRV record lookups | Traditional infrastructure |
| `file_sd` | Reads target list from JSON/YAML file | Simple automation |
| `ec2_sd` | AWS EC2 instance discovery | AWS environments |

For this tutorial, we use `static_configs` (hardcoded) because our lab is small.

---

### 2.8 How to Instrument YOUR OWN Application

If you write an app and want Prometheus to monitor it, you add a few lines
of code to expose metrics. Here's what it looks like conceptually:

```python
# 1. Define what you want to measure
request_counter = Counter('http_requests_total', 'Total requests', ['method', 'status'])
response_time = Histogram('http_request_duration_seconds', 'Response times')

# 2. Update metrics when things happen
def handle_request(request):
    start = time.now()
    response = process(request)      # Do actual work
    duration = time.now() - start

    request_counter.labels(method='GET', status='200').increment()
    response_time.observe(duration)

    return response

# 3. Serve metrics on /metrics (Prometheus will scrape this)
app.route('/metrics') → return all_metrics_as_text()
```

That's it! Prometheus does the rest (scraping, storing, alerting).

---

### 2.9 The Prometheus Architecture (Complete Picture)

```
                         ┌──────────────────────────────────────┐
                         │           PROMETHEUS                  │
                         │                                      │
YOUR SERVICES            │  ┌──────────┐    ┌───────────────┐  │
┌────────────┐           │  │ Retrieval │    │    TSDB       │  │
│ Your App   │◀──────────│──│ (Scraper) │───▶│ (Time Series  │  │
│ /metrics   │  HTTP GET │  │           │    │  Database)    │  │
└────────────┘           │  └──────────┘    └───────┬───────┘  │
                         │                          │           │
┌────────────┐           │  ┌──────────┐    ┌──────▼────────┐  │
│ Node       │◀──────────│──│ Service   │    │  Rule Engine  │  │
│ Exporter   │           │  │ Discovery │    │  (evaluates   │  │
└────────────┘           │  └──────────┘    │   alert rules) │  │
                         │                   └───────┬───────┘  │
┌────────────┐           │  ┌──────────┐            │           │
│ MySQL      │◀──────────│──│ HTTP API │    ┌───────▼────────┐  │
│ Exporter   │           │  │ (PromQL  │    │  Alertmanager  │  │
└────────────┘           │  │  queries)│    │  (routes       │  │
                         │  └──────────┘    │   notifications│  │
                         │       ▲           └───────────────┘  │
                         └───────┼──────────────────────────────┘
                                 │
                         ┌───────┴───────┐
                         │    GRAFANA    │
                         │  (dashboards) │
                         └───────────────┘
```

**Data flow:**
1. Retrieval scrapes /metrics from all targets every N seconds
2. Data goes into TSDB (time-series database)
3. Rule Engine evaluates alert conditions
4. Alertmanager handles notifications (email, Slack, PagerDuty)
5. Grafana queries TSDB via HTTP API to draw dashboards
6. Users query via HTTP API or Prometheus UI using PromQL

---

### 2.10 Data Storage: The TSDB

Prometheus stores data in its own Time Series Database (TSDB).

Key facts:
- **Retention**: Default 15 days (configurable — we set 30 days)
- **Storage format**: Highly compressed, optimized for time-series patterns
- **On disk**: About 1-2 bytes per sample (very efficient!)
- **NOT for long-term**: For months/years of data, use Thanos or Cortex

Each unique combination of metric name + labels = one time series:
```
http_requests_total{method="GET", status="200"}   → Time Series #1
http_requests_total{method="GET", status="500"}   → Time Series #2
http_requests_total{method="POST", status="201"}  → Time Series #3
```

---

### 2.11 What is Alertmanager?

When Prometheus detects a problem (alert rule fires), it sends the alert
to **Alertmanager**, which handles:

- **Grouping**: "These 10 alerts are all about the same thing" → send ONE notification
- **Silencing**: "I know about this, stop alerting me for 2 hours"
- **Routing**: "Critical alerts → PagerDuty, Warnings → Slack"
- **Deduplication**: Don't send the same alert twice

---

### 2.12 Key Vocabulary for This Topic

| Term | Meaning |
|------|---------|
| **Scrape** | One pull of metrics from a target |
| **Scrape interval** | How often Prometheus pulls (e.g., every 15s) |
| **Target** | A host:port that serves /metrics |
| **Job** | A group of similar targets (e.g., all your web servers) |
| **Instance** | A specific target within a job |
| **Exporter** | Translates foreign metrics into Prometheus format |
| **TSDB** | Time Series Database — where Prometheus stores data |
| **Retention** | How long data is kept before deletion |
| **Instrumentation** | Adding metric code to your application |

---
---

## PART B: HANDS-ON EXERCISES

---

### Exercise 2.1: See What Prometheus is Scraping

```bash
# List all targets and their health
curl -s "http://localhost:9090/api/v1/targets" | jq '.data.activeTargets[] | {job: .labels.job, instance: .labels.instance, health: .health, lastScrape: .lastScrape}'
```

You should see 3 healthy targets:
- `prometheus` (monitors itself)
- `node-exporter` (OS metrics)
- `sample-app` (our application)

---

### Exercise 2.2: Examine Prometheus Configuration

```bash
# See what config Prometheus is using
curl -s "http://localhost:9090/api/v1/status/config" | jq -r '.data.yaml'
```

Look for the `scrape_configs` section — this is where targets are defined.

---

### Exercise 2.3: Explore Node Exporter Metrics

```bash
# See ALL metrics from Node Exporter (there are hundreds!)
curl -s http://localhost:9100/metrics | wc -l

# Just CPU metrics
curl -s http://localhost:9100/metrics | grep "node_cpu_seconds"

# Memory metrics
curl -s http://localhost:9100/metrics | grep "node_memory_Mem"

# Filesystem (disk) metrics
curl -s http://localhost:9100/metrics | grep "node_filesystem_avail"
```

---

### Exercise 2.4: Explore Our Custom App Metrics

```bash
# See all metrics from our sample application
curl -s http://localhost:8000/metrics

# Just the HTTP request counter
curl -s http://localhost:8000/metrics | grep "http_requests_total"

# The latency histogram buckets
curl -s http://localhost:8000/metrics | grep "http_request_duration_seconds_bucket"

# Current gauges
curl -s http://localhost:8000/metrics | grep -E "(cpu_usage|memory_usage|queue_depth|active_connections)"
```

---

### Exercise 2.5: Understand the Metric Types in Practice

```bash
# COUNTER example — run this twice with 30s gap, see it ONLY increase:
echo "--- COUNTER (http_requests_total) ---"
curl -s http://localhost:8000/metrics | grep 'http_requests_total{' | head -3
echo ""
echo "Waiting 30 seconds..."
sleep 30
curl -s http://localhost:8000/metrics | grep 'http_requests_total{' | head -3

# GAUGE example — changes each time:
echo ""
echo "--- GAUGE (active_connections) ---"
curl -s http://localhost:8000/metrics | grep "active_connections "
sleep 5
curl -s http://localhost:8000/metrics | grep "active_connections "
sleep 5
curl -s http://localhost:8000/metrics | grep "active_connections "
```

---

### Exercise 2.6: Query Through Prometheus (Not Directly)

When you query through Prometheus, it knows the HISTORY:

```bash
# Current CPU (instant query)
curl -s "http://localhost:9090/api/v1/query?query=app_cpu_usage_percent"

# CPU over the last 5 minutes (range query) - shows multiple data points
curl -s "http://localhost:9090/api/v1/query_range?query=app_cpu_usage_percent&start=$(date -d '5 minutes ago' +%s 2>/dev/null || date -v-5M +%s)&end=$(date +%s)&step=30s" | jq '.data.result[0].values | length'
```

---

### Exercise 2.7: See How Labels Create Multiple Time Series

```bash
# One metric name, MANY time series due to labels:
curl -s "http://localhost:9090/api/v1/query?query=http_requests_total" | jq '.data.result | length'

# See each one with its labels:
curl -s "http://localhost:9090/api/v1/query?query=http_requests_total" | jq '.data.result[] | "\(.metric.method) \(.metric.endpoint) \(.metric.status) = \(.value[1])"'
```

---

### Exercise 2.8: Check Scrape Duration

How long does each scrape take? If it's too long, Prometheus struggles.

```bash
# How long each target takes to scrape
curl -s "http://localhost:9090/api/v1/query?query=scrape_duration_seconds" | jq '.data.result[] | "\(.metric.job): \(.value[1])s"'
```

---

## Key Takeaways

1. Prometheus **pulls** metrics — your apps serve them, Prometheus collects them
2. The `/metrics` endpoint is just plain text in a specific format
3. **Exporters** translate metrics from systems you can't modify
4. **Node Exporter** gives you OS-level metrics automatically
5. Scrape interval determines how often data is collected (15s is standard)
6. Each unique metric + label combination = one time series
7. More labels = more time series = more resource usage (cardinality!)

---

**✅ Topic 2 Complete! Next: Topic 3** → Writing PromQL queries and discovering why manual thresholds break.
