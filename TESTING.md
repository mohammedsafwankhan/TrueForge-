# Testing Guide – Stranger Builds 2026

This document describes the testing strategy, test suites, and guidelines for verifying the autonomous agent system.

---

## 1. Test Architecture

The test suite contains **71 automated unit and integration tests** covering all phases of the project:

| Test Module | Test Focus | Status |
| ----------- | ---------- | ------ |
| `tests/test_agent.py` | Agent lifecycle, identity, session service, memory | 9 / 9 PASSED |
| `tests/test_agents_phase2.py` | Planner, Research, Execution, Verification agents | 4 / 4 PASSED |
| `tests/test_asi_client.py` | Live ASI-1 API connectivity, completions, planning, json | 6 / 6 PASSED |
| `tests/test_cards.py` | All 6 ASI interactive card types, schemas, roundtrip serialization | 8 / 8 PASSED |
| `tests/test_chat_protocol.py` | ACP specification, handlers, manifest generation, deduplication | 7 / 7 PASSED |
| `tests/test_e2e_phase2.py` | End-to-end multi-agent execution pipeline | 1 / 1 PASSED |
| `tests/test_langgraph_workflow.py` | LangGraph StateGraph, conditional routing, retries | 2 / 2 PASSED |
| `tests/test_live_integration.py` | Agent-to-agent live loopback Chat Protocol exchange | 1 / 1 PASSED |
| `tests/test_messages.py` | Message models, content parsing, timezone normalization | 12 / 12 PASSED |
| `tests/test_payment.py` | Pricing, invoices, review cards, anti-replay, on-chain verification | 7 / 7 PASSED |
| `tests/test_reliability.py` | Circuit breaker tripping/recovery, backoff retry, health tracker | 4 / 4 PASSED |
| `tests/test_tools.py` | CoinGecko live API, Open-Meteo, math sandbox, MCP adapter | 10 / 10 PASSED |
| **TOTAL** | **Comprehensive Full System Coverage** | **71 / 71 PASSED** |

---

## 2. Running Tests

### 2.1 Run All Tests
```bash
python -m pytest tests -v
```

### 2.2 Run Specific Module
```bash
# Test interactive cards
python -m pytest tests/test_cards.py -v

# Test payment protocol & double spending prevention
python -m pytest tests/test_payment.py -v

# Test live ASI-1 connectivity
python -m pytest tests/test_asi_client.py -v
```

### 2.3 Run with Code Coverage
```bash
python -m pytest tests --cov=. --cov-report=term-missing
```

---

## 3. Mocking vs. Live External Testing

1. **Live External Tests**:
   * `test_asi_client.py`: Directly verifies live connection to `https://api.asi1.ai/v1` using authenticated API credentials.
   * `test_tools.py`: Directly verifies live HTTP connectivity against CoinGecko and Open-Meteo.
2. **Deterministic Mocks**:
   * `test_payment.py`: Simulates ledger transaction receipts to test transaction confirmation logic without burning real testnet tokens during CI runs.
   * Duplicate payment tests use real SQLite database queries to ensure database unique indexes prevent double-spending.
