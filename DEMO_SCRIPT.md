# Stranger Builds 2026 – Hackathon Demo Script

This document provides a guided walkthrough for hackathon judges to verify the end-to-end functionality of the autonomous agent system.

---

## 1. Quick Verification (30 Seconds)

Open your web browser and visit:
* **Agent Overview**: [http://localhost:8000/](http://localhost:8000/)
  * Displays agent name, cryptographic address (`agent1qwc...`), wallet address (`fetch1r5l...`), published protocol manifest digest, and Agentverse Inspector link.
* **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
  * Displays uptime, subsystem health, and circuit breaker states.

---

## 2. Interactive ASI:One Demonstration Scenarios

### Scenario A: General Inquiry & Interactive Capability Discovery
1. **User Action**: Send message `"help"` or `"What can you do?"` via ACP.
2. **Agent Behavior**:
   * Acknowledges receipt immediately (`ChatAcknowledgement`).
   * Returns a helpful summary accompanied by an **Interactive Selection Card**.
   * Selection card presents 4 actionable options: Crypto Pricing Oracle, Weather Telemetry, Fetch Ledger MCP Inspector, Safe Computational Engine.

### Scenario B: Dynamic Task Parameter Configuration
1. **User Action**: Click or request `"Configure task"`.
2. **Agent Behavior**:
   * Dispatches an **Interactive Input Form Card**.
   * User selects asset (`fetch-ai`), enters quantity (`1000`), and submits the form.

### Scenario C: Paid Task Execution & Review Card Authorization
1. **User Action**: Request `"Perform a live portfolio valuation for 1000 FET"`.
2. **Agent Behavior**:
   * **Payment Identification**: `PaymentService` identifies this as a premium task requiring `0.05 FET`.
   * **Review Card**: Emits an interactive **Review Screen Card** displaying:
     * Task ID: e.g. `task-abc123`
     * Fee: `0.0500 FET`
     * Merchant Address: `fetch1r5lk0kkhgrp4ep8n57635fwrz428fyc3lfyjqa`
     * Buttons: `Authorize Payment (0.0500 FET)` | `Decline`
3. **User Action**: Submits on-chain transaction and provides transaction hash.
4. **Agent Behavior**:
   * **On-Chain Verification**: Queries Fetch.ai Dorado Testnet via `LedgerClient` to confirm the transaction.
   * **Double-Spending Check**: Validates `tx_hash` against `TransactionRef` database table.
   * **Confirmation Card**: Emits an interactive **Confirmation Card** with the confirmed block height.

### Scenario D: Autonomous Multi-Agent Execution & Verification
1. **Agent Behavior**:
   * **Planner Agent**: Uses ASI-1 (`asi1-mini`) to construct the execution DAG.
   * **Research Agent**: Queries CoinGecko API for real-time Fetch.ai ($FET) spot price ($USD).
   * **Execution Agent**: Computes total valuation (`1000 * spot_price`) in the AST-sandboxed math evaluator.
   * **Verification Agent**: Audits numerical bounds and reasonableness.
   * **Result Card**: Returns a formatted report accompanied by an **Interactive Result Card** stamped with `PASSED (Quality Verified)`.

---

## 3. Running the Automated Test Suite

To run all 71 automated tests verifying the entire system:
```bash
python -m pytest tests -v
```
All tests execute in ~45 seconds with 100% pass rate.
