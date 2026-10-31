# API & Protocol Documentation – Stranger Builds 2026

This document details the communication protocols, REST diagnostics, interactive card schemas, and tool interfaces exposed by the agent.

---

## 1. Fetch.ai Agent Chat Protocol (ACP:0.3.0)

The agent communicates asynchronously over ACP using the official `chat_protocol_spec`.

### Protocol Identity
* **Name**: `AgentChatProtocol`
* **Version**: `0.3.0`
* **Digest**: `proto:30a801ed3a83f9a0ff0a9f1e6fe958cb91da1fc2218b153df7b6cbf87bd33d62`

### Message Types Handled
1. **`ChatMessage`**:
   * Encapsulates one or more content blocks (`StartSessionContent`, `EndSessionContent`, `TextContent`, `MetadataContent`).
   * Automatically answered with an immediate `ChatAcknowledgement` and an asynchronous reply `ChatMessage`.
2. **`ChatAcknowledgement`**:
   * Confirms delivery and receipt of a previously dispatched message.

### Interaction Flow
```
User / ASI:One                         Primary Agent
     |                                      |
     | ---- ChatMessage(TextContent) -----> |
     | <--- ChatAcknowledgement ----------- | (Immediate delivery ack)
     |                                      | [Multi-Agent Processing]
     | <--- ChatMessage(Text + Metadata) -- | (Execution result + Card)
     | ---- ChatAcknowledgement ----------> |
```

---

## 2. ASI Interactive Cards Schemas

Interactive cards are transmitted inside `ChatMessage` as `MetadataContent(type="metadata", metadata={...})`. All values in the `metadata` dictionary are strings.

### 2.1 Available Card Types
* **`input_form`**: Dynamic form fields (text, number, select) for submitting task parameters.
* **`selection`**: Visual cards presenting actionable choice buttons.
* **`detail`**: Telemetry and metrics display with source references and refresh buttons.
* **`review`**: Task execution fee review and payment authorization screen.
* **`confirmation`**: On-chain payment confirmation badge and transaction hash.
* **`result`**: Execution results with multi-agent consensus verification status.

### 2.2 Sample Metadata Schema
```json
{
  "content_type": "asi_card",
  "version": "1.0.0",
  "card_id": "4a12ec84-9a67-4e6f-9993-272cb6e60b8a",
  "card_type": "review",
  "title": "Review & Authorize Task Payment",
  "description": "Explicit authorization required before triggering paid autonomous execution:",
  "card_payload": "{\"fields\": [...], \"actions\": [...], \"data\": {...}}",
  "fields": "[{\"field_id\": \"fee\", \"label\": \"Execution Fee\", \"value\": \"0.0500 FET\"}]",
  "actions": "[{\"action_id\": \"authorize_payment\", \"label\": \"Authorize Payment\", \"action_type\": \"submit\"}]",
  "data": "{\"task_id\": \"task-123\", \"fee_fet\": 0.05}",
  "timestamp": "2026-10-31T08:30:00Z"
}
```

---

## 3. REST Diagnostics & Health Endpoints

When running locally or inside a container, the agent exposes REST HTTP diagnostic endpoints:

### `GET /`
Returns runtime agent identity, address, wallet, and Agentverse Inspector link:
```json
{
  "name": "stranger_builds_primary_agent",
  "address": "agent1qwcve9lh53jmq7wy583vh42jmdq93tm00nfhllm86agdl92xxt0mcskpemh",
  "wallet_address": "fetch1r5lk0kkhgrp4ep8n57635fwrz428fyc3lfyjqa",
  "status": "ONLINE",
  "version": "0.3.0",
  "network": "testnet",
  "protocol": "AgentChatProtocol:0.3.0",
  "manifest_digest": "proto:30a801ed3a83f9a0ff0a9f1e6fe958cb91da1fc2218b153df7b6cbf87bd33d62",
  "inspector_url": "https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A8000&address=agent1qwcve9lh53jmq7wy583vh42jmdq93tm00nfhllm86agdl92xxt0mcskpemh"
}
```

### `GET /health`
Returns aggregated subsystem health and circuit breaker states:
```json
{
  "status": "healthy",
  "uptime_seconds": 1284.5,
  "timestamp": "2026-10-31T08:35:00Z",
  "details": "Subsystems healthy: 5. Breakers: 0"
}
```

---

## 4. MCP Tools & Tool Registry

The execution engine exposes tools through a centralized registry (`tools/tool_registry.py`):

1. **`coingecko_price`**: Fetches real-time cryptocurrency spot prices ($USD) for tokens (e.g. `fetch-ai`, `ethereum`, `bitcoin`).
2. **`open_meteo_weather`**: Fetches live temperature, wind speed, and meteorological metrics for latitude/longitude coordinates.
3. **`calculate_expression`**: Evaluates mathematical formulas in a safe, sandboxed AST-parsed evaluator.
4. **`format_data_table`**: Renders structured multi-column data into clean Markdown tables.
5. **`fetchai_ledger_inspector`**: MCP-compliant tool querying account balances, block height, and network parameters on Fetch.ai Dorado testnet.
