"""
prometheus.py
Queries prometheus for Kubernetes cluster metrics
Wilberth Barrantes
"""

import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("sangan.prometheus")

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")


def get_cluster_metrics() -> dict:
    """
    Fetch key metrics from Prometheus.
    Returns a flat dict of metric_name -> value.
    Why flat dict: easier to sanitize and pass to LLM
    than nested Prometheus response format.
    """
    metrics = {}

    queries = {
        "cpu_usage_percent": 'sum(rate(container_cpu_usage_seconds_total{namespace="default"}[5m])) * 100',
        "memory_usage_percent": 'sum(container_memory_working_set_bytes{namespace="default"}) / scalar(machine_memory_bytes) * 100',
        "pod_restart_count": 'sum(increase(kube_pod_container_status_restarts_total{namespace="default"}[15m]))',
        "pods_not_ready": 'count(kube_pod_status_ready{namespace="default", condition="true"} == 0) or vector(0)',
        "pods_running": 'count(kube_pod_status_phase{namespace="default", phase="Running"})',
    }

    for metric_name, query in queries.items():
        try:
            response = requests.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": query},
                timeout=5,
            )
            response.raise_for_status()
            data = response.json()

            # Prometheus returns results as a list
            # We take the first result value
            results = data.get("data", {}).get("result", [])
            if results:
                # value is [timestamp, value_string]
                value = float(results[0]["value"][1])
                metrics[metric_name] = round(value, 2)
            else:
                metrics[metric_name] = 0.0
                logger.warning(f"No data returned for metric: {metric_name}")

        except requests.RequestException as e:
            logger.error(f"Failed to fetch metric {metric_name}: {e}")
            metrics[metric_name] = None

    logger.info(f"Collected metrics: {metrics}")
    return metrics
