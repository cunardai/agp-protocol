# AGP Implementation Profile v0.5-draft
## Operational Semantics, Security, Idempotency, and Runtime Rules

**Status:** Draft  
**Applies to:** AGP Registry API, Decision API, Execution API

---

# 1. Purpose

This profile defines the **required runtime behavior** for interoperable AGP implementations.

The base AGP spec defines:
- object shapes
- endpoint surfaces
- protocol layering

This profile defines:
- who may call what
- sync vs async behavior
- idempotency semantics
- object state constraints
- revocation effects
- retry behavior
- error handling
- ordering guarantees
- webhook security
- minimum conformance rules

Without this profile, two teams can both claim “AGP support” while behaving incompatibly.

---

# 2. Conformance model

An implementation is conformant only if it satisfies:

1. **Core object validation**  
   All submitted objects validate against the published schemas.

2. **Operational semantics**  
   All lifecycle, idempotency, revocation, and execution rules in this document are enforced.

3. **Security controls**  
   Authn/authz, signature checks, and callback verification are implemented per this profile.

4. **Deterministic enforcement points**  
   Consequential execution is blocked when required upstream artifacts are missing, invalid, expired, revoked, or out of scope.

---

# 3. Trust domains

AGP implementations SHOULD separate these trust domains:

- **Registry domain**  
  durable authority and governance artifacts

- **Decision domain**  
  evidence, analysis, evaluation, approvals

- **Execution domain**  
  side-effect control and forensic recording

A single deployment MAY combine them physically, but MUST preserve their logical permission boundaries.

---

# 4. Authentication and authorization profile

## 4.1 Authentication requirements

Implementations MUST support at least one of:

- OAuth2 client credentials
- mutual TLS

Implementations SHOULD support both.

Human approval interfaces MAY use OpenID Connect user authentication in addition to the machine profile above.

---

## 4.2 Issuer classes

Every write operation MUST be attributable to an issuer class.

Minimum issuer classes:

- `registry_issuer`
- `capability_issuer`
- `skill_publisher`
- `policy_engine`
- `approver`
- `execution_gateway`
- `ledger_writer`
- `revocation_issuer`

---

## 4.3 Minimum authorization matrix

## Registry API

### `/tasks`
- `POST`: `registry_issuer`
- `GET`: `registry_issuer`, `policy_engine`, `execution_gateway`, authorized readers

### `/liability-bindings`
- `POST`: `registry_issuer`
- `GET`: authorized readers

### `/capabilities`
- `POST`: `capability_issuer`
- `GET`: authorized readers, execution gateway, policy engine

### `/skills`
- `POST`: `skill_publisher` or `registry_issuer`
- `GET`: authorized readers

### `/revocations`
- `POST`: `revocation_issuer`
- `GET`: authorized readers

## Decision API

### `/contexts`
- `POST`: authorized agent, tool gateway, or ingestion service
- `GET`: authorized readers

### `/evidence-bundles`
- `POST`: authorized agent, evidence service
- `GET`: authorized readers

### `/commerce-sessions`
- `POST`: authorized agent, commerce orchestrator
- `GET`: authorized readers

### `/decisions`
- `POST`: authorized agent runtime
- `GET`: authorized readers

### `/policy-evaluations`
- `POST`: authorized agent runtime, orchestrator, decision service
- `GET operations`: authorized readers

### `/policy-decisions`
- `POST`: `policy_engine`
- `GET`: authorized readers

### `/approval-requests`
- `POST`: authorized agent runtime, orchestrator, policy engine
- `GET operations`: authorized readers

### `/approvals`
- `POST`: `approver`
- `GET`: authorized readers

## Execution API

### `/action-envelopes`
- `POST`: authorized execution caller or orchestrator
- `GET`: authorized readers

### `/execution-receipts`
- `POST`: `execution_gateway`, tool gateway
- `GET`: authorized readers

### `/ledger-events`
- `POST`: `ledger_writer`, `execution_gateway`
- `GET`: authorized readers

### `/replay`
- `GET`: authorized readers only

---

# 5. Object signature profile

## 5.1 Signed object classes

The following objects MUST be signed by their issuer:

