# agp-sdk

Python SDK for the [Agent Governance Protocol](https://agp.dev) — a governance protocol for autonomous agents operating in high-stakes, regulated, and multi-stakeholder environments.

Built and maintained by [CunardAI](https://cunardai.com).

## Install

```bash
pip install agp-sdk
```

Requires Python 3.11+.

## Quick start

The `TaskSession` API manages the full AGP lifecycle — task creation, liability binding, policy evaluation, human approval, and execution — without you having to track artifact IDs between steps.

```python
from agp import AGPClient

client = AGPClient(
    "https://your-agp-server",
    client_id="my-agent",       # OAuth 2.0 client credentials
    client_secret="s3cr3t",     # token fetch and refresh handled automatically
)

# Low-risk action — policy allows automatically
with client.task_session(
    principal_id="my-agent",
    requested_outcome="Summarise Q3 sales report",
    risk_tier="low",
) as session:
    session.bind(
        sponsoring_entity="acme-corp",
        accountable_owner="cto@acme.com",
        jurisdiction="EU",
    )
    session.decide(
        agent_id="my-agent",
        selected_action="summarise_document",
        rationale="Read-only NLP task, no PII",
        uncertainty_score=0.05,
    )
    session.evaluate(verdict="allow")
    receipt = session.execute(
        agent_id="my-agent",
        tool_id="nlp-summariser",
        operation={"document_id": "doc_q3_sales"},
        capability_token_ref="cap_xxx",
    )
    print(receipt.action_id)  # logged immutably to the audit ledger
```

## High-risk action with human approval

When the policy verdict is `require_approval`, the agent waits for a human controller to sign off before execution proceeds.

```python
with client.task_session(
    principal_id="finance-agent",
    requested_outcome="Approve $125k payment to Acme Corp",
    risk_tier="high",
    jurisdictions=["EU"],
    regulatory_frameworks=["EU_AI_ACT_2024"],
) as session:
    session.bind(
        sponsoring_entity="treasury",
        accountable_owner="cfo@acme.com",
        jurisdiction="EU",
    )
    session.issue_capability(
        subject_agent="finance-agent",
        issuer="treasury-controller",
        principal_id="finance-agent",
        permitted_actions=["approve_payment"],
        constraints={"max_amount_usd": 200000},
    )
    session.decide(
        agent_id="finance-agent",
        selected_action="approve_payment",
        rationale="Vendor on approved list, within delegated limit",
        uncertainty_score=0.12,
    )
    session.evaluate(verdict="require_approval", policy_set_ref="pset_finance_v2")

    # Human controller reviews and approves out-of-band.
    # Agent resumes here after approval is recorded.
    session.approve(approver_id="cfo@acme.com", notes="Confirmed with procurement")

    receipt = session.execute(
        agent_id="finance-agent",
        tool_id="payment-gateway",
        operation={"vendor": "Acme Corp", "amount_usd": 125000},
    )
```

## Low-level API

Use the sub-clients directly when you need fine-grained control.

```python
# Registry
task = client.registry.create_task(
    principal_id="my-agent",
    requested_outcome="...",
    risk_tier="medium",
)
capability = client.registry.issue_capability(
    subject_agent="my-agent",
    issuer="platform",
    principal_id="my-agent",
    permitted_actions=["data_read"],
)

# Decision
decision = client.decision.create_decision(
    task_id=task.task_id,
    agent_id="my-agent",
    selected_action="data_read",
    rationale="...",
    uncertainty_score=0.1,
)
policy = client.decision.evaluate_policy(
    task_id=task.task_id,
    decision_ref=decision.decision_id,
    verdict="allow",
)

# Execution — fail-closed gate
receipt = client.execution.submit_envelope(
    task_id=task.task_id,
    agent_id="my-agent",
    tool_id="my-tool",
    operation={"key": "value"},
    capability_token_ref=capability.capability_id,
    decision_ref=decision.decision_id,
    policy_decision_ref=policy.policy_evaluation_id,
)

# Audit replay
events = client.execution.replay_task(task.task_id)
```

## Resume a session after restart

```python
# Pick up an APPROVAL_PENDING task from a queue
session = client.resume_session("tsk_01HXYZ...")
session.approve(approver_id="reviewer@acme.com")
receipt = session.execute(...)
```

## Auth

AGP uses OAuth 2.0 client credentials (RFC 6749). Pass `client_id` and `client_secret` to the constructor — tokens are fetched and cached automatically, with refresh before expiry.

```python
client = AGPClient(
    "https://your-agp-server",
    client_id="my-agent",
    client_secret="s3cr3t",
)
```

If your server has auth disabled (no `AGP_AUTH_SECRET` set), omit the credentials:

```python
client = AGPClient("http://localhost:8099")  # open server, useful for dev
```

## Error handling

```python
from agp.exceptions import (
    AGPPolicyDeniedError,
    AGPApprovalRequiredError,
    AGPTokenRevokedError,
    AGPNotFoundError,
)

try:
    receipt = session.execute(...)
except AGPPolicyDeniedError as e:
    print(f"Blocked by policy: {e}")
except AGPApprovalRequiredError:
    print("Waiting for human approval")
except AGPTokenRevokedError:
    print("Capability token has been revoked")
```

## Links

- [Protocol spec](https://agp.dev)
- [TypeScript SDK](https://www.npmjs.com/package/@agp-protocol/sdk)
- [GitHub](https://github.com/cunardai/agp)
- [Apache-2.0 License](https://github.com/cunardai/agp/blob/main/LICENSE)
