"""
Capacity Planning Pipeline
============================
A complete, production-ready capacity planning tool that:
1. Fetches historical metrics from Prometheus
2. Applies multiple forecasting methods
3. Identifies when capacity limits will be breached
4. Generates a capacity planning report

This is the kind of tool an SRE team would actually use.

Usage:
    python capacity_planner.py
"""

import sys
from datetime import datetime, timedelta

try:
    from prometheus_api_client import PrometheusConnect
    import pandas as pd
    import numpy as np
    from sklearn.linear_model import LinearRegression
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    import matplotlib.pyplot as plt
    import warnings
    warnings.filterwarnings('ignore')
except ImportError:
    print("Install: pip install prometheus-api-client pandas numpy scikit-learn statsmodels matplotlib")
    sys.exit(1)

prom = PrometheusConnect(url="http://localhost:9090", disable_ssl=True)


class CapacityPlanner:
    """
    Production-grade capacity planning for infrastructure metrics.

    For each resource, this tool:
    1. Analyzes historical growth trends
    2. Applies multiple forecasting methods
    3. Calculates time-to-exhaustion
    4. Generates actionable recommendations
    """

    def __init__(self, prometheus_url="http://localhost:9090"):
        self.prom = PrometheusConnect(url=prometheus_url, disable_ssl=True)
        self.results = []

    def fetch_metric(self, query, hours=2, step='60s'):
        """Fetch historical data."""
        end = datetime.now()
        start = end - timedelta(hours=hours)
        result = self.prom.custom_query_range(
            query=query, start_time=start, end_time=end, step=step
        )
        if not result or not result[0]['values']:
            return None
        values = [float(v[1]) for v in result[0]['values']]
        timestamps = [datetime.fromtimestamp(float(v[0])) for v in result[0]['values']]
        return pd.DataFrame({'timestamp': timestamps, 'value': values})

    def analyze_resource(self, name, query, capacity_limit, unit='%',
                         warning_threshold=0.8, critical_threshold=0.9):
        """
        Analyze a single resource's capacity.

        Args:
            name: Human-readable resource name
            query: PromQL query
            capacity_limit: Maximum capacity value
            unit: Unit of measurement
            warning_threshold: Fraction of capacity for warning (0.8 = 80%)
            critical_threshold: Fraction of capacity for critical (0.9 = 90%)
        """
        print(f"\n  Analyzing: {name}...")
        df = self.fetch_metric(query, hours=2)

        if df is None or len(df) < 10:
            return {
                'name': name,
                'status': 'NO_DATA',
                'message': 'Insufficient data'
            }

        current_value = df['value'].iloc[-1]
        current_pct = (current_value / capacity_limit) * 100

        # Method 1: Linear trend
        df['seconds'] = (df['timestamp'] - df['timestamp'].min()).dt.total_seconds()
        X = df['seconds'].values.reshape(-1, 1)
        y = df['value'].values

        lin_model = LinearRegression()
        lin_model.fit(X, y)
        growth_rate = lin_model.coef_[0]  # units per second

        # Time to warning and critical
        warning_value = capacity_limit * warning_threshold
        critical_value = capacity_limit * critical_threshold

        time_to_warning = None
        time_to_critical = None

        if growth_rate > 0:
            if current_value < warning_value:
                time_to_warning = (warning_value - current_value) / growth_rate / 3600  # hours
            if current_value < critical_value:
                time_to_critical = (critical_value - current_value) / growth_rate / 3600  # hours

        # Method 2: Exponential smoothing forecast
        forecast_values = None
        try:
            ts = df.set_index('timestamp')['value']
            ts = ts.asfreq('60s', method='ffill')
            if len(ts) >= 20:
                hw_model = ExponentialSmoothing(
                    ts, trend='add', seasonal=None,
                    initialization_method='estimated'
                )
                fitted = hw_model.fit(optimized=True)
                forecast_values = fitted.forecast(60)  # 1 hour ahead
        except Exception:
            pass

        # Determine status
        if current_pct >= critical_threshold * 100:
            status = 'CRITICAL'
        elif current_pct >= warning_threshold * 100:
            status = 'WARNING'
        elif time_to_critical and time_to_critical < 24:
            status = 'WATCH'
        else:
            status = 'OK'

        result = {
            'name': name,
            'unit': unit,
            'current_value': current_value,
            'capacity_limit': capacity_limit,
            'current_pct': current_pct,
            'growth_rate_per_hour': growth_rate * 3600,
            'time_to_warning_hours': time_to_warning,
            'time_to_critical_hours': time_to_critical,
            'status': status,
            'forecast': forecast_values,
            'history': df
        }

        self.results.append(result)
        return result

    def generate_report(self):
        """Generate a capacity planning report."""
        print("\n")
        print("╔" + "═" * 68 + "╗")
        print("║" + "  CAPACITY PLANNING REPORT".center(68) + "║")
        print("║" + f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(68) + "║")
        print("╠" + "═" * 68 + "╣")

        for r in self.results:
            if r['status'] == 'NO_DATA':
                print(f"║  {r['name']:20s} │ NO DATA AVAILABLE".ljust(68) + " ║")
                continue

            # Status emoji
            status_icon = {
                'OK': '✅', 'WATCH': '👀', 'WARNING': '⚠️ ', 'CRITICAL': '🚨'
            }
            icon = status_icon.get(r['status'], '❓')

            print(f"║  {icon} {r['name']:<18s} │ "
                  f"{r['current_value']:.1f}/{r['capacity_limit']:.0f} {r['unit']} "
                  f"({r['current_pct']:.1f}%)".ljust(67) + "║")

            # Growth info
            rate = r['growth_rate_per_hour']
            if abs(rate) > 0.01:
                direction = "↑" if rate > 0 else "↓"
                print(f"║     Growth: {direction} {abs(rate):.2f} {r['unit']}/hour".ljust(68) + " ║")

            # Time to limits
            if r['time_to_critical_hours'] is not None:
                if r['time_to_critical_hours'] < 24:
                    print(f"║     ⏰ Critical in: {r['time_to_critical_hours']:.1f} hours".ljust(68) + " ║")
                elif r['time_to_critical_hours'] < 168:
                    days = r['time_to_critical_hours'] / 24
                    print(f"║     ⏰ Critical in: {days:.1f} days".ljust(68) + " ║")

            print("║" + " " * 68 + "║")

        print("╠" + "═" * 68 + "╣")

        # Recommendations
        print("║  RECOMMENDATIONS:".ljust(68) + " ║")
        critical = [r for r in self.results if r['status'] == 'CRITICAL']
        warnings = [r for r in self.results if r['status'] == 'WARNING']
        watches = [r for r in self.results if r['status'] == 'WATCH']

        if critical:
            for r in critical:
                print(f"║  🚨 {r['name']}: IMMEDIATE action required!".ljust(68) + " ║")
        if warnings:
            for r in warnings:
                print(f"║  ⚠️  {r['name']}: Plan expansion within 24h".ljust(68) + " ║")
        if watches:
            for r in watches:
                hours = r.get('time_to_critical_hours', '?')
                print(f"║  👀 {r['name']}: Monitor closely (~{hours:.0f}h to critical)".ljust(68) + " ║")
        if not critical and not warnings and not watches:
            print("║  ✅ All resources healthy. No action needed.".ljust(68) + " ║")

        print("╚" + "═" * 68 + "╝")

    def plot_results(self):
        """Generate visualization of all analyzed resources."""
        n_resources = len([r for r in self.results if r['status'] != 'NO_DATA'])
        if n_resources == 0:
            return

        fig, axes = plt.subplots(n_resources, 1, figsize=(14, 4 * n_resources))
        if n_resources == 1:
            axes = [axes]

        plot_idx = 0
        for r in self.results:
            if r['status'] == 'NO_DATA':
                continue

            ax = axes[plot_idx]
            df = r['history']

            # Plot historical data
            ax.plot(df['timestamp'], df['value'], 'b-', linewidth=1, label='Actual')

            # Plot capacity limits
            ax.axhline(y=r['capacity_limit'], color='red', linestyle='-',
                       linewidth=2, alpha=0.7, label=f"Capacity ({r['capacity_limit']}{r['unit']})")
            ax.axhline(y=r['capacity_limit'] * 0.8, color='orange', linestyle='--',
                       alpha=0.7, label='Warning (80%)')

            # Plot forecast if available
            if r['forecast'] is not None:
                forecast_times = [df['timestamp'].max() + timedelta(minutes=i+1)
                                  for i in range(len(r['forecast']))]
                ax.plot(forecast_times, r['forecast'].values, 'r--',
                        linewidth=2, label='Forecast')

            # Status color
            status_colors = {'OK': 'green', 'WATCH': 'yellow',
                             'WARNING': 'orange', 'CRITICAL': 'red'}
            ax.set_facecolor(
                (*plt.cm.colors.to_rgb(status_colors.get(r['status'], 'white')), 0.05)
            )

            ax.set_title(f"{r['name']} [{r['status']}] - "
                         f"{r['current_pct']:.1f}% used")
            ax.set_ylabel(f"{r['unit']}")
            ax.legend(loc='upper left')
            plot_idx += 1

        plt.xlabel('Time')
        plt.tight_layout()
        plt.savefig('capacity_report.png', dpi=100)
        print(f"\n  📊 Capacity chart saved to: capacity_report.png")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("  CAPACITY PLANNING PIPELINE")
    print("  Analyzing infrastructure resources...")
    print("=" * 70)

    planner = CapacityPlanner()

    # Define resources to monitor
    resources = [
        {
            'name': 'CPU Usage',
            'query': 'app_cpu_usage_percent',
            'capacity_limit': 100,
            'unit': '%'
        },
        {
            'name': 'Memory',
            'query': 'app_memory_usage_bytes / 1024 / 1024',
            'capacity_limit': 512,  # 512MB
            'unit': 'MB'
        },
        {
            'name': 'Queue Depth',
            'query': 'app_queue_depth',
            'capacity_limit': 50,  # Max queue before degradation
            'unit': 'items'
        },
        {
            'name': 'Connections',
            'query': 'active_connections',
            'capacity_limit': 200,  # Max connections
            'unit': 'conns'
        },
    ]

    # Analyze each resource
    for resource in resources:
        planner.analyze_resource(**resource)

    # Generate report
    planner.generate_report()

    # Generate charts
    planner.plot_results()

    print("\n" + "=" * 70)
    print("  WHAT TO DO WITH THIS IN PRODUCTION")
    print("=" * 70)
    print("""
  1. Run this as a CRON job (e.g., every 6 hours)
  2. Send the report to Slack/PagerDuty
  3. Auto-scale resources when WATCH status detected
  4. Create Grafana annotations for predicted breaches
  5. Track forecast accuracy over time (MAPE metric)
  
  This is the CORE of proactive operations:
  Instead of waiting for alerts → predict and prevent.
""")