- `LiabilityBinding`
- `CapabilityToken`
- `SkillManifest`
- `RevocationNotice`
- `DecisionRecord`
- `PolicyDecision`
- `ApprovalArtifact`
- `ActionEnvelope`
- `ExecutionReceipt`
- `EventLedgerRecord`

The following SHOULD be signed:
- `AttestedContext`
- `EvidenceBundle`
- `CommerceSession`

---

## 5.2 Signature minimums

Each signed object MUST bind at least:
- object type
- stable object identifier
- full canonical payload hash
- issuer identity
- issuance timestamp

Implementations SHOULD use a canonical JSON serialization before hashing/signing.

If detached signatures are used, the signature reference MUST be immutable and resolvable.

---

## 5.3 Signature verification

Before any consequential action, the execution domain MUST verify signatures on:
- `CapabilityToken`
- `PolicyDecision`
- `ApprovalArtifact` if present
- `ActionEnvelope`

If any required signature is missing or invalid, execution MUST fail closed.

---

# 6. Idempotency semantics

## 6.1 General rule

Any POST that creates a durable artifact or side effect SHOULD support `Idempotency-Key`.  
The following endpoints MUST support it:

- `POST /tasks`
- `POST /liability-bindings`
- `POST /capabilities`
- `POST /skills`
- `POST /revocations`
- `POST /contexts`
- `POST /evidence-bundles`
- `POST /commerce-sessions`
- `POST /decisions`
- `POST /policy-evaluations`
- `POST /approval-requests`
- `POST /approvals`
- `POST /action-envelopes`
- `POST /execution-receipts`
- `POST /ledger-events`

---

## 6.2 Idempotency behavior

For a given endpoint + idempotency key + authenticated caller:

- If the same request payload is retried, the server MUST return the original successful response or the current operation status.
- If the same key is reused with a different payload, the server MUST return conflict.

Recommended error:
- `409 AGP_IDEMPOTENCY_CONFLICT`

---

## 6.3 Retention window

Servers SHOULD retain idempotency records for at least:
- 24 hours for Decision API
- 24 hours for Execution API
- 7 days for Registry API

Implementations MAY retain longer.

---

# 7. Sync vs async rules

## 7.1 Registry API

Registry writes SHOULD be synchronous by default.

Async registry operations MAY be used for:
- external trust verification of skill manifests
- bulk revocations
- external issuer validation

If async is used, the endpoint MUST return `202` and an `AsyncOperation`.

---

## 7.2 Decision API

### Policy evaluation
A policy evaluation MUST be asynchronous when:
- human review is required
- external compliance systems are queried
- multiple policy engines must be combined
- SLA cannot guarantee timely synchronous response

Otherwise synchronous operation is allowed.

### Approval requests
Approval requests MUST be asynchronous.

Reason: approval is inherently externalized and time-variable.

### Decision creation
Decision record creation SHOULD be synchronous.

---

## 7.3 Execution API

### Action envelope submission
Execution MAY be:
- validation-only
- synchronous validation + immediate execution
- asynchronous queued execution

The mode MUST be explicit via request preference or endpoint profile.

### Execution receipts
Execution receipts are always durable records and SHOULD be synchronous to record, even if the actual action completed earlier.

---

# 8. Async operation semantics

## 8.1 Operation identity

Each async operation MUST have:
- `operation_id`
- `status`
- `created_at`
- `updated_at`
- `status_url`

It SHOULD have:
- `result_url`
- `callback_url` if supplied by client

---

## 8.2 Operation state rules

Allowed states:

- `pending`
- `running`
- `awaiting_human`
- `succeeded`
- `failed`
- `cancelled`

Allowed transitions:

```text
pending -> running
pending -> awaiting_human
running -> awaiting_human
running -> succeeded
running -> failed
running -> cancelled
awaiting_human -> running
awaiting_human -> succeeded
awaiting_human -> failed
awaiting_human -> cancelled
```

Invalid transitions MUST be rejected.

---

## 8.3 Terminal state rules

Terminal states:
- `succeeded`
- `failed`
- `cancelled`

Once terminal, the operation MUST NOT transition again.

---

## 8.4 Result binding

If operation type is:

