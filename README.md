# Agent Governance Protocol (AGP)

**v0.5.1** · [agp-protocol.dev](https://agp-protocol.dev) · [Spec](spec/implementation-profile.md) · [Proposed extensions](spec/studio-extensions.md) · Apache-2.0

[![CI](https://github.com/cunardai/agp/actions/workflows/ci.yml/badge.svg)](https://github.com/cunardai/agp/actions/workflows/ci.yml)

---

AI agents can now approve payments, send emails, modify databases, and make legal commitments at machine speed. **Who authorised that? Under what constraints? Can you prove it?**

AGP is an open governance protocol that sits between an agent's intent and its actions. Before any consequential action executes, the agent must declare intent, prove delegated authority, pass a policy evaluation, and — for high-risk actions — obtain human approval. Execution is **fail-closed**: any missing or revoked artifact blocks the action. Every step is logged to an immutable, hash-chained audit ledger.

---

## The Mandate Paradox

Current AI agents are Yes-Bots — optimised to execute, with no structural way to say no. In high-stakes environments, an agent that always says YES is a high-speed liability.

AGP introduces **The Purple Line**: a deterministic, protocol-layer enforcement boundary that an agent cannot cross without verifiable authority, policy clearance, and a complete evidence chain — regardless of who gives the instruction.

---

## How it works

An AI agent about to approve a $125,000 vendor payment:

| Step | What happens |
|---|---|
| **1. Register task** | Agent declares intent: who, what, risk tier (`high`). Creates the governance root. |
| **2. Prove authority** | Agent presents a capability token — delegated, scoped, expiring, revocable. |
| **3. Policy evaluation** | Policy engine checks vendor, amount, jurisdiction. Returns `require_approval`. |
| **4. Human approval** | Approval request routed to CFO. Agent waits. Nothing executes yet. |
| **5. Submit action envelope** | All artifacts bundled and submitted. Server validates each one. Returns 201 + signed receipt. |
| **✕ Anything missing?** | Rejected. No bypass path exists. |

---

## Install

```bash
pip install agp-sdk                 # Python
npm install @agp-protocol/sdk       # TypeScript / Node.js
```

```python
from agp import AGPClient

client = AGPClient(
    "https://your-agp-server",
    client_id="my-agent",
    client_secret="s3cr3t",
)

task = client.registry.create_task({
    "principal_id": "my-agent",
    "requested_outcome": "Approve $125k payment to Acme Corp",
    "risk_tier": "high",
})
capability = client.registry.create_capability({ "task_id": task["task_id"], ... })
policy     = client.decision.evaluate_policy({ "task_id": task["task_id"], ... })
approval   = client.decision.create_approval({ "task_id": task["task_id"], ... })
receipt    = client.execution.submit({ "task_id": task["task_id"], ... })
# → 201 Created. Signed receipt + immutable ledger entry.
```

```typescript
import { AGPClient } from "@agp-protocol/sdk";

const client = new AGPClient("https://your-agp-server", {
  clientId: "my-agent",
  clientSecret: "s3cr3t",
});

const task     = await client.registry.createTask({ ... });
const decision = await client.decision.evaluate(task.task_id);
const receipt  = await client.execution.submit({ task_id: task.task_id, ... });
```

---

## Three trust domains

```
┌─────────────────────────────────────────────────────────────────┐
│  REGISTRY            │  DECISION              │  EXECUTION       │
│                      │                        │                  │
│  Tasks               │  Attested contexts     │  Action envelopes│
│  Capability tokens   │  Evidence bundles      │  Receipts        │
│  Liability bindings  │  Impact assessments    │  Event ledger    │
│  Delegations         │  Policy evaluations    │                  │
│  Skill registry      │  Approvals             │  Fail-closed gate│
│  Revocations         │  Escalations           │  Hash-chained log│
└─────────────────────────────────────────────────────────────────┘
```

Each domain has its own OpenAPI 3.1 spec and OAuth 2.0 scope set. Execution is the gate — no action passes without valid artifacts from both Registry and Decision.

---

## Repository layout

```
agp-protocol/
├── spec/
│   ├── implementation-profile.md    # Full protocol specification
│   └── studio-extensions.md         # Proposed: principal register (E1), detectors (E2), Production Profile
├── api/
│   ├── registry.yaml                # OpenAPI 3.1 — Registry domain
│   ├── decision.yaml                # OpenAPI 3.1 — Decision domain
│   └── execution.yaml               # OpenAPI 3.1 — Execution domain
├── schemas/                         # JSON Schema 2020-12 source (26 schemas)
│   ├── objects/                     # Core protocol objects
│   ├── common/                      # Shared definitions
│   └── async/                       # Async operation schemas
├── sdk/
│   ├── python/                      # Python SDK (agp-sdk on PyPI)
│   └── typescript/                  # TypeScript SDK (@agp-protocol/sdk on npm)
├── mcp/                             # MCP protocol binding
├── policies/
│   └── eu-ai-act/                   # OPA / Rego policy suite
└── conformance/                     # pytest conformance suite (200+ tests)
```

---

## Protocol interoperability

AGP is the **governance layer** across the agentic protocol stack. Other protocols handle transport and commerce; AGP handles accountability:

| Protocol | Handles | AGP adds |
|---|---|---|
| MCP | Tool call transport | Authority, policy, audit envelope per tool call |
| A2A | Agent-to-agent coordination | Sub-token delegation, cascade revocation |
| AP2 | Payment mandates | Capability token per mandate, immutable evidence chain |
| UCP | Commerce sessions | Spend authority enforcement before merchant contact |

---

## Key properties

| Property | Description |
|---|---|
| **Fail-closed** | Missing or revoked artifact halts execution. No bypass path. |
| **Delegatable capabilities** | Tokens carry spend limits, scope constraints, expiry. Revoking a parent cascades to all children. |
| **Immutable audit trail** | Hash-chained event ledger. Append-only. Full replay supported. |
| **Governance role separation** | `executive`, `compliance_monitor`, `impact_assessor` roles strictly separated. |
| **Taint tracking** | External content is untrusted by default. Taint propagates through derivations. |
| **EU AI Act alignment** | Risk classification (Art. 9), transparency (Art. 13), human oversight (Art. 14), record-keeping (Art. 12). |

---

## Conformance

Run the full suite against any AGP-compliant server:

```bash
cd conformance
pip install -r requirements.txt
pytest tests/ --base-url=http://your-server
```

Auth tests require `AGP_AUTH_SECRET`, `AGP_CLIENT_ID=conformance-client`, `AGP_CLIENT_SECRET=conformance-secret` on the server.

---

## Status

| Component | Status |
|---|---|
| Protocol specification | ✅ v0.5-draft |
| OpenAPI specs (3 domains) | ✅ v0.5.1 |
| JSON Schema 2020-12 (26 schemas) | ✅ v0.5.1 |
| Python SDK (`agp-sdk`) | ✅ v0.5.1 on PyPI |
| TypeScript SDK (`@agp-protocol/sdk`) | ✅ v0.5.1 on npm |
| MCP protocol binding | ✅ v0.5.0 |
| EU AI Act OPA policies | ✅ v0.5.1 |
| Conformance suite | ✅ 200+ tests |

---

## Authentication

AGP uses OAuth 2.0 client credentials (RFC 6749). Both SDKs handle token fetch and refresh automatically when `client_id` and `client_secret` are provided.

Nine fine-grained scopes: `agp.registry.read/write`, `agp.decision.read/write`, `agp.execution.read/write`, `agp.approval.write`, `agp.policy.write`, `agp.revocation.write`.

---

## Contributing

The schema `$id` URIs and API paths are stable within a minor version. Breaking changes increment the major version.

Issues and PRs welcome. See [agp-protocol.dev](https://agp-protocol.dev) for the full protocol documentation.
