# Sangan — AI-Powered Kubernetes Cluster Monitor

> Named after the Yu-Gi-Oh card that searches 1 monster with 1500 or less ATK from their Deck to the hand.
> Sangan watches your Kubernetes cluster so you don't have to.

A security-first, locally-run AI monitoring agent that analyzes Kubernetes cluster health using a self-hosted LLM. No data leaves your machine.

---

## What It Does

Sangan runs a continuous monitoring loop:

1. **Collects** real-time metrics from Prometheus (CPU, memory, pod restarts, availability)
2. **Sanitizes** all data before it touches the LLM - prompt injection defense built in
3. **Analyzes** metrics using Phi-3 Mini running locally on GPU via Ollama
4. **Decides** HEALTHY or ALERT and logs the result with full audit trail
5. **Sleeps** 60 seconds and repeats

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
Structured log output / alert handler
```

---

## Security Model

Security was a first-class concern from day one, not an afterthought.

| Threat | Mitigation |
|--------|-----------|
| Prompt injection via metric labels | Input sanitizer — regex whitelist, max length enforcement |
| LLM output executed as code | Never happens — output is parsed for keywords only |
| Ollama exposed to network | Bound to `127.0.0.1` — host-only access |
| Malicious keys in metric data | Explicit key whitelist — unknown keys rejected by default |
| System prompt manipulation | Hardcoded prompt — never derived from external input |
| Container privilege escalation | Non-root user, read-only filesystem, all capabilities dropped (Kubernetes deployment) |

---

## Stack

- **Runtime:** Python 3.12
- **LLM:** Phi-3 Mini via [Ollama](https://ollama.com)
- **GPU:** NVIDIA RTX 4060 (CUDA 13.2) — via NVIDIA Container Toolkit
- **Metrics:** Prometheus + kube-prometheus-stack (Helm)
- **Orchestration:** Kubernetes (minikube), Docker
- **OS:** Arch Linux / RHEL compatible

---

## Requirements

- Docker with NVIDIA Container Toolkit
- NVIDIA GPU with CUDA support
- Kubernetes cluster with Prometheus deployed
- Python 3.12+
- Helm (for monitoring stack)

---

## Quick Start

**1. Clone the repo**
```bash
git clone https://github.com/barrawi/sangan-ai-watcher
cd sangan-ai-watcher
```

**2. Start Ollama with GPU support**
```bash
docker compose up -d
```

Ollama will automatically pull Phi-3 Mini on first boot if not already present.

**3. Deploy Kubernetes monitoring stack**
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace
```

**4. Forward Prometheus to localhost**
```bash
kubectl port-forward -n monitoring svc/prometheus-operated 9090:9090 &
```

**5. Install Python dependencies**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**6. Run Sangan**
```bash
python -m agent.monitor
```

---

## Sample Output

```
2026-03-29 12:47:20 sangan.monitor INFO Sangan is watching...
2026-03-29 12:47:20 sangan.monitor INFO Starting evaluation cycle...
2026-03-29 12:47:20 sangan.prometheus INFO Collected metrics: {'cpu_usage_percent': 0.14, 'memory_usage_percent': 0.0, 'pod_restart_count': 0.0, 'pods_not_ready': 0.0, 'pods_running': 3.0}
2026-03-29 12:47:20 sangan.sanitizer INFO Sanitized 5/5 metrics
2026-03-29 12:47:57 sangan.monitor INFO LLM response: Status: HEALTHY
2026-03-29 12:47:57 sangan.monitor INFO Cluster status: HEALTHY
2026-03-29 12:47:57 sangan.monitor INFO Sleeping 60s until next cycle
```

---

## Project Structure

```
sangan-ai-watcher/
├── agent/
│   └── monitor.py          # Main loop — collect, analyze, act
├── collector/
│   ├── prometheus.py       # Prometheus metric queries
│   └── sanitizer.py        # Input sanitization + prompt builder
├── tests/                  # Test suite (coming soon)
├── kubernetes/             # K8s manifests (coming soon)
├── docker-compose.yml      # Ollama + GPU setup
├── requirements.txt
└── README.md
```

---

## Roadmap

- [ ] Discord/webhook alert integration
- [ ] Kubernetes deployment manifests with RBAC and NetworkPolicy
- [ ] Testinfra post-deployment validation
- [ ] Multi-agent architecture — separate monitor and report agents
- [ ] CI/CD pipeline via GitHub Actions
- [ ] Grafana dashboard for agent activity metrics

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
- Wrote all the code (with bugs, typos and all — AI caught them, I fixed them)
- Made every technical decision and understood the reasoning behind each one
- Set up and operated the full infrastructure stack
- Debugged every failure and understood what caused it

I believe AI is a tool like any other — a senior engineer who can answer questions instantly. Using it doesn't replace understanding. Every line in this project I can explain, every security decision I can justify, and every bug I encountered I understand why it happened.

If you want to talk through any part of this project in depth, I'm happy to.

---

## Author

**Wilberth Barrantes Calderón**
[LinkedIn](https://www.linkedin.com/in/wilberth-barrantes-320902358/)

---

*Built from scratch on Arch Linux. No tutorials were followed in the making of this project, AI agents used for support.*
