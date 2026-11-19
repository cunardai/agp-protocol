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
| `LedgerClient` (`client.ledger`) | Report acts (`report`), `verify`, checkpoints (`seal`, `checkpoints`, `verifyCheckpoint`, `checkpointKey`), `evidencePack` for an auditor |
| `PrincipalsClient` (`client.principals`) | The principal register (E1): `register`, `get`, `list`, `history`, `setStatus` — restrict, suspend, revoke, reinstate |
| `ContentClient` (`client.content`) | Kept prompts and answers: `store`, `get` (recorded), `retention`, `setRetention`; `contentRef()` gives the id and hash AGP will |
| `AdminClient` (`client.admin`) | OAuth clients, `provisionOrgClient` (an org's first client), object `versions` |

### v0.9 studio profile

These follow the reference server's v0.9 studio profile (agp-platform, branch `agp-v0.9-studio`): an
unalterable, per-org ledger with signed checkpoints; tenancy; immutable objects; auth that fails closed;
the principal register; reported events; kept content. A product hosting several organisations holds one
client per organisation, provisioned once:

```ts
const provisioner = new AGPClient(url, { client_id: "provisioner", client_secret: "…" });
const { client_id, client_secret } = await provisioner.admin.provisionOrgClient("bank-a", { client_id: "studio-bank-a", scopes: [...] });
const agp = new AGPClient(url, { client_id, client_secret });

await agp.ledger.report([{ event_kind: "tool.call", principal_id: "assistant:ann", acting_for: "user:ann",
                           action_class: "write", outcome: "initiated" }]);
await agp.principals.setStatus("user:ann", { status: "suspended", reason: "…", on_behalf_of: "user:admin1" });
const pack = await agp.ledger.evidencePack({ from: "2026-11-01T00:00:00Z" });   // a zip; verify.py inside
```

New errors: `AGPUnauthorizedError` (401), `AGPForbiddenError` (403) and `AGPPrincipalBlockedError` (a
principal, or whom it acts for, is stopped), `AGPImmutableError` (a record written twice),
`AGPLedgerUnavailableError` (the act wasn't carried out — retry), `AGPAuthNotConfiguredError`.

Verdicts come from the server in v0.9: register policy sets with `policy_engine` (`rules` takes your own
`rules` and `default_verdict`); a verdict passed to `evaluatePolicy` is kept for the record and doesn't
count.

Tests: `AGP_BASE_URL=… npm test` (an open server, started with `AGP_CALLER_VERDICTS=1` for the v0.5
session tests, which send their own verdicts) and, for the studio profile, a server with auth on and
a provisioning client: `AGP_AUTH_BASE_URL=… AGP_PROVISIONER_ID=… AGP_PROVISIONER_SECRET=… npm test`.

## Links

- [Protocol spec](https://agp.dev)
- [Python SDK](https://pypi.org/project/agp-sdk/)
- [GitHub](https://github.com/cunardai/agp)
- [Apache-2.0 License](https://github.com/cunardai/agp/blob/main/LICENSE)
