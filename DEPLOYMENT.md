# Deployment Guide – Stranger Builds 2026 Autonomous Agent

This guide covers deployment options: Local Development, Docker Containerization, Production Kubernetes/Cloud, and Agentverse Registration.

---

## 1. System Requirements

* **Python**: 3.12+ (or 3.14)
* **Operating System**: Linux, macOS, or Windows
* **RAM**: 2 GB minimum (4 GB recommended)
* **Disk Space**: 500 MB
* **Network**: Outbound access to `https://api.asi1.ai/v1`, `https://api.coingecko.com`, `https://api.open-meteo.com`, and Fetch.ai Dorado Testnet RPC.

---

## 2. Environment Variables Reference

Create a `.env` file in the root directory:

```env
# Agent Identity & Network
AGENT_NAME=stranger_builds_primary_agent
AGENT_PORT=8000
AGENT_ENDPOINT=http://127.0.0.1:8000/submit
AGENT_NETWORK=testnet
AGENT_SEED=your_secure_agent_mnemonic_seed_phrase_here
AGENT_MAILBOX_KEY=

# ASI-1 Model Configuration
ASI1_API_KEY=sk_your_asi1_api_key_here
ASI1_API_BASE=https://api.asi1.ai/v1
ASI1_MODEL=asi1-mini

# Database & Cache (PostgreSQL / Redis with SQLite / In-Memory fallback)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/stranger_builds
REDIS_URL=redis://localhost:6379/0

# Security & Policies
LOG_LEVEL=INFO
REQUIRE_TOOL_APPROVAL=false
SESSION_EXPIRY_SECONDS=3600
MESSAGE_DEDUPLICATION_TTL_SECONDS=300
```

---

## 3. Local Deployment

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run test suite to verify installation
python -m pytest tests -v

# 3. Start the agent daemon
python main.py
```

Verify agent is running by visiting:
* Preview Inspector: `http://localhost:8000/`
* Health Check: `http://localhost:8000/health`

---

## 4. Docker Deployment

### 4.1 Build Docker Image
```bash
docker build -t stranger-builds-agent:latest .
```

### 4.2 Run Docker Container
```bash
docker run -d \
  --name stranger_builds_agent \
  -p 8000:8000 \
  --env-file .env \
  stranger-builds-agent:latest
```

### 4.3 Container Health Verification
```bash
docker ps
curl http://localhost:8000/health
```

---

## 5. Agentverse Registration & Hosting

To register your agent on the global Fetch.ai Almanac and Agentverse catalog:

1. Log into [Agentverse](https://agentverse.ai/).
2. Navigate to **My Agents** -> **Connect Local Agent**.
3. Retrieve your Agentverse API Key / Mailbox Key.
4. Set in `.env`:
   ```env
   AGENT_MAILBOX_KEY=your_mailbox_api_key
   ```
5. Restart your agent (`python main.py`).
6. Your agent will establish a persistent WebSocket connection to the Agentverse mailbox, automatically registering its address and chat protocol manifest (`proto:30a801ed3a83f9a0ff0a9f1e6fe958cb91da1fc2218b153df7b6cbf87bd33d62`) on the Fetch.ai Almanac contract.
7. Anyone in ASI:One or the Agentverse Explorer can now discover and message your agent directly!
