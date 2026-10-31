# Stranger Builds 2026 – Production Deployment Guide

This guide details step-by-step production deployment procedures for bare metal, Docker, and Kubernetes environments.

---

## 1. Prerequisites Checklist

- [x] Python 3.12+ (or 3.14) runtime installed
- [x] Docker Engine 24.0+ & Docker Compose (optional for containerized deployment)
- [x] Valid ASI-1 API Key from [ASI:One Developer Portal](https://asi1.ai/)
- [x] Network connectivity to Fetch.ai Dorado Testnet RPC
- [x] Agentverse Account (for global catalog listing)

---

## 2. Environment Configuration

Copy the example environment file and configure production parameters:

```bash
cp .env.example .env
```

Ensure the following variables are defined:
```env
# Agent Identity
AGENT_NAME=stranger_builds_primary_agent
AGENT_PORT=8000
AGENT_ENDPOINT=http://127.0.0.1:8000/submit
AGENT_NETWORK=testnet
AGENT_SEED=stranger_builds_production_master_seed_phrase_2026

# ASI-1 API Runtime Engine
ASI1_API_KEY=sk_your_asi1_api_key_here
ASI1_API_BASE=https://api.asi1.ai/v1
ASI1_MODEL=asi1-mini

# Database (PostgreSQL recommended for production)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/stranger_builds
# Note: If PostgreSQL is unreachable, the system automatically falls back to SQLite!

# Agentverse Mailbox (for global discovery)
AGENT_MAILBOX_KEY=
```

---

## 3. Deployment Method A: Docker Containerization

### Step 1: Build the Multi-Stage Image
```bash
docker build -t stranger-builds-agent:0.3.0 .
```

### Step 2: Run the Production Container
```bash
docker run -d \
  --name stranger_builds_agent \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file .env \
  stranger-builds-agent:0.3.0
```

### Step 3: Verify Container Health
```bash
# Check container status
docker ps -f name=stranger_builds_agent

# Check health endpoint
curl -s http://localhost:8000/health | jq
```

---

## 4. Deployment Method B: Systemd Service (Linux Server)

Create `/etc/systemd/system/stranger-builds.service`:

```ini
[Unit]
Description=Stranger Builds Autonomous Agent Daemon
After=network.target

[Service]
Type=simple
User=agentuser
WorkingDirectory=/opt/stranger-builds
EnvironmentFile=/opt/stranger-builds/.env
ExecStart=/opt/stranger-builds/.venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable stranger-builds
sudo systemctl start stranger-builds
sudo systemctl status stranger-builds
```

---

## 5. Agentverse Almanac Registration & Discovery

To connect your deployed agent to the global Fetch.ai Almanac and enable discovery in ASI:One:

1. Visit [Agentverse](https://agentverse.ai/) and register an account.
2. Under **Agents**, click **Connect Local Agent**.
3. Generate a **Mailbox API Key**.
4. Add `AGENT_MAILBOX_KEY=<your_mailbox_key>` to your production `.env` file.
5. Restart your agent container or systemd service.
6. The agent will establish a WebSocket mailbox connection to Agentverse, register its Almanac contract record, and publish its protocol digest:
   `proto:30a801ed3a83f9a0ff0a9f1e6fe958cb91da1fc2218b153df7b6cbf87bd33d62`.
7. Your agent is now globally accessible to all ASI:One users!
