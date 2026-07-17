# Topic 2: Collecting the Data Fuel — Prometheus & Exporters

## How Prometheus Works

Unlike traditional monitoring (where apps push metrics TO a server), Prometheus
uses a **pull model**: it reaches out and scrapes metrics from your services.

```
┌─────────────────────────────────────────────────────┐
│                    PROMETHEUS                         │
│                                                      │
│  ┌──────────┐   ┌───────────┐   ┌───────────────┐  │
│  │ Scraper  │──▶│   TSDB    │──▶│  Rule Engine  │  │
│  │ (pulls)  │   │ (stores)  │   │ (evaluates)   │  │
│  └────┬─────┘   └───────────┘   └───────┬───────┘  │
│       │                                   │          │
└───────┼───────────────────────────────────┼──────────┘
        │ HTTP GET /metrics                 │ fires alerts
        ▼                                   ▼
┌──────────────┐                    ┌──────────────┐
│   Targets    │                    │ Alertmanager │
│ (exporters)  │                    │              │
└──────────────┘                    └──────────────┘
```

### Key Concepts

- **Target**: Any endpoint that exposes metrics in Prometheus format
- **Exporter**: A service that translates metrics from another system into Prometheus format
- **Scrape**: The act of Prometheus pulling metrics from a target
- **TSDB**: Time Series Database — stores all metric data with timestamps

## The Prometheus Data Model

Every metric in Prometheus is a **time series** identified by:

```
metric_name{label1="value1", label2="value2"} <value> <timestamp>
```

Example:
```
http_requests_total{method="GET", endpoint="/api/users", status="200"} 1547 1710000000
```

### The 4 Metric Types

| Type | Behavior | Use Case | Example |
|------|----------|----------|---------|
| Counter | Only increases | Requests, errors, bytes | `http_requests_total` |
| Gauge | Goes up and down | Temperature, memory, connections | `active_connections` |
| Histogram | Counts in buckets | Latency distribution | `http_request_duration_seconds` |
| Summary | Quantiles client-side | Request sizes | `http_request_size_bytes` |

## Hands-On Exercises

### Exercise 2.1: Examine the Prometheus Configuration

Open `config/prometheus.yml` and understand each section:

```yaml
# How often Prometheus pulls metrics
global:
  scrape_interval: 15s

# What to monitor
scrape_configs:
  - job_name: 'node-exporter'     # Human-readable name
    static_configs:
      - targets: ['node-exporter:9100']  # Where to scrape
```

**Try this**: Change `scrape_interval` to `5s` and reload:
```bash
# Reload prometheus config without restart
curl -X POST http://localhost:9090/-/reload
```

### Exercise 2.2: Explore Node Exporter

Node Exporter exposes hundreds of OS-level metrics.

1. Visit http://localhost:9100/metrics
2. Search for these key metrics:
   - `node_cpu_seconds_total` — CPU time per mode (user, system, idle)
   - `node_memory_MemTotal_bytes` — Total memory
   - `node_filesystem_avail_bytes` — Available disk space
   - `node_network_receive_bytes_total` — Network bytes received

### Exercise 2.3: Build Your Own Custom Exporter

Create a new file to understand how instrumentation works:

```bash
cd 02-prometheus-exporters
python custom_exporter.py
```

Then visit http://localhost:8001/metrics to see your custom metrics!

### Exercise 2.4: Understanding Labels and Cardinality

Query Prometheus to see how labels create multiple time series:

```promql
# This single metric name has MANY time series due to labels:
http_requests_total

# Count how many unique series exist:
count(http_requests_total)

# Filter by specific labels:
http_requests_total{method="GET", status="200"}
```

**Warning**: High cardinality kills Prometheus! Never use unbounded values as labels
(user IDs, request IDs, timestamps). Each unique label combination = new time series.

### Exercise 2.5: Service Discovery Concepts

In production, you wouldn't hardcode targets. Prometheus supports:

- `kubernetes_sd` — Auto-discover pods in Kubernetes
- `consul_sd` — Find services registered in Consul
- `dns_sd` — Discover via DNS SRV records
- `file_sd` — Read targets from a JSON/YAML file (we'll use this)

Try file-based service discovery:
```bash
# Create a targets file
cat > config/targets.json << 'EOF'
[
  {
    "targets": ["sample-app:8000"],
    "labels": {"env": "tutorial", "team": "aiops"}
  }
]
EOF
```

## Understanding the Pull vs Push Debate

| Pull (Prometheus) | Push (DataDog, CloudWatch) |
|-------------------|---------------------------|
| ✅ Central control of what's monitored | ✅ Works behind firewalls |
| ✅ Easy to detect if target is down | ✅ Event-driven (no scrape delay) |
| ✅ Can scrape any HTTP endpoint | ❌ Need to manage agent on every host |
| ❌ Can't monitor short-lived jobs easily | ❌ Harder to know if agent is dead |

For short-lived jobs, Prometheus has the **Pushgateway** (we won't cover it here).

## Key Takeaways

1. Prometheus PULLS metrics via HTTP — your apps just serve them
2. Exporters translate external systems into Prometheus format
3. Labels are powerful but watch cardinality
4. Node Exporter gives you OS metrics "for free"
5. Custom metrics require just a few lines of code

---
**Next: Topic 3 →** We'll write PromQL queries and see where manual thresholds break down.
