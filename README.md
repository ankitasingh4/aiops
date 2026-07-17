# AIOps Foundations: Intelligent Monitoring with Prometheus & Grafana

A hands-on tutorial covering 5 topics to build expertise in AI-powered operations monitoring.

## Prerequisites

- Docker & Docker Compose installed
- Python 3.9+ installed
- Basic familiarity with command line

## Course Structure

| # | Topic | Folder |
|---|-------|--------|
| 1 | The "AI" in AIOps: From Data to Decisions | `01-aiops-overview/` |
| 2 | Collecting the Data Fuel: Prometheus & Exporters | `02-prometheus-exporters/` |
| 3 | Basic Analysis with PromQL & The Limits of Manual Thresholds | `03-promql-analysis/` |
| 4 | AI-Powered Anomaly Detection | `04-anomaly-detection/` |
| 5 | AI-Driven Forecasting for Proactive Operations | `05-forecasting/` |

## Quick Start

```bash
# 1. Start the monitoring stack
docker-compose up -d

# 2. Install Python dependencies (for topics 4 & 5)
pip install -r requirements.txt

# 3. Follow each topic in order starting with 01-aiops-overview/
```

## Access Points (after docker-compose up)

| Service | URL |
|---------|-----|
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (admin/admin) |
| Node Exporter | http://localhost:9100/metrics |
| Custom App | http://localhost:8000/metrics |
| Alertmanager | http://localhost:9093 |

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Exporters  │────▶│  Prometheus  │────▶│   Grafana   │
│  (metrics)  │     │  (collect)   │     │ (visualize) │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐     ┌─────────────┐
                    │ Alertmanager │     │  Python ML  │
                    │  (alerts)    │     │  (AI/ML)    │
                    └──────────────┘     └─────────────┘
```
