"""
Sample Application with Prometheus Metrics
===========================================
This app simulates a real-world web service that:
- Handles HTTP requests with varying latency
- Occasionally produces errors
- Has periodic load spikes (simulating real traffic patterns)
- Exposes all metrics via /metrics endpoint

This is the "instrumented application" you'll monitor throughout the tutorial.
"""

import time
import random
import threading
import math
from flask import Flask, request, jsonify
from prometheus_client import (
    Counter, Histogram, Gauge, Summary,
    generate_latest, CONTENT_TYPE_LATEST
)

app = Flask(__name__)

# =============================================================================
# METRIC DEFINITIONS
# =============================================================================
# These are the 4 core Prometheus metric types you'll learn about:

# COUNTER: Only goes up. Good for: requests, errors, bytes sent
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# HISTOGRAM: Tracks distributions (buckets). Good for: latency, response sizes
http_request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# GAUGE: Goes up AND down. Good for: temperature, memory, active connections
active_connections = Gauge(
    'active_connections',
    'Number of active connections'
)

cpu_usage_percent = Gauge(
    'app_cpu_usage_percent',
    'Simulated CPU usage percentage'
)

memory_usage_bytes = Gauge(
    'app_memory_usage_bytes',
    'Simulated memory usage in bytes'
)

queue_depth = Gauge(
    'app_queue_depth',
    'Number of items waiting in processing queue'
)

# SUMMARY: Similar to histogram but calculates quantiles client-side
request_size_bytes = Summary(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method']
)


# =============================================================================
# TRAFFIC SIMULATION
# =============================================================================

def simulate_realistic_metrics():
    """
    Background thread that simulates realistic system behavior:
    - Sinusoidal CPU patterns (like day/night traffic)
    - Memory that slowly grows (like a leak)
    - Random spikes (like traffic bursts)
    - Queue depth that correlates with load
    """
    start_time = time.time()
    memory_base = 256 * 1024 * 1024  # 256MB base

    while True:
        elapsed = time.time() - start_time
        hour_of_day = (elapsed / 60) % 24  # Simulate 24h in 24 minutes

        # CPU: sinusoidal pattern with noise (simulates daily traffic pattern)
        base_cpu = 30 + 25 * math.sin(2 * math.pi * hour_of_day / 24)
        noise = random.gauss(0, 5)
        # Occasional spike (5% chance every cycle)
        spike = random.random() < 0.05
        cpu = base_cpu + noise + (30 if spike else 0)
        cpu = max(5, min(95, cpu))
        cpu_usage_percent.set(cpu)

        # Memory: slow growth with periodic GC (simulates memory leak + cleanup)
        memory_growth = (elapsed / 3600) * 50 * 1024 * 1024  # 50MB per hour
        gc_event = int(elapsed / 300) * 50 * 1024 * 1024  # GC every 5 minutes
        memory = memory_base + memory_growth - gc_event + random.randint(-10_000_000, 10_000_000)
        memory = max(memory_base, memory)
        memory_usage_bytes.set(memory)

        # Queue: correlates with CPU (high load = deeper queue)
        base_queue = int(cpu / 10)
        queue_noise = random.randint(-2, 5)
        queue_depth.set(max(0, base_queue + queue_noise))

        # Active connections: correlates with time of day
        connections = int(base_cpu * 2 + random.gauss(0, 10))
        active_connections.set(max(0, connections))

        time.sleep(5)


# =============================================================================
# HTTP ENDPOINTS
# =============================================================================

@app.route('/metrics')
def metrics():
    """Prometheus scrapes this endpoint to collect metrics."""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


@app.route('/api/users', methods=['GET'])
def get_users():
    """Simulated API endpoint with realistic latency patterns."""
    start = time.time()

    # Simulate variable processing time
    base_latency = 0.05
    # Sometimes slow (simulates DB query issues)
    if random.random() < 0.1:
        base_latency = 0.5 + random.random() * 1.5
    # Rarely very slow (simulates connection pool exhaustion)
    elif random.random() < 0.02:
        base_latency = 3.0 + random.random() * 2.0

    time.sleep(base_latency + random.gauss(0, 0.01))
    duration = time.time() - start

    # Simulate errors (5% error rate normally, higher under load)
    cpu = cpu_usage_percent._value.get()
    error_probability = 0.05 if cpu < 70 else 0.15
    if random.random() < error_probability:
        status = '500'
        http_requests_total.labels('GET', '/api/users', status).inc()
        http_request_duration.labels('GET', '/api/users').observe(duration)
        return jsonify({'error': 'Internal Server Error'}), 500

    status = '200'
    http_requests_total.labels('GET', '/api/users', status).inc()
    http_request_duration.labels('GET', '/api/users').observe(duration)
    request_size_bytes.labels('GET').observe(random.randint(100, 500))
    return jsonify({'users': ['alice', 'bob', 'charlie']}), 200


@app.route('/api/orders', methods=['POST'])
def create_order():
    """Simulated write endpoint - higher latency."""
    start = time.time()
    time.sleep(0.1 + random.gauss(0.05, 0.02))
    duration = time.time() - start

    if random.random() < 0.03:
        http_requests_total.labels('POST', '/api/orders', '500').inc()
        http_request_duration.labels('POST', '/api/orders').observe(duration)
        return jsonify({'error': 'Failed to create order'}), 500

    http_requests_total.labels('POST', '/api/orders', '201').inc()
    http_request_duration.labels('POST', '/api/orders').observe(duration)
    request_size_bytes.labels('POST').observe(random.randint(500, 2000))
    return jsonify({'order_id': random.randint(1000, 9999)}), 201


@app.route('/api/health')
def health():
    """Health check endpoint."""
    http_requests_total.labels('GET', '/api/health', '200').inc()
    return jsonify({'status': 'healthy'}), 200


@app.route('/webhook/alerts', methods=['POST'])
def alert_webhook():
    """Receives alerts from Alertmanager."""
    data = request.get_json(silent=True)
    if data:
        print(f"[ALERT] Received: {data.get('status', 'unknown')} - "
              f"{len(data.get('alerts', []))} alert(s)")
    return jsonify({'status': 'received'}), 200


# =============================================================================
# TRAFFIC GENERATOR
# =============================================================================

def generate_traffic():
    """Simulates incoming traffic to the application."""
    import urllib.request
    time.sleep(5)  # Wait for app to start

    while True:
        try:
            # Random endpoint selection (weighted towards reads)
            if random.random() < 0.7:
                urllib.request.urlopen('http://localhost:8000/api/users')
            elif random.random() < 0.5:
                req = urllib.request.Request(
                    'http://localhost:8000/api/orders',
                    data=b'{}',
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                urllib.request.urlopen(req)
            else:
                urllib.request.urlopen('http://localhost:8000/api/health')
        except Exception:
            pass

        # Variable request rate (busier during "peak hours")
        cpu = cpu_usage_percent._value.get()
        sleep_time = max(0.1, 2.0 - (cpu / 50))
        time.sleep(sleep_time + random.random() * 0.5)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    # Start background metric simulation
    metrics_thread = threading.Thread(target=simulate_realistic_metrics, daemon=True)
    metrics_thread.start()

    # Start traffic generator
    traffic_thread = threading.Thread(target=generate_traffic, daemon=True)
    traffic_thread.start()

    print("=" * 60)
    print("  Sample App Running - Metrics at http://localhost:8000/metrics")
    print("=" * 60)

    app.run(host='0.0.0.0', port=8000, threaded=True)
