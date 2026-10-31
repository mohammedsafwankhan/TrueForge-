# Security Policy & Credential Management

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.3.x   | :white_check_mark: |
| 0.2.x   | :white_check_mark: |
| < 0.2.0 | :x:                |

---

## Security Architecture & Best Practices

This autonomous agent is architected with strict defense-in-depth principles:

### 1. Zero Hardcoded Credentials
* **Strict Environment Isolation**: API keys (`ASI1_API_KEY`, `AGENT_SEED`, `AGENT_MAILBOX_KEY`) are exclusively read at runtime from `.env` or system environment variables via `pydantic-settings`.
* **Git Protection**: `.gitignore` and `.dockerignore` strictly blacklist `.env`, `private_keys.json`, `.pem`, `.key`, and database files.

### 2. Real-Time Log Sanitization & Sensitive Data Filtering
* A custom logging filter (`SensitiveDataFilter` in `core/logger.py`) inspects every log message before emission.
* Regular expressions automatically redact:
  * Fetch.ai private keys & seed phrases (`fetch1...`, BIP-39 mnemonic strings).
  * API tokens (`sk_...`, Bearer tokens).
  * On-chain signatures.
  * Authorization headers.

### 3. Payment Protocol & Double-Spending Protection
* **On-Chain Verification**: Payments are verified strictly against the Fetch.ai Dorado Testnet or Mainnet ledger via `cosmpy.aerial.client.LedgerClient`.
* **Double-Spending Prevention**: Every confirmed transaction hash (`tx_hash`) is written to the persistent `TransactionRef` database table with a unique index. Duplicate transaction submissions are immediately rejected with `PaymentStatus.DUPLICATE_REJECTED`.
* **Zero Payment Simulation**: Operations requiring payment will never proceed on simulated status. If the ledger is unreachable or the transaction is not found, the operation terminates with an explicit error.

### 4. Sandboxed Code Execution
* Mathematical and tool executions are sandboxed using an AST-based white-listed evaluator (`tools/execution_tools.py`), preventing arbitrary code execution, `eval()`, or `exec()`.

### 5. Resiliency & Denial-of-Service Protection
* **Circuit Breakers**: External HTTP services (ASI-1, CoinGecko, Open-Meteo, Ledger) are wrapped in configurable `CircuitBreaker` instances (`core/reliability.py`) that fail fast when downstream services become degraded.
* **Message Deduplication**: Inbound ACP messages are hashed and cached with a TTL to prevent replay attacks and duplicate execution loops.

---

## Reporting a Vulnerability

If you identify a security flaw or vulnerability:
1. Please email the maintainers or security team directly with the subject line `[SECURITY] Stranger Builds 2026 Vulnerability`.
2. Do not file public GitHub issues for security vulnerabilities.
3. Include detailed steps to reproduce the vulnerability, including any sample payloads or requests.
4. Maintainers will acknowledge receipt within 24 hours and issue a patch within 72 hours.
