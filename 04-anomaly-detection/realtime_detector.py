"""
Real-Time Anomaly Detection Pipeline
======================================
This script demonstrates a production-like anomaly detection pipeline:
1. Continuously fetches metrics from Prometheus
2. Maintains a sliding window of "normal" behavior
3. Detects anomalies in real-time
4. Logs alerts with explanations

Run this alongside your Prometheus stack to see live detection:
    python realtime_detector.py

Press Ctrl+C to stop.
"""

import sys
import time
from datetime import datetime, timedelta
from collections import deque

try:
    from prometheus_api_client import PrometheusConnect
    import numpy as np
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
except ImportError:
    print("Install: pip install prometheus-api-client numpy scikit-learn")
    sys.exit(1)

# Configuration
PROMETHEUS_URL = "http://localhost:9090"
CHECK_INTERVAL = 30  # seconds between checks
TRAINING_WINDOW = 200  # number of samples to train on
RETRAIN_EVERY = 50  # retrain model every N new samples
CONTAMINATION = 0.05

# Metrics to monitor
METRICS = {
    'cpu': 'app_cpu_usage_percent',
    'memory_mb': 'app_memory_usage_bytes / 1024 / 1024',
    'queue': 'app_queue_depth',
    'connections': 'active_connections',
}

prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)


class RealtimeAnomalyDetector:
    """
    A sliding-window anomaly detector that:
    - Collects metric snapshots over time
    - Periodically retrains an Isolation Forest
    - Scores new data points against the model
    - Explains why something is anomalous
    """

    def __init__(self, metrics, window_size=200, contamination=0.05):
        self.metrics = metrics
        self.window_size = window_size
        self.contamination = contamination
        self.history = deque(maxlen=window_size)
        self.model = None
        self.scaler = StandardScaler()
        self.samples_since_train = 0
        self.normal_stats = {}  # mean/std for each metric
        self.total_anomalies = 0
        self.total_checks = 0

    def fetch_current_values(self):
        """Get current values of all monitored metrics."""
        values = {}
        for name, query in self.metrics.items():
            try:
                result = prom.custom_query(query=query)
                if result:
                    values[name] = float(result[0]['value'][1])
            except Exception as e:
                pass
        return values if len(values) == len(self.metrics) else None

    def add_sample(self, values):
        """Add a new sample to the history."""
        self.history.append(values)
        self.samples_since_train += 1

    def train_model(self):
        """Train/retrain the Isolation Forest on current history."""
        if len(self.history) < 30:
            return False

        # Convert history to numpy array
        data = np.array([[s[m] for m in self.metrics.keys()]
                         for s in self.history])

        # Update scaler and model
        self.scaler.fit(data)
        X_scaled = self.scaler.transform(data)

        self.model = IsolationForest(
            n_estimators=100,
            contamination=self.contamination,
            random_state=42
        )
        self.model.fit(X_scaled)

        # Update normal statistics
        for i, name in enumerate(self.metrics.keys()):
            col = data[:, i]
            self.normal_stats[name] = {
                'mean': np.mean(col),
                'std': np.std(col)
            }

        self.samples_since_train = 0
        return True

    def detect(self, values):
        """Check if current values are anomalous."""
        if self.model is None:
            return None, None, None

        # Create feature vector
        x = np.array([[values[m] for m in self.metrics.keys()]])
        x_scaled = self.scaler.transform(x)

        # Get prediction and score
        prediction = self.model.predict(x_scaled)[0]
        score = self.model.decision_function(x_scaled)[0]

        is_anomaly = prediction == -1

        # Generate explanation
        explanation = []
        if is_anomaly:
            for name in self.metrics.keys():
                if name in self.normal_stats and self.normal_stats[name]['std'] > 0:
                    z = (values[name] - self.normal_stats[name]['mean']) / \
                        self.normal_stats[name]['std']
                    if abs(z) > 1.5:
                        direction = "HIGH" if z > 0 else "LOW"
                        explanation.append(f"{name}={values[name]:.1f} "
                                           f"({direction}, z={z:+.1f})")

        return is_anomaly, score, explanation

    def run(self):
        """Main detection loop."""
        print(f"\n{'═' * 70}")
        print(f"  Real-Time Anomaly Detection RUNNING")
        print(f"  Monitoring: {list(self.metrics.keys())}")
        print(f"  Check interval: {CHECK_INTERVAL}s")
        print(f"  Training window: {self.window_size} samples")
        print(f"{'═' * 70}")
        print(f"\n  Collecting initial training data...")
        print(f"  (Need at least 30 samples before detection starts)\n")

        try:
            while True:
                # Fetch current metric values
                values = self.fetch_current_values()

                if values is None:
                    print(f"  [{datetime.now().strftime('%H:%M:%S')}] "
                          f"⚠️  Could not fetch all metrics. Retrying...")
                    time.sleep(CHECK_INTERVAL)
                    continue

                # Add to history
                self.add_sample(values)
                self.total_checks += 1

                # Train/retrain if needed
                if self.model is None or self.samples_since_train >= RETRAIN_EVERY:
                    if self.train_model():
                        if self.model is not None and self.total_checks > 30:
                            print(f"  [{datetime.now().strftime('%H:%M:%S')}] "
                                  f"🔄 Model retrained on {len(self.history)} samples")

                # Detect anomalies
                is_anomaly, score, explanation = self.detect(values)

                if is_anomaly is None:
                    # Still collecting training data
                    progress = len(self.history)
                    print(f"  [{datetime.now().strftime('%H:%M:%S')}] "
                          f"📊 Collecting data... ({progress}/30 samples)")
                elif is_anomaly:
                    self.total_anomalies += 1
                    print(f"\n  [{datetime.now().strftime('%H:%M:%S')}] "
                          f"🚨 ANOMALY DETECTED (score: {score:.3f})")
                    print(f"    Values: " +
                          ", ".join(f"{k}={v:.1f}" for k, v in values.items()))
                    if explanation:
                        print(f"    Reason: {' | '.join(explanation)}")
                    print()
                else:
                    # Normal - print compact status
                    compact = " | ".join(f"{k}={v:.0f}" for k, v in values.items())
                    print(f"  [{datetime.now().strftime('%H:%M:%S')}] "
                          f"✅ Normal (score: {score:+.3f}) │ {compact}")

                time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print(f"\n\n{'═' * 70}")
            print(f"  Detection stopped.")
            print(f"  Total checks: {self.total_checks}")
            print(f"  Total anomalies: {self.total_anomalies}")
            if self.total_checks > 0:
                print(f"  Anomaly rate: "
                      f"{self.total_anomalies/self.total_checks*100:.1f}%")
            print(f"{'═' * 70}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("  Real-Time Anomaly Detection Pipeline")
    print("=" * 70)
    print("""
  This script continuously monitors your Prometheus metrics
  and detects anomalies using a self-training Isolation Forest.
  
  How it works:
  1. Collects 30+ samples to learn "normal" behavior
  2. Trains an Isolation Forest model
  3. Scores each new sample against the model
  4. Retrains every 50 samples to adapt to changes
  
  Press Ctrl+C to stop.
""")

    detector = RealtimeAnomalyDetector(
        metrics=METRICS,
        window_size=TRAINING_WINDOW,
        contamination=CONTAMINATION
    )
    detector.run()
