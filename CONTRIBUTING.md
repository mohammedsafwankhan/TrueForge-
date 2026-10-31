# Contributing to Stranger Builds 2026 Autonomous Agent

Thank you for your interest in contributing to the **Stranger Builds 2026** Autonomous AI Agent project! This repository implements an autonomous multi-agent execution pipeline built on Fetch.ai's `uAgents`, the official Agent Chat Protocol (ACP), ASI-1 runtime reasoning, LangGraph orchestration, ASI Interactive Cards, and Fetch.ai Payment Protocol.

---

## 1. Development Principles

1. **Protocol Integrity**: Never break or replace the official Fetch.ai Agent Chat Protocol (`AgentChatProtocol:0.3.0`). All communication must remain compliant with official ACP message schemas.
2. **ASI-1 as Runtime Reasoning Engine**: ASI-1 is the primary reasoning and planning brain. Do not replace it with arbitrary alternative models.
3. **No Simulated Payments**: Never simulate successful payments. All paid operations must verify on-chain transaction hashes using `cosmpy.aerial.client.LedgerClient`.
4. **Interactive Cards**: All interactive cards must conform to the official ACP `MetadataContent` specification with all metadata values serialized as strings.
5. **Security First**: Never commit private keys, mnemonic seeds, or API tokens. Secrets must be loaded exclusively via environment variables.

---

## 2. Getting Started

### Prerequisites

* Python 3.12+ (or Python 3.14)
* Git
* SQLite 3 (or PostgreSQL 15+)
* Redis (optional, local cache fallback enabled)

### Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/stranger-builds/autonomous-agent.git
cd autonomous-agent

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and supply your ASI1_API_KEY and AGENT_SEED
```

---

## 3. Running the Test Suite

Before submitting a Pull Request, ensure that all unit and integration tests pass:

```bash
# Run the complete test suite
python -m pytest -v

# Run Phase 3 specific tests
python -m pytest tests/test_cards.py tests/test_payment.py tests/test_reliability.py -v
```

---

## 4. Pull Request Workflow

1. Fork the repository and create your feature branch (`git checkout -b feature/interactive-tool`).
2. Implement your changes following PEP 8 conventions, strict type annotations, and docstrings.
3. Write comprehensive unit tests for all new models and service methods.
4. Verify that existing tests continue to pass.
5. Commit your changes with descriptive messages:
   ```bash
   git commit -m "feat(cards): add custom portfolio rebalancing interactive card"
   ```
6. Push to your branch and open a Pull Request against `main`.

---

## 5. Security & Vulnerability Reporting

If you discover a security vulnerability or credential exposure risk, please do **NOT** open a public issue. Follow the instructions outlined in [SECURITY.md](SECURITY.md).
