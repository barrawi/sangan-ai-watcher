"""
monitor.py
Main agent loop: collect, sanitize, analyze, alert
Wilberth Barrantes
"""

import json
import logging
import time

import httpx

from collector.prometheus import get_cluster_metrics
from collector.sanitizer import build_prompt, sanitize_metrics

logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s %(message)s", level=logging.INFO
)

logger = logging.getLogger("sangan.monitor")

OLLAMA_URL = "http://localhost:11434"
MODEL = "phi3:mini"
CHECK_INTERVAL = 60  # seconds between evaluations

PERMITTED_ACTIONS = {
    "send_alert",
    "log_warning",
}


def query_llm(prompt: str) -> str:
    # send sanitized promt to local ollama

    try:
        response = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0},  # low = consistent output
            },
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()["response"].strip()

    except httpx.RequestError as e:
        logger.error(f"Failed to reach Ollama: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error querying LLM: {e}")
        return None


def handle_alert(message: str, metrics: dict):
    # handle LLM alerts, human readable message

    logger.warning(f"SANGAN ALERT: {message}")
    logger.warning(f"Metrics at time of alert: {json.dumps(metrics)}")
    # might send the message trhough discord or whatsapp in the future


def evaluate():
    # evaluation cycle

    logger.info("Starting evaluation cycle...")

    # collect from prometheus
    raw_metrics = get_cluster_metrics()

    # sanitize
    sanitized = sanitize_metrics(raw_metrics)

    if not sanitized:
        logger.error("No sanitized metrics avaible, skipping cycle...")
        return

    # build prompt
    prompt = build_prompt(sanitized)
    logger.debug(f"Prompt build: {prompt}")

    # query local LLM
    response = query_llm(prompt)

    # timeout?
    if not response:
        logger.error("No response from LLM, skipping cycle...")
        return

    logger.info(f"LLM response: {response}")

    # make sure LLM responds with STATUS, if it allucinates this will jump
    if not response.upper().startswith("STATUS:"):
        logger.warning(f"Unexpected LLM response format: {response}")
        return

    # parse response, check for ALERT
    if "ALERT" in response.upper():
        handle_alert(response, sanitized)
    else:
        logger.info("Cluster status: HEALTHY")


if __name__ == "__main__":
    logger.info("Sangan is watching...")
    while True:
        try:
            evaluate()
        except Exception as e:
            logger.error(f"Evaluation cycle failed: {e}")
        logger.info(f"Sleeping {CHECK_INTERVAL}s until next cycle")
        time.sleep(CHECK_INTERVAL)
