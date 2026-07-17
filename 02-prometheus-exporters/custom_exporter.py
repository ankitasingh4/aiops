"""
Custom Prometheus Exporter
==========================
This exercise teaches you how to instrument YOUR OWN application with metrics.

Run this file:
    python custom_exporter.py

Then visit: http://localhost:8001/metrics
"""

import time
import random
import threading
from prometheus_client import (
    Counter, Gauge, Histogram, Summary,
    start_http_server, Info
)

# =============================================================================
# STEP 1: Define your metrics
# =============================================================================

# Info metric - static metadata about the service
app_info = Info('custom_app', 'Information about the custom app')
app_info.info({
    'version': '1.2.3',
    'environment': 'tutorial',
    'language': 'python'
})

# Counter - tracks total number of processed jobs
jobs_processed = Counter(
    'jobs_processed_total',
    'Total number of jobs processed',
    ['job_type', 'status']  # Labels!
)

# Gauge - current queue size
job_queue_size = Gauge(
    'job_queue_size',
    'Current number of jobs in the queue',
    ['priority']
)

# Histogram - job processing duration
job_duration = Histogram(
    'job_processing_duration_seconds',
    'Time spent processing a job',
    ['job_type'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

# Summary - payload sizes
payload_size = Summary(
    'job_payload_size_bytes',
    'Size of job payloads',
    ['job_type']
)


# =============================================================================
# STEP 2: Simulate application behavior
# =============================================================================

def process_jobs():
    """Simulates a job processing system."""
    job_types = ['email', 'report', 'notification', 'data_sync']

    while True:
        # Pick a random job type
        job_type = random.choice(job_types)

        # Simulate queue changes
        for priority in ['high', 'medium', 'low']:
            queue_change = random.randint(-2, 3)
            current = job_queue_size.labels(priority)._value.get()
            new_val = max(0, current + queue_change)
            job_queue_size.labels(priority).set(new_val)

        # Simulate processing a job
        # Different job types have different latency profiles
        if job_type == 'email':
            duration = random.gauss(0.5, 0.1)
        elif job_type == 'report':
            duration = random.gauss(5.0, 2.0)  # Reports are slow
        elif job_type == 'notification':
            duration = random.gauss(0.2, 0.05)  # Notifications are fast
        else:  # data_sync
            duration = random.gauss(10.0, 3.0)  # Sync is slowest

        duration = max(0.01, duration)

        # Record the duration
        job_duration.labels(job_type).observe(duration)

        # Record payload size
        size = random.randint(100, 10000) if job_type != 'report' else random.randint(10000, 1000000)
        payload_size.labels(job_type).observe(size)

        # Simulate success/failure
        if random.random() < 0.05:  # 5% failure rate
            jobs_processed.labels(job_type, 'failed').inc()
        else:
            jobs_processed.labels(job_type, 'success').inc()

        # Wait before processing next job
        time.sleep(random.uniform(0.5, 2.0))


# =============================================================================
# STEP 3: Start the exporter
# =============================================================================

if __name__ == '__main__':
    # Start the metrics server on port 8001
    start_http_server(8001)
    print("=" * 60)
    print("  Custom Exporter Running!")
    print("  Metrics available at: http://localhost:8001/metrics")
    print("=" * 60)
    print("\nMetrics being exposed:")
    print("  - jobs_processed_total (Counter)")
    print("  - job_queue_size (Gauge)")
    print("  - job_processing_duration_seconds (Histogram)")
    print("  - job_payload_size_bytes (Summary)")
    print("  - custom_app_info (Info)")
    print("\nPress Ctrl+C to stop.\n")

    # Start job processing simulation
    worker = threading.Thread(target=process_jobs, daemon=True)
    worker.start()

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