### Policy evaluation
- `succeeded` MUST bind to a `PolicyDecision`

### Approval request
- `succeeded` MUST bind to an `ApprovalArtifact`

### Execution request
- `succeeded` SHOULD bind to an `ExecutionReceipt`
- and SHOULD have at least one corresponding ledger event

---

# 9. State-machine constraints

## 9.1 Task lifecycle constraints

Minimum allowed task progression:

```text
CREATED
-> BOUND
-> DELEGATED
-> SKILL_BOUND (optional)
-> COMMERCE_INIT (optional)
-> ANALYZING
-> DECIDED
-> POLICY_CHECKED
-> APPROVAL_PENDING (optional)
-> EXECUTING
-> COMPLETED
```

Failure states:
- `DENIED`
- `REVOKED`
- `QUARANTINED`
- `FAILED`

### Mandatory transition guards

- `CREATED -> BOUND` requires valid `LiabilityBinding`
- `BOUND -> DELEGATED` requires valid `CapabilityToken`
- `ANALYZING -> DECIDED` requires valid `DecisionRecord`
- `DECIDED -> POLICY_CHECKED` requires valid `PolicyDecision`
- `POLICY_CHECKED -> APPROVAL_PENDING` required if policy result is `require_approval`
- `POLICY_CHECKED -> EXECUTING` allowed only if policy result is `allow`
- `APPROVAL_PENDING -> EXECUTING` requires valid `ApprovalArtifact`
- `EXECUTING -> COMPLETED` SHOULD require at least one `ExecutionReceipt` or equivalent proof of execution
- any active state MAY transition to `REVOKED` if required authority is revoked
- any active state MAY transition to `QUARANTINED` on taint or integrity failure

---

## 9.2 Commerce constraints

If `commerce_session_ref` is present in a `DecisionRecord` or `ActionEnvelope`:

- referenced `CommerceSession` MUST exist
- `CommerceSession.status` MUST be compatible with the requested action
- checkout/order-creating actions MUST NOT execute if session status is `failed` or `cancelled`

For payment-bearing commerce:
- `payment_ref` or equivalent payment authorization reference MUST be present before execution

---

# 10. Execution validation rules

Before accepting or executing an `ActionEnvelope`, the Execution API MUST verify:

1. referenced `CapabilityToken` exists
2. token not expired
3. token not revoked
4. any ancestor delegation not revoked
5. `DecisionRecord` exists
6. `PolicyDecision` exists and is valid
7. if policy result is `require_approval`, valid `ApprovalArtifact` exists
8. `ApprovalArtifact` not expired
9. `ApprovalArtifact` scope covers intended action
10. requested operation is within token authority
11. parameter ranges are within allowed bounds
12. task is not already terminal in a conflicting state
13. required signatures validate
14. tainted content has not been promoted unlawfully
15. required commerce/payment references are present when relevant

Failure on any item MUST fail closed.

---

# 11. Revocation semantics

## 11.1 Immediate effect

Revocation MUST take effect at `effective_at`.

If omitted by deployment profile, effect is immediate at receipt time.

---

## 11.2 Propagation rules

Revoking a `CapabilityToken` MUST invalidate:
- direct usage of that token
- all descendant delegations
- all future action envelopes depending on them

Revoking a `SkillManifest` MUST:
- block future high-risk use of that skill
- NOT retroactively invalidate already completed historical decisions
- but SHOULD mark dependent in-flight tasks for reevaluation or quarantine

Revoking a `CommerceSession` MUST:
- block future checkout/order actions for that session

---

## 11.3 In-flight execution

If revocation occurs after an action has already executed externally:
- historical records remain valid
- new execution MUST stop
- a ledger event documenting revocation impact SHOULD be appended

---

# 12. Retry semantics

## 12.1 Safe retries

Safe to retry with same idempotency key:
- artifact creation requests
- async requests
- ledger appends that were not acknowledged

Unsafe to retry without idempotency key:
- action execution
- approval creation
- revocation creation
- ledger appends

---

## 12.2 Client guidance

Clients SHOULD retry only when:
- transport error occurred
- timeout occurred before response
- server returned retryable error

