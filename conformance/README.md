# AGP Conformance Test Suite

Black-box test suite for verifying AGP server implementations against the protocol specification.
Run it against any AGP-conformant server — the reference implementation or your own.

## Quick start

```bash
cd conformance/

# Install dependencies
pip install -r requirements.txt

# Run against the local reference server (default)
pytest

# Run against a remote server
pytest --base-url https://your-agp-server.example.com

# Run a specific section only
pytest tests/test_05_execution_gate.py

# Show a concise pass/fail summary
pytest --tb=no -q
```

## Test structure

| File | Protocol Section | What it tests |
|------|-----------------|---------------|
| `test_01_tasks.py` | §4 | Task creation, field validation, listing, filtering |
| `test_02_state_machine.py` | §9.1 | All valid + invalid state transitions, terminal states |
| `test_03_registry.py` | §5-§9 | Liability bindings, capability tokens, delegations, skills, policy sets, revocations |
| `test_04_decision.py` | §10-§13 | Decisions, policy evaluations, approvals, escalations, policy_set_ref validation |
| `test_05_execution_gate.py` | §10 | All 9 fail-closed gate prerequisite checks + execution lifecycle |
| `test_06_ledger.py` | §14 | Hash-chained ledger append, hash mismatch rejection, replay |
| `test_07_idempotency.py` | §15 | Idempotency-Key semantics across all resource types |
| `test_08_error_format.py` | §16 | AGP error envelope format on all error codes |

## Conformance levels

| Result | Meaning |
|--------|---------|
| All pass | **Fully conformant** — safe to use in production |
| Execution gate failures | **Non-conformant** — unsafe; fix before production |
| Idempotency failures | **Partially conformant** — retry loops may cause duplicates |
| Error format failures | **Partially conformant** — error handling will be inconsistent |

## Running the reference server

```bash
cd server/
uvicorn main:app --port 8099
# Then in another terminal:
cd ../conformance/
pytest
```

With PostgreSQL:
```bash
cd server/
docker compose --profile postgres up -d
DATABASE_URL=postgresql://agp:agp@localhost:5432/agp uvicorn main:app --port 8099
```
