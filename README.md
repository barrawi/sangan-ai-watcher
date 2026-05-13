[![Sangan CI/CD](https://github.com/barrawi/sangan-ai-watcher/actions/workflows/main.yml/badge.svg)](https://github.com/barrawi/sangan-ai-watcher/actions)

# Sangan — AI-Powered Kubernetes Cluster Monitor

> Named after the Yu-Gi-Oh card that searches 1 monster with 1500 or less ATK from their Deck to the hand.
> Sangan watches your Kubernetes cluster so you don't have to.

A security-first, locally-run AI monitoring agent that analyzes Kubernetes cluster health using a self-hosted LLM. No data leaves your machine.

<img width="874" height="46" alt="image" src="https://github.com/user-attachments/assets/e11f99f9-cc4c-45df-a82f-4a88c99f4399" />
<img width="803" height="67" alt="image" src="https://github.com/user-attachments/assets/5241950e-86e0-453a-8724-a619483ebe18" />

---

## What It Does

Sangan runs a continuous monitoring loop:

1. **Collects** real-time metrics from Prometheus (CPU, memory, pod restarts, availability)
2. **Sanitizes** all data before it touches the LLM - prompt injection defense built in
3. **Analyzes** metrics using Phi-3 Mini running locally on GPU via Ollama
4. **Decides** HEALTHY or ALERT and logs the result with full audit trail
5. **Alerts** via Discord webhook when the cluster needs attention
6. **Sleeps** 60 seconds and repeats

Everything runs locally. No OpenAI API. No external calls. No data exfiltration.

---

## Architecture

```
Prometheus (Kubernetes metrics)
        ↓
collector/prometheus.py — fetches and parses metrics
        ↓
collector/sanitizer.py — strips malicious input, whitelist-only keys
        ↓
agent/monitor.py — builds hardcoded prompt, queries LLM, parses response
        ↓
Ollama + Phi-3 Mini (local GPU inference, RTX 4060)
        ↓
Structured log output + Discord webhook alert
```

---

## Security Model

Security was a first-class concern from day one, not an afterthought.

| Threat | Mitigation |
|--------|------------|
| Prompt injection via metric labels | Input sanitizer — regex whitelist, max length enforcement |
| LLM output executed as code | Never happens — output is parsed for keywords only |
| Ollama exposed to network | Bound to minikube bridge IP only — not exposed to wider network |
| Malicious keys in metric data | Explicit key whitelist — unknown keys rejected by default |
| System prompt manipulation | Hardcoded prompt — never derived from external input |
| Unexpected LLM response format | Format gate — malformed responses are flagged and skipped, never silently treated as healthy |
| Container privilege escalation | Non-root user (uid 1001), read-only filesystem, all capabilities dropped |
| Kubernetes API access | Empty RBAC Role — no API permissions granted, ServiceAccount token not mounted |
| Pod network exposure | NetworkPolicy — egress only to Prometheus ClusterIP and Ollama host, ingress blocked |

> **Note on LLM-generated reasons:** The ALERT/HEALTHY decision is based on metric thresholds. The reason text is LLM-generated and should be treated as a hint, not a diagnosis. Small models can misattribute causes - always check the raw metrics logged alongside the alert.

---

## Stack

- **Runtime:** Python 3.12
- **LLM:** Phi-3 Mini via [Ollama](https://ollama.com)
- **GPU:** NVIDIA RTX 4060 (CUDA) — via NVIDIA Container Toolkit
- **Metrics:** Prometheus + kube-prometheus-stack (Helm)
- **Alerts:** Discord webhook (pluggable — same code works for Slack or any webhook receiver)
- **Orchestration:** Kubernetes (minikube), Docker
- **Testing:** Pytest, Testinfra
- **OS:** Arch Linux / RHEL compatible

---

## Requirements

- Docker with NVIDIA Container Toolkit
- NVIDIA GPU with CUDA support
- Kubernetes cluster with Prometheus deployed
- Python 3.12+
- Helm (for monitoring stack)
- Discord server with a webhook configured (for alerts)
---

## Quick Start

**1. Clone the repo**
```bash
git clone https://github.com/barrawi/sangan-ai-watcher
cd sangan-ai-watcher
```
 
**2. Configure environment**
```bash
cp .env.example .env
# Edit .env and fill in your values
```
 
`.env.example`:
```
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
OLLAMA_URL=http://localhost:11435
PROMETHEUS_URL=http://localhost:9090
```
 
**3. Start Ollama with GPU support**
```bash
docker compose up -d ollama
watch docker compose ps
```
 
Ollama will automatically pull Phi-3 Mini on first boot if not already present. Wait for `(healthy)` before proceeding.
 
**4. Deploy Kubernetes monitoring stack**
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace
 
kubectl get pods -n monitoring -w
```
 
**5. Deploy Sangan to Kubernetes**
```bash
# Build the image first
docker build -t sangan:latest .

# Load image into minikube
minikube image load sangan:latest
 
# Create the secret with your values
# Edit kubernetes/secret.yaml with your base64-encoded values first
kubectl apply -f kubernetes/
```
 
Watch Sangan come up:
```bash
kubectl get pods -n default -w
kubectl logs -f deployment/sangan
```
 
**6. Run locally (optional, without Kubernetes)**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
 
# Port-forward Prometheus
kubectl port-forward -n monitoring svc/prometheus-operated 9090:9090 &
 
python -m agent.monitor
```

**7. Post-deploy validation (requires live cluster):**
```bash
pip install pytest-testinfra
pytest tests/test_deployment.py -v
```
Validates the running pod is non-root (uid 1001), filesystem is read-only, 
env vars are present, and all capabilities are dropped.

---

## Sample Output

Normal operation:
```
{"time": "2026-04-01T16:22:01Z", "logger": "sangan.monitor", "level": "INFO", "msg": "Sangan is watching..."}
{"time": "2026-04-01T16:22:01Z", "logger": "sangan.monitor", "level": "INFO", "msg": "Starting evaluation cycle..."}
{"time": "2026-04-01T16:22:01Z", "logger": "sangan.prometheus", "level": "INFO", "msg": "Collected metrics: {'cpu_usage_percent': 0.14, 'memory_usage_percent': 0.45, 'pod_restart_count': 0.0, 'pods_not_ready': 0.0, 'pods_running': 3.0}"}
{"time": "2026-04-01T16:22:01Z", "logger": "sangan.sanitizer", "level": "INFO", "msg": "Sanitized 5/5 metrics"}
{"time": "2026-04-01T16:22:02Z", "logger": "sangan.monitor", "level": "INFO", "msg": "LLM response: Status: HEALTHY\nReason: All metrics within normal thresholds."}
{"time": "2026-04-01T16:22:02Z", "logger": "sangan.monitor", "level": "INFO", "msg": "Cluster status: HEALTHY"}
{"time": "2026-04-01T16:22:02Z", "logger": "sangan.monitor", "level": "INFO", "msg": "Sleeping 60s until next cycle"}
```
 
Alert firing:
```
2026-04-01 17:37:15 sangan.prometheus INFO Collected metrics: {'cpu_usage_percent': 0.16, 'memory_usage_percent': 0.55, 'pod_restart_count': 0.0, 'pods_not_ready': 2.0, 'pods_running': 11.0}
2026-04-01 17:37:15 sangan.sanitizer INFO Sanitized 5/5 metrics
2026-04-01 17:37:15 sangan.monitor INFO LLM response: Status: ALERT
                                                        Reason: High CPU usage and unavailable pods.
2026-04-01 17:37:15 sangan.monitor WARNING SANGAN ALERT: Status: ALERT
2026-04-01 17:37:16 sangan.notifier INFO Alert sent successfully via webhook
```
 
---
 
## Discord Alerts
 
When Sangan detects an ALERT condition, it sends a formatted embed to your Discord channel:

<img width="359" height="237" alt="image" src="https://github.com/user-attachments/assets/8403d71f-1f11-49c1-9db5-3cd2a25c79d6" />

The webhook transport is pluggable - `notifications/notifier.py` can be pointed at Slack or any webhook receiver by swapping `_build_discord_payload()` for the target platform's format.

---

## Running Tests
 
```bash
python -m pytest tests/ -v
```
<img width="934" height="249" alt="image" src="https://github.com/user-attachments/assets/79299556-0164-4310-a508-e9a51dc9fd6d" />
 
The test suite covers the sanitizer security layer - the most critical component in the pipeline. Tests include prompt injection stripping, key whitelist enforcement, value sanitization, length truncation, and prompt structure integrity.
 
---

Sangan runs as a proper Kubernetes workload with a full security posture:
 
```
kubernetes/
├── serviceaccount.yaml   # Dedicated identity, API token not mounted
├── role.yaml             # Empty rules - no Kubernetes API access needed
├── rolebinding.yaml      # Binds ServiceAccount to Role
├── secret.yaml           # DISCORD_WEBHOOK_URL, OLLAMA_URL, PROMETHEUS_URL
├── deployment.yaml       # Non-root, read-only filesystem, dropped capabilities
└── networkpolicy.yaml    # Egress only: Prometheus ClusterIP + Ollama host
```
 
Sangan queries Prometheus directly via ClusterIP - no port-forward needed when running inside the cluster.
 
> `secret.yaml` is in `.gitignore` — never commit secrets to version control.

---

## Project Structure

```
sangan-ai-watcher/
├── agent/
│   └── monitor.py              # Main loop - collect, analyze, act
├── collector/
│   ├── prometheus.py           # Prometheus metric queries
│   └── sanitizer.py            # Input sanitization + prompt builder
├── notifications/
│   └── notifier.py             # Pluggable webhook alert transport
├── tests/
│   └── test_sanitizer.py       # Sanitizer security layer tests (11 tests)
│   └── test_deployment.py      # Post-deploy security validation (testinfra)
├── kubernetes/
│   ├── serviceaccount.yaml
│   ├── role.yaml
│   ├── rolebinding.yaml
│   ├── secret.yaml             # Not committed - see .gitignore
│   ├── deployment.yaml
│   └── networkpolicy.yaml
├── Dockerfile                  # Multi-stage build, non-root user, 45MB image
├── docker-compose.yml          # Ollama with GPU support
├── requirements.txt
├── .env.example
└── README.md
```

---

## Roadmap

- [x] Prometheus metric collection (CPU, memory, restarts, pod availability)
- [x] Input sanitization with prompt injection defense
- [x] Local LLM analysis via Ollama + Phi-3 Mini on GPU
- [x] Discord/webhook alert integration (pluggable transport)
- [x] Environment variable configuration
- [x] Docker healthcheck for Ollama
- [x] Pytest suite — sanitizer security layer (11 tests)
- [x] Dockerfile — multi-stage build, non-root user, 45MB final image
- [x] Kubernetes deployment manifests with RBAC and NetworkPolicy
- [x] GitHub Actions CI/CD pipeline
- [x] Testinfra post-deployment validation
- [x] Structured JSON logging
- [ ] Grafana dashboard for agent activity

---

## A Note on AI-Assisted Development

This project was built with AI assistance (Claude and Gemini mostly, *free versions only*) as a collaborative tool throughout the development process.

What AI helped with:
- Architectural and security threat modeling advising
- Debugging environment issues (Docker, minikube, NVIDIA Container Toolkit)
- Code review and identifying bugs before they became problems
- Documentation structure and README writing

What I did:

- Investigated the how to.
- Designed the project concept and goals
- Wrote all the code (with bugs, typos and all — AI caught them and assited foward)
- Made every technical decision and understood the reasoning behind each one
- Set up and operated the full infrastructure stack
- Debugged every failure and understood what caused it

I believe AI is a tool like any other - a senior engineer who can answer questions instantly. Using it doesn't replace understanding. Every line in this project I can explain, every security decision I can justify, and every bug I encountered I understand why it happened.

If you want to talk through any part of this project in depth, I'm happy to.

---

## Author

**Wilberth Barrantes Calderón** || 
[LinkedIn](https://www.linkedin.com/in/wilberth-barrantes-320902358/)

---

*Built from scratch on Arch Linux. No tutorials were followed in the making of this project, AI agents used for support.*