Clients SHOULD NOT retry on:
- scope violation
- invalid signature
- policy denied
- taint blocked
- approval expired
- revocation conflict

---

# 13. Error code profile

Minimum standard codes:

- `AGP_INVALID_REQUEST`
- `AGP_INVALID_SIGNATURE`
- `AGP_UNAUTHORIZED`
- `AGP_FORBIDDEN`
- `AGP_NOT_FOUND`
- `AGP_IDEMPOTENCY_CONFLICT`
- `AGP_SCOPE_VIOLATION`
- `AGP_TOKEN_EXPIRED`
- `AGP_TOKEN_REVOKED`
- `AGP_DELEGATION_REVOKED`
- `AGP_POLICY_DENIED`
- `AGP_APPROVAL_REQUIRED`
- `AGP_APPROVAL_EXPIRED`
- `AGP_TAINT_BLOCKED`
- `AGP_EVIDENCE_INSUFFICIENT`
- `AGP_COMMERCE_SESSION_INVALID`
- `AGP_PAYMENT_REFERENCE_REQUIRED`
- `AGP_LEDGER_UNAVAILABLE`
- `AGP_OPERATION_FAILED`
- `AGP_OPERATION_CANCELLED`

### Mapping guidance

- `400` for malformed input
- `401` for missing/invalid auth
- `403` for authenticated but not permitted
- `404` for missing resource
- `409` for idempotency conflict, state conflict, revocation conflict
- `422` for semantically invalid but well-formed request
- `202` for accepted async work

---

# 14. Ordering guarantees

## 14.1 Ledger ordering

Within a single task stream:
- ledger events MUST have deterministic order
- `prev_event_hash` SHOULD hash-chain to prior event in that task stream

If strict total ordering is not available globally, per-task ordering is sufficient.

---

## 14.2 Replay ordering

Replay endpoints MUST return events in task order.

Replay stream SHOULD emit:
1. historical events in order
2. a terminal replay completion signal

---

# 15. Webhook / callback profile

## 15.1 Callback support

If `callback_url` is provided for async operations, servers MAY send callbacks.

If callbacks are supported, servers MUST:
- use HTTPS
- sign callback payloads or authenticate them
- retry on transient failures
- stop retrying after a defined max attempt profile

---

## 15.2 Callback payload

Callback payload SHOULD be an `AsyncOperation`.

If final:
- `status` MUST be terminal
- `result_url` SHOULD be present when applicable

---

## 15.3 Callback verification

Implementations MUST define one of:
- HMAC signature header
- detached JWS
- mutual TLS callback channel

If callback authenticity cannot be verified, clients MUST ignore it.

---

# 16. Taint and evidence enforcement profile

## 16.1 Taint defaults

External or retrieved content MUST default to:
- untrusted
- non-instruction-eligible

---

## 16.2 Taint propagation

If a derived artifact is materially based on tainted content, the taint MUST propagate unless:
- explicit policy clearance exists, or
- human review has cleared it, or
- a verified transformation rule removes it

---

## 16.3 Evidence sufficiency

For `high` or `critical` risk actions:
- unverified evidence alone is insufficient
- disputed evidence is blocking unless explicitly overridden by policy and approval

---

# 17. Minimum audit requirements

An implementation MUST be able to reconstruct for any consequential action:

- which principal sponsored the task
- which agent acted
- what capability was used
- which decision was made
- what policy result applied
- whether approval was required and granted
- what execution happened
- what ledger events recorded it
- whether revocation affected the workflow

If it cannot reconstruct that, it is not actually accountable.

---

# 18. Endpoint-level behavior summary

## Registry API
- mostly synchronous
- strongly permissioned
- idempotent for writes
- no fail-open behavior

## Decision API
- mixed sync/async
- async required for approvals
- async allowed for policy evaluations
- must preserve decision provenance

## Execution API
- fail closed on missing prerequisites
- supports validate-only and async execution
- durable receipts and ledgering required for consequential actions

---

# 19. Minimum production profile

A deployment claiming **AGP Production Profile** MUST implement:

- OAuth2 or mTLS auth
- signed control artifacts
- idempotency keys on required POSTs
- async operation status endpoint
- revocation propagation
- approval request workflow
- fail-closed execution enforcement
- append-only task replay
- standardized error codes

