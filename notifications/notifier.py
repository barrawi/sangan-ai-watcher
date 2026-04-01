"""
notifier.py
Webhook for alert transport
Wilberth Barrantes
"""

import json
import logging
import os

import requests

logger = logging.getLogger("sangan.notifier")


def send_webhook_alert(message: str, metrics: dict) -> bool:
    # sends alert to webhook, returns true or false, discord, slack, wte
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    if not webhook_url:
        logger.warning("No webhook URL configured, skipping alert")
        return False

    payload = _build_discord_payload(message, metrics)

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Alert sent successfully via webhook")
        return True

    except requests.RequestException as e:
        logger.error(f"Failed to send webhook alert: {e}")
        return False


def _build_discord_payload(message: str, metrics: dict) -> dict:
    # message that appears on Discord
    metric_lines = "\n".join(f"• {k}: {v}" for k, v in metrics.items())

    return {
        "embeds": [
            {
                "title": "🚨 Sangan Alert",
                "description": message,
                "color": 15158332,  # red color
                "fields": [
                    {
                        "name": "Metrics at time of alert",
                        "value": f"```\n{metric_lines}\n```",
                    }
                ],
                "footer": {"text": "Sangan AI Watcher"},
            }
        ]
    }
