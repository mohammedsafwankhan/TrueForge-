# Stranger Builds 2026 – Final Architecture Specification

## 1. Executive Summary

This project delivers a production-ready, autonomous multi-agent execution system developed for the **Stranger Builds 2026** hackathon. Built from the ground up on Fetch.ai's `uAgents` framework, it integrates:
1. **Agent Chat Protocol (ACP:0.3.0)**: Standard Fetch.ai conversational messaging with published protocol manifest.
2. **ASI-1 Model Integration**: Live runtime reasoning, dynamic decomposition, and consensus evaluation via `https://api.asi1.ai/v1`.
3. **Multi-Agent Specialization**: 4 distinct role-based subagents (Planner, Research, Execution, Verification) coordinated via LangGraph.
4. **ASI Interactive Cards**: ACP-compliant interactive UI cards (Input Forms, Selection, Detail, Review, Confirmation, Result).
5. **Fetch.ai Payment Protocol**: Pay-per-task microtransaction architecture with on-chain CosmPy ledger verification and database anti-replay protection.
6. **Production Resiliency**: Circuit breakers, exponential backoff with jitter, AST-sandboxed computation, and multi-stage containerization.

---

## 2. Component Directory Structure

```
stranger-builds/
├── agents/                     # Specialized Agents & Primary Orchestrator
│   ├── primary_agent.py        # ACP Listener, REST Preview & Lifecycle Manager
│   ├── planner_agent.py        # Task decomposition & DAG planning (ASI-1)
│   ├── research_agent.py       # Live API fetching & data synthesis
│   ├── execution_agent.py      # MCP & AST-sandboxed tool runner
│   └── verification_agent.py   # Result validation & anomaly detection
├── cards/                      # ASI Interactive Cards (ACP-compliant)
│   ├── models.py               # ASICard, CardType, CardAction, CardField
│   └── card_factory.py         # Factory producing all 6 interactive card types
├── core/                       # Foundational Infrastructure
│   ├── config.py               # Pydantic Settings & environment validation
│   ├── exceptions.py           # Typed domain exceptions
│   ├── logger.py               # Real-time sensitive credential redaction filter
│   └── reliability.py          # CircuitBreakers, backoff retry, HealthTracker
├── db/                         # Persistence & Anti-Replay
│   ├── connection.py           # Async SQLAlchemy (Postgres + SQLite fallback)
│   ├── models.py               # SessionRecord, ExecutionLog, TransactionRef
│   └── cache.py                # Redis cache with local in-memory fallback
├── models/                     # Data Contracts
│   ├── requests.py             # Inbound parsed request representations
│   └── responses.py            # ExecutionResult, AgentPreviewInfo, AgentHealthInfo
├── orchestration/              # LangGraph Workflow Engine
│   ├── asi_client.py           # Authenticated client for api.asi1.ai (asi1-mini)
│   ├── engine.py               # Execution engine orchestrating specialized agents
│   ├── state.py                # Typed LangGraph workflow state definition
│   └── workflow.py             # StateGraph definition with conditional routing
├── payment/                    # Fetch.ai Payment Protocol
│   ├── models.py               # PaymentInvoice, PaymentStatus, VerificationResult
│   └── service.py              # Pay-per-task pricing, CosmPy ledger validation
├── protocols/                  # Fetch.ai Protocols
│   └── chat_protocol.py        # ACP:0.3.0 protocol definition & message handlers
├── tools/                      # Tool Suite & Integrations
│   ├── api_tools.py            # Live CoinGecko price oracle & Open-Meteo telemetry
│   ├── execution_tools.py      # AST-sandboxed math evaluator & Markdown tables
│   ├── mcp_tools.py            # Model Context Protocol adapter for Fetch ledger
│   └── tool_registry.py        # Central tool registration & authorization guard
├── tests/                      # 71 Automated Unit & Integration Tests
├── Dockerfile                  # Multi-stage production container
├── .dockerignore               # Security & image size optimization
├── main.py                     # Entry point launching agent runtime
└── README.md                   # Repository overview
```

---

## 3. Communication & Execution Lifecycle

```
================================================================================
                               EXECUTION PIPELINE
================================================================================

1. Inbound ACP Message
   User/ASI:One dispatches ChatMessage -> Primary Agent verifies HMAC/Signature ->
   Immediate ChatAcknowledgement dispatched -> Message hashed to prevent replay.

2. Intent Understanding & Dynamic Planning
   Message routed to PlannerAgent -> ASI-1 analyzes intent -> Decomposes request into
   executable subtasks with dependencies and required tools.

3. Payment Review (if premium task)
   PaymentService checks task fee -> If non-zero, dispatches ReviewCard ->
   Awaits user authorization & on-chain tx_hash -> Verifies on-chain via CosmPy ->
   Checks TransactionRef table to prevent double-spending.

4. Multi-Agent Execution (LangGraph StateGraph)
   - ResearchAgent: Fetches live telemetry (CoinGecko / Open-Meteo).
   - ExecutionAgent: Executes approved tools inside AST math sandbox.
   - VerificationAgent: Audits result against reasonableness bounds.
   - Conditional Edge: If verification fails, loops back with backoff retry.

5. Delivery & Interactive Cards
   Final response assembled -> Attached with appropriate ASI Interactive Card
   (ResultCard, DetailCard, or SelectionCard) -> Transmitted as ChatMessage.
```