Anything less is a demo profile, not production.

---

# 20. Blunt assessment

This is now the part that makes the whole thing credible.

Before this, the spec was:
- decent object model
- decent endpoint design
- weak runtime meaning

With this profile, it becomes:
- implementable
- testable
- enforceable
- harder to fake

Still missing for a truly serious package:
- formal signature/JWS profile
- reference authz matrix by actor and scope
- conformance test suite
- event schema for A2A/MCP/UCP/AP2 bindings

Those would be the next real steps.

---

# 21. Multi-Agent Governance Profile

## 21.1 Agent role taxonomy

AGP implementations operating in high or critical risk contexts SHOULD deploy three distinct governance roles:

- **`executive`** — the agent focused on task completion and tool execution
- **`compliance_monitor`** — monitors execution in real time against policy and Purple Line constraints; has veto authority
- **`impact_assessor`** — simulates short, medium, and long-term consequences before a decision is finalised

A single physical agent MAY hold multiple roles, but MUST preserve their logical independence. A compliance_monitor MUST NOT be the same logical identity as the executive agent it is monitoring.

---

## 21.2 Governance requirements on tasks

A `Task` MAY declare `governance_requirements`, specifying which roles must attest before execution is permitted.

```json
{
  "governance_requirements": {
    "required_roles": ["executive", "compliance_monitor", "impact_assessor"],
    "quorum": 2
  }
}
```

If `quorum` is omitted, all declared roles must attest.

---

## 21.3 Governance attestations on action envelopes

Each `ActionEnvelope` MUST carry `governance_attestations` when the task declares `governance_requirements`.

Each attestation has a `verdict`:
- `cleared` — agent approves execution
- `flagged` — agent blocks execution; MUST trigger `APPROVAL_PENDING` or `QUARANTINED` transition
- `conditional` — execution allowed only if stated `conditions` are met

Execution MUST be blocked until:
1. All required roles have attested
2. No attestation carries a `flagged` verdict
3. All `conditional` conditions have been verified

If any attestation is `flagged`, the execution domain MUST fail closed and surface the flag to the human review path.

---

## 21.4 Compliance monitor authority

A `compliance_monitor` attestation with `flagged` verdict carries higher automatic weight than other roles. Implementations MUST:

- Immediately pause the task
- Transition to `APPROVAL_PENDING` (minimum)
- Preserve the attestation and its signature in the audit trail

The compliance monitor's `flagged` verdict cannot be overridden by the executive agent alone. It requires an `ApprovalArtifact` from an `approver` issuer class.

---

# 22. Impact Assessment Profile

## 22.1 When required

An `ImpactAssessment` produced by an `impact_assessor` agent MUST be linked from the `DecisionRecord` via `impact_assessment_ref` when:

- Task `risk_tier` is `high` or `critical`, AND
- `action_class` is `transact`, `delete`, or `admin`

For other combinations it is RECOMMENDED.

---

## 22.2 Time horizon coverage

Impact assessments MUST cover at minimum:
- `short_term` for `medium` risk actions
- `short_term` and `medium_term` for `high` risk actions
- `short_term`, `medium_term`, and `long_term` for `critical` risk actions

Each horizon entry MUST declare:
- `consequences` (non-empty list)
- `severity` (negligible → critical)
- `reversible` (boolean — whether the effect can be undone post-revocation)

---

## 22.3 Pareto constraint check

For `transact` and `delete` action classes, the `pareto_assessment` field MUST be populated.

If `improves_without_harm` is `false`, the assessment MUST list `harmed_parties` and MUST indicate whether `mitigation_available`.

An impact assessment with `improves_without_harm: false` and `mitigation_available: false` SHOULD result in a `recommendation` of `require_human_review` or `block`.

---

## 22.4 Recommendation semantics

The `recommendation` field is advisory, not binding. It informs the policy engine — it does not replace the `PolicyDecision`.

However:
- A `block` recommendation from the impact assessor MUST be surfaced in the audit trail
- A `block` recommendation SHOULD trigger `require_approval` policy result unless the policy engine has explicit override authority
- Policy engines MUST record whether they overrode a `block` recommendation and why

