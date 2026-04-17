# @agp-protocol/sdk

TypeScript/Node.js SDK for the [Agent Governance Protocol](https://agp.dev) — a governance protocol for autonomous agents operating in high-stakes, regulated, and multi-stakeholder environments.

Built and maintained by [CunardAI](https://cunardai.com).

## Install

```bash
npm install @agp-protocol/sdk
```

## Quick start

```typescript
import { AGPClient } from "@agp-protocol/sdk";

const client = new AGPClient({ baseUrl: "https://your-agp-server" });

// Register a task
const task = await client.registry.registerTask({ ... });

// Request a policy decision
const decision = await client.decision.evaluate(task.task_id);

// Submit an action envelope
const result = await client.execution.submit({ task_id: task.task_id, ... });
```

## Clients

| Client | Description |
|---|---|
| `AGPClient` | Top-level client — composes all three domains |
| `RegistryClient` | Task registration and capability scoping |
| `DecisionClient` | Policy evaluation and approval workflows |
| `ExecutionClient` | Action envelope submission and audit ledger |

## Links

- [Protocol spec](https://agp.dev)
- [Python SDK](https://pypi.org/project/agp-sdk/)
- [GitHub](https://github.com/cunardai/agp)
- [Apache-2.0 License](https://github.com/cunardai/agp/blob/main/LICENSE)