---

# 23. Agent-Initiated Escalation Profile (Whistleblower)

## 23.1 The problem this solves

The AGP task lifecycle supports external revocation and quarantine, but prior to this profile, an agent had no way to raise a concern without either proceeding or silently abandoning. This profile adds a first-class mechanism for any agent to escalate an ethical concern without being the executing party.

---

## 23.2 Who may raise an escalation

Any authorized agent with write access to the decision domain MAY raise an `EscalationNotice`. The raising agent:
- Does NOT have to be the executing agent
- Does NOT have to be the policy engine
- MUST be authenticated and their identity bound to the notice via signature

---

## 23.3 Mandatory task transitions

On receipt of a valid `EscalationNotice`, the receiving system MUST initiate a task transition:

| `requested_action`   | Required task transition       | Human required |
|----------------------|-------------------------------|----------------|
| `quarantine`         | → `QUARANTINED`               | No             |
| `pause_and_review`   | → `APPROVAL_PENDING`          | Yes            |
| `escalate_to_human`  | → `APPROVAL_PENDING`          | Yes (mandatory human approver) |

`QUARANTINED` via escalation is immediate and does not require a prior `PolicyDecision`. This is the exception to the normal state machine guard rules — intentional, because the raising agent may be alerting to a condition that would prevent policy evaluation from completing safely.

---

## 23.4 Immutability

An `EscalationNotice` MUST NOT be deleted even if later dismissed. The record — including its `resolution` — is a permanent part of the audit trail.

A dismissed escalation MUST record:
- `resolved_by` (identity of the resolving authority)
- `outcome: dismissed`
- `notes` explaining the dismissal rationale

---

## 23.5 Compliance monitor weight

An `EscalationNotice` raised by an agent with `raising_agent_role: compliance_monitor` MUST be treated with higher automatic severity than escalations from other roles. Implementations SHOULD:
- Require dual approval to dismiss a compliance_monitor escalation
- Flag the escalation to the `revocation_issuer` class for awareness

---

# 24. Ethical Framework Declaration Profile

## 24.1 Why this matters

Two policy engines can both claim "policy compliant" while applying incompatible ethical frameworks — one utilitarian, one rights-based — and produce opposite results on the same input. Without framework declaration, the audit trail is incomplete: it records what was decided but not the ethical basis for the decision.

---

## 24.2 Where ethical_framework appears

The `ethicalFramework` object appears on:
- `SkillManifest.ethical_framework` — the framework the skill is designed to operate under
- `PolicyDecision.ethical_framework` — the framework applied to reach this specific decision
- `ImpactAssessment.ethical_framework_applied` — the framework used to evaluate consequences

---

## 24.3 Required contexts

`ethical_framework` MUST be populated on `PolicyDecision` when:
- `result` is `deny` or `quarantine`, AND
- Task `risk_tier` is `high` or `critical`

`ethical_framework` MUST be populated on `SkillManifest` when:
- `risk_class` is `high` or `critical`

In all other contexts it is RECOMMENDED.

---

## 24.4 Framework definitions

| Framework | Decision test |
|---|---|
| `veil_of_ignorance` | Would this rule be fair if I did not know my position in the outcome? (Rawlsian) |
| `pareto_optimal` | Does the action make at least one party better off without making any party worse off? |
| `utilitarian` | Does the action produce the greatest aggregate benefit for the greatest number? |
| `rights_based` | Are there rights that cannot be violated regardless of aggregate benefit? |
| `value_pluralist` | Multiple frameworks held in explicit tension; resolution recorded in `obligations` |
| `custom` | Implementation-specific; `policy_ref` is required and must resolve to a declared policy |

---

## 24.5 Framework consistency

Implementations SHOULD validate that:
- A `PolicyDecision` with `primary: pareto_optimal` does not produce `allow` when the linked `ImpactAssessment` reports `improves_without_harm: false` without recorded mitigation
- A `PolicyDecision` with `primary: rights_based` does not produce `allow` when `obligations` contains a rights violation

These validations are advisory in v0.5. A future conformance test suite SHOULD make them enforceable.
