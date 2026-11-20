# AGP v0.9 — Proposed Extensions from a Production Deployment
## The principal register (E1), detectors (E2), and the changes a bank deployment needed

**Status:** Proposal to the AGP working group — not yet part of AGP
**Builds on:** AGP Implementation Profile v0.5-draft (`spec/implementation-profile.md`), AGP v0.9 objects and APIs
**Reference implementation:** `agp-platform`, branch `agp-v0.9-studio` (server) — every behaviour below is implemented and tested there
**Conformance:** `conformance/tests/test_production.py` (`--profile production`) and `test_decision.py` in the same repository
**Relation to the Implementation Profile:** §2 proposes additions to its §19 *Minimum production profile*; §§3–9 are new extensions, each claimable on its own
**Origin:** running AGP beside the BIAN Agentic Banking Studio, where people, chat assistants, MCP tokens, API keys, published A2A agents and generated BIAN services all act on a bank's data

The key words MUST, MUST NOT, SHOULD and MAY are to be read as in RFC 2119.

---

# 1. Why

AGP v0.9 models *authority* well — tasks, liability, capability tokens, delegations, decisions, approvals, envelopes, the §10 gate, revocation. Putting it in front of a real product showed what it doesn't yet say:

| Gap in v0.9 | Consequence | Section |
|---|---|---|
| A principal is any string a task names; nothing records who acts or can stop them | A compromised agent or person keeps acting until every token is found and revoked | §3 (E1) |
| A caller writes its own policy verdict | The gate trusts a `allow` the caller made up | §2.1 |
| An approval names an approver but isn't bound to a person, an action or its parameters | One approval can be replayed for another action; a person can approve their own | §2.2 |
| Nothing watches behaviour | Scope probing, bulk export, a copied token, a looping agent go unnoticed | §4 (E2) |
| Only what passes through AGP is on the ledger | A product's own acts — reads, exports, sign-ins, AI calls — aren't recorded anywhere tamper-evident | §5 |
| `/agp/validate` needs an ActionEnvelope | An agent's tool call outside a task can't be checked | §6 |
| Policy is code per regulation | A bank can't load a regulation, or its own standard, as data | §7 |
| One tenant | A platform serving several banks mixes their objects | §2.4 |
| The ledger and its readers see everything | Personal data and secrets leak through ledger reads, webhooks and logs | §8 |

Each section gives the behaviour an implementation MUST have to claim the extension, the objects and endpoints, and what the reference implementation does where the proposal leaves a choice.

---

# 2. Changes to core behaviour

These tighten v0.9's existing semantics rather than add surface. The proposal is that the Implementation Profile's **§19 Minimum production profile** ("AGP Production Profile") also require all of §2 — today's §19 list (signed artifacts, revocation propagation, an approval workflow, fail-closed execution, …) doesn't yet say whose verdict counts, who may approve, or what the ledger must resist.

## 2.1 Verdicts come from the server

- A PolicyDecision's verdict MUST be computed by the server from an active PolicySet that names an engine the server runs (`policy_engine`). A caller-supplied `verdict` MUST NOT count; it MAY be kept as `caller_verdict` for the record.
- `POST /agp/decision/policy-evaluations` requires `policy_set_ref` (or `policy_set_refs`, §7.4). A PolicySet without a server-side engine MUST be refused at registration (400) and at evaluation (422 `AGP_POLICY_NO_ENGINE`).
- The §10 gate MUST refuse a PolicyDecision not marked `server_computed` (422 `AGP_POLICY_DENIED`).
- Compatibility: an implementation MAY offer a v0.5 mode (`AGP_CALLER_VERDICTS=1` in the reference) in which callers' verdicts count. It MUST NOT be the default, and an implementation running in it MUST NOT claim the AGP Production Profile (§19, as extended here).

## 2.2 Approvals bound to people

An **ApprovalRequest** (schema: `schemas/approval-request.json`) asks for an action identified by `action` (dotted lower case, e.g. `variant.delete`) and `params_hash` (`sha256:` of the action's canonical parameters), for a person.

| Mode | Who approves |
|---|---|
| `self` | the person behind the request (a person confirming what their own assistant proposed) |
| `single` | one person other than the requester and the person it's for |
| `dual`, `multi:n` (2–10) | two / n different such people |
| `hub_and_org` | reinstating a read-only org only (§4.4): one of the org's people and one at the hub |

- An approver MUST be a registered person (§3), active. Agents never approve.
- Nobody MUST decide a request twice; one denial ends it; requests expire (reference: 15 minutes; a two-person action's, a day).
- Each org keeps a **two-person list** of actions that are `dual` at least, whatever mode is asked (`GET / PUT /agp/two-person-actions`). Changing the list is itself a two-person action. Some entries are fixed and can't be removed: reinstating a person, changing the list, changing detector settings, reinstating an org.
- A granted request issues an **ApprovalArtifact** carrying `approver_ids`, `action`, `params_hash`, `requested_for` and `valid_until` (reference: 10 minutes).
- An approval is used once: `POST /agp/approvals/redeem {action, params_hash, requested_for}` finds a granted, unexpired, unused artifact for exactly that action, those parameters and that person and marks it used (a write-once `approval_uses` record; a second redemption is refused).
- The §10 gate MUST, for an approval: refuse one past `valid_until`; refuse one approved by the task's own principal; refuse one whose `params_hash` differs from the envelope's.
- A request MAY carry `payload` (≤ 4 KB): what the product needs to carry the action out once granted (e.g. the ids of the task chain it opened). A request bound to a task (`task_id`) moves the task: granted → `POLICY_CHECKED`; denied or expired → `DENIED`.

## 2.3 Revocation that bites

- A RevocationNotice counts from its `effective_at`, not before.
- Revoking a delegation revokes every delegation below it and every capability token resting on any of them. This MUST be computed when checked (so nothing can be left behind) and SHOULD be recorded on the ledger when issued (`revocation.cascaded`).
- A revoked task moves to `REVOKED` if it isn't finished.

## 2.4 Tenancy

- Every object belongs to the org of the token that created it (an `org` claim; a client belongs to one org). An org MUST NOT read or change another's objects; a request naming another org's object answers as if it didn't exist.
- Object identity is `(type, id)`. (The reference's Postgres store keyed objects on `id` alone; an approval and its use share an id and one overwrote the other. Keyed on the pair since.)
- PolicySets MAY be shared read-only across orgs (`org = "*"`) for an implementation's built-in policies.

## 2.5 The ledger

- Each org has its own hash chain. The store MUST NOT let the server's own database role alter or delete a ledger row (the reference grants `INSERT, SELECT` only, and triggers refuse the rest).
- Writes happen before acts: an event that can't be recorded stops the act.
- **Signed checkpoints**: the chain head is periodically signed (Ed25519), optionally anchored to an RFC 3161 time-stamping authority. `GET /agp/ledger/verify` recomputes the chain and checks every checkpoint.
- **Evidence packs**: `GET /agp/ledger/evidence?from=&to=` exports an org's range as a zip an auditor checks offline, without trusting AGP or whoever exported it — the rows, the checkpoints covering them, the keys, a signed manifest, and a standalone checker. The export is itself on the ledger first.
- Governance objects are **versioned** (tasks, policy sets, principals, approval requests, settings — every change a new version, the history kept) or **write-once** (decisions, policy decisions, approvals, capability tokens, revocations, receipts, anomaly signals, published packs). A write over a version the writer didn't read is refused (stale read).

## 2.6 The product carries out the action

v0.9's synchronous envelope marks the task `COMPLETED` and writes a receipt when the envelope is issued — before anything has happened. When the product, not AGP, performs the action:

- `POST /agp/action-envelopes` with `Prefer: execute-async` MUST move the task to `EXECUTING`, record `action.initiated`, and return an Operation (202).
- The product calls `POST /agp/validate` at the moment it acts.
- Its `POST /agp/execution-receipts` (`outcome`: success / failed) for that envelope MUST finish the task (`COMPLETED` / `FAILED`) and the operation, on the ledger.

---

# 3. E1 — The principal register

**Everyone and everything that acts is registered, with a status that stops it at once.** Schema: `schemas/principal.json`.

- `kind`: `user`, `assistant`, `mcp_client`, `a2a_agent`, `a2a_caller`, `api_key`, `service`, `job`, `script`. Only `user` is a person.
- `acting_for`: the principal this one acts for (an assistant for its user, an MCP token for the person who issued it). It MUST already be registered.
- `status`: `active` · `restricted` (may read, not act) · `suspended` (may do nothing until reinstated) · `revoked` (terminal).
- The **effective status** is the most restrictive along the `acting_for` chain. Suspending a person MUST stop everything acting for them at once; reinstating them restores those agents unless one was suspended on its own. Nothing is copied down the chain.
- **Reinstatement is by people only**: an agent by one admin; a person by two different admins, neither of them the person (the first request is held, 202; the second completes it). A product signing in for all its admins names the admin acting (`on_behalf_of`, a registered person).
- Checked: on every request from a client linked to a principal; when a task or capability names principals; at the §10 gate and `/agp/validate` (`principal_status`); on the capability check (§6). Unregistered principals MAY be allowed for compatibility; an implementation SHOULD offer a mode that refuses them.
- Status changes are on the ledger (`principal.status_changed`, with who and why) and pushed (§9).

| Endpoint | Scope |
|---|---|
| `POST /agp/principals` `{principal_id, kind, acting_for?, display?}` | `agp.principal.admin` |
| `GET /agp/principals`, `GET /agp/principals/{id}`, `GET /agp/principals/{id}/history` | `agp.registry.read` |
| `POST /agp/principals/{id}/status` `{status, reason, on_behalf_of?}` | `agp.principal.admin` |

---

# 4. E2 — Detectors

**A principal whose behaviour turns anomalous is stopped automatically, until people reinstate it.** Schema: `schemas/anomaly-signal.json`.

## 4.1 Model

- Detectors read the ledger as it's written, and look back over it periodically (reference: a worker per event, a one-minute job).
- A finding is an **AnomalySignal** — write-once: detector, principal, score, evidence (the ledger events that set it off), mode, response, and `context` a product may act on (e.g. a session to end). It is on the ledger as `anomaly.detected`, so webhooks carry it.
- Mode, per detector and org: `report` (score and alert, never block — the default while baselines form) · `enforce` (apply the response) · `off`. Changing settings is a two-person action (`detector.settings`). A server MAY set defaults for every org that hasn't set its own.
- **The response ladder**: `record` → `alert` → `step_up` → `restrict` → `suspend` → `org_read_only`. A response goes through the principal register like any status change (`status_by: "detector:<name>"`), so whoever enforces statuses refuses the next request.

## 4.2 The detectors

| Detector | Triggers on (reference defaults) | Default |
|---|---|---|
| `scope_probing` | 10 refusals in 5 minutes | enforce → suspend |
| `integrity` | the org's chain or signed checkpoints don't verify | enforce → org read-only |
| `velocity` | over 120 acts a minute, or 10× the principal's baseline | report → step-up |
| `ai_spend` | over 2 M tokens an hour (or 10× baseline); the same prompt 8 times in 10 minutes | report → suspend |
| `bulk_read` | 300 distinct reads or 5 exports in 10 minutes | report → restrict |
| `destructive` | 20 deletes in 10 minutes | report → suspend |
| `credentials` | 5 failed sign-ins on one account in 10 minutes; one session from two networks within 5 minutes (a copied token — `context.end_session`); an MCP token, API key or A2A caller on a new network after 20 acts | report → step-up |
| `agent_behaviour` | an agent calling the same tool with the same arguments 6 times in 5 minutes; a changing tool call in a turn that came with an attached document (possible prompt injection) | report → suspend |
| `time` | a high-risk act at an hour the principal hardly ever works | report → step-up |

Networks and sessions are opaque ids a product reports (an HMAC of the client's /24 or /48 and of the session id, keyed with the product's secret): AGP never holds an address, so impossible travel — which needs places — is out of scope.

## 4.3 Step-up

Between alert and restrict: the principal stays active but its next **change** is refused (`AGP_STEP_UP_REQUIRED`) until a person signs in again (a product clears it when they do) or, for an agent, a person clears it (`POST /agp/principals/{id}/step-up/clear {how}`).

## 4.4 Org read-only, and the hub operator

- An integrity failure makes the org **read-only**: writes are refused (423 `AGP_ORG_READ_ONLY`) except governance itself, reported events and content — what happens meanwhile is still recorded.
- Reinstating the org (`POST /agp/org-status {status: active, reason}`) is a two-person action. Where a platform operates many banks from a hub, it is `hub_and_org`: one of the org's own people and one person at the hub.
- **The hub operator** holds one credential not tied to any org, scope `agp.operator` and nothing else. It can list read-only orgs and their reinstatement requests (`GET /agp/operator/orgs`) and decide the hub's half (`POST /agp/operator/orgs/{org}/approval-requests/{id}/decisions`, naming the hub's person). It can't read an org's ledger or decide anything else.

| Endpoint | Scope |
|---|---|
| `GET /agp/detectors`, `GET /agp/anomaly-signals`, `GET /agp/org-status` | `agp.registry.read` |
| `PUT /agp/detectors` (202, two-person), `POST /agp/org-status` (202) | `agp.principal.admin` |
| `POST /agp/principals/{id}/step-up/clear` | `agp.principal.admin` |
| `GET /agp/operator/orgs`, `POST /agp/operator/orgs/{org}/approval-requests/{id}/decisions` | `agp.operator` |

---

# 5. What a product reports, and what was said

## 5.1 Reported events

A product that governs through AGP also reports what happens on its side — requests (reads included, metadata only), tool calls, AI calls, exports, sign-ins, refusals — so that one tamper-evident ledger holds all of it. Schema: `schemas/reported-event.json`.

- `POST /agp/events {events: [...]}` (≤ 500; `agp.execution.write`). Each event is checked before any is written.
- AGP MUST set what the reporter can't be trusted to say: `actor` (the token's client), the org, and `source: "reported"`.
- `client_event_id` is kept per org: a retried batch MUST record each event once. (The reference's Postgres store read a seen key as unseen when its object lived only in the ledger, and recorded retries twice; found by the conformance suite.)
- Consequential acts SHOULD be reported before they happen and waited for (`outcome: initiated`), their result after; reads MAY be batched.

## 5.2 Content kept apart from the ledger

Prompts and answers are kept in full, apart from the ledger, with their own retention per org; the ledger keeps only their hashes, for as long as the ledger is kept — so an event still proves what was said after the words are gone.

- `POST /agp/content` (`agp.execution.write`): the id is the content's hash; a `sha256` that doesn't match is refused. Never changed once stored; deleted only past its retention.
- `GET /agp/content/{id}` (`agp.content.read`): every read is on the ledger first.
- `GET / PUT /agp/content-retention`.

---

# 6. Checking an agent's capability outside a task

`/agp/validate` needs an ActionEnvelope, so it covers actions inside a task. An agent's tool calls — a chat assistant, an MCP token, a generated service's operations — mostly happen outside one. Each such agent holds a CapabilityToken naming the tools it may use, and asks before every changing call:

`POST /agp/capabilities/{id}/check {agent_id, tool_id, acting_for?, policy_set_refs?, signals?, arguments?, risk_tier?}` (`agp.execution.write`)

Checks in order: `capability_exists` · `agent_identity` · `capability_not_expired` · `capability_not_revoked` (its own or its delegation chain's) · `tool_permitted` (`*` permits all) · `principal_status` (the agent, whom its capability acts for, and `acting_for` — the principal behind this call, e.g. the person a service is serving: suspended there, refused here, whatever agent carries it) · `policy`, if asked — the given PolicySets, or `"installed"` (every pack installed in the org, §7), judge this call from its `signals` and `arguments`: `deny` / `quarantine` refused citing the provision, `require_approval` refused as `approval_required` (an automated caller has nobody to ask).

200 `PERMIT`, or 403 `DENY` with `failed_check` and `reason`. A DENY MUST be on the ledger (`enforcement.denied`); a PERMIT need not be (the caller's own `tool.call` names the capability). The arguments are judged, not kept.

Revoking the capability stops the agent's next changing call — the kill switch §11 of v0.9 describes, for agents outside tasks.

---

# 7. Policy Packs

Policy as data: a regulation, or a bank's own standard, as one document of PolicySets. Schema: `schemas/policy-pack.json`. (The format follows the v1.0 line's `kind: PolicyPack`; the tenancy, citations and combination below are new.)

## 7.1 Format

```yaml
apiVersion: agp/v1
kind: PolicyPack
metadata: {pack_id: bank/consumer-credit, name: …, version: "1.0.0", publisher: …, citation: {instrument: …, regulator: …}}
spec:
  policy_sets:
    - name: consumer-credit
      version: "1.0.0"
      publisher: …
      regulatory_frameworks: [US-PA]
      jurisdictions: [US-PA]
      policy_engine: rules
      default_verdict: allow
      rules:
        - id: no-hidden-charges
          verdict: deny
          rationale: Costs and charges must be itemised.
          source_refs: [{instrument: "12 Pa.C.S.", provision: "§6224"}]
          effective_from: "2025-01-01"
          condition:
            all:
              - {field: signals.bian.service_domains, op: in, value: [Consumer Loan]}
              - {field: args.itemised, op: eq, value: false}
  controls: [{name: disclosure, source_refs: [{provision: "§6222"}]}]
  signals: [{path: bian.service_domains, type: array}]
```

A rule: `id`, `verdict`, `rationale`, `condition` — a tree of `all` / `any` / `not` over leaves `{field, op, value}` (ops: `eq ne lt lte gt gte in not_in contains contains_any starts_with regex exists`) — `scope.tools`, `source_refs` (each with a `provision`), `effective_from` (inclusive) / `effective_until` (exclusive), `set` (derived attributes), `require` (controls). Fields read the task: `intent`, `tool`, `outcome`, `risk_tier`, `jurisdictions`, `frameworks`, `principal_id`, `args.*` and `signals.<namespace>.*`. A Task MAY carry `tool`, `intent`, `arguments` and `signals` for conditions to read. First matching rule wins; otherwise `default_verdict`.

## 7.2 Channels and tenancy

- **official** — shipped with the implementation, read-only, visible to every org.
- **org** — published by an org (`POST /agp/packs {manifest}`), that org's only. A published version MUST NOT change; publish a new version.
- Installing (`POST /agp/packs/install {pack_id, version?}`) makes the pack's PolicySets in the installing org, with new ids, tagged with the pack. A new version deprecates the sets of the version it replaces. Installing the same version again changes nothing.
- Uninstalling (`POST /agp/packs/uninstall {pack_id}`) stops it applying: its PolicySets are deprecated, not deleted — they remain the record of what applied when.

## 7.3 Verdicts cite their provisions

A PolicyDecision from a rule MUST name what decided it: `matched_rule`, `matched_conditions`, `source_refs`, `require`, `pack_id` — on the object and on the ledger (`policy.verdict`). A refusal therefore cites the provision it enforces.

## 7.4 Several sets at once

`POST /agp/decision/policy-evaluations` MAY take `policy_set_refs` (≤ 20): each set is evaluated and the most restrictive verdict wins — `deny` > `quarantine` > `require_stronger_auth` > `require_approval` > `allow` — with every result kept under `evaluations`. (An org's installed packs are evaluated beside the product's own policy.)

| Endpoint | Scope |
|---|---|
| `GET /agp/packs`, `GET /agp/packs/manifest?pack_id=&version=` | `agp.registry.read` |
| `POST /agp/packs`, `POST /agp/packs/install` | `agp.registry.write` |

---

# 8. Data masking

What's read out of AGP is masked; what's stored isn't — the ledger's hashes are over the real events, so it still verifies.

- **Where**: ledger reads (`GET /agp/ledger-events`, task replay), webhook payloads, approval requests' summaries and reasons, and log lines.
- **What**: in an event's `detail`, `action` and `resource` — named fields (secrets redacted; direct identifiers partly masked; customer and subject ids pseudonymised under the implementation's key) and, in any text, recognisable keys, tokens, JWTs, private keys, emails, IBANs, Luhn-valid card numbers, SSNs, IPv4 addresses and phone numbers. Ids, hashes, times and the chain MUST NOT be touched.
- **Raw**: `?raw=true`, with scope `agp.execution.admin` only — never granted by default.
- **Evidence packs stay whole**: they are the integrity record, checked offline against the events' hashes.

---

# 9. Statuses pushed

A product enforcing AGP's statuses needs them at once, not on its next poll.

- `GET /agp/status-stream` (Server-Sent Events): every principal and org status change, and step-up asked or cleared.
- `GET /agp/principals-blocked`: the current blocked set (`org_status`, each principal's effective status, why, and by whom; `step_up` entries) — read on connect, and periodically as a backstop.
- Across server instances, a change on one MUST reach the streams on all (the reference uses Postgres `NOTIFY` / `LISTEN`).

---

# 10. Scopes

| Scope | Granted by default | For |
|---|---|---|
| `agp.principal.admin` | yes | the principal register, detector settings, step-up, org status |
| `agp.content.read` | yes | reading kept content (each read on the ledger) |
| `agp.org.provision` | **no** — by name | creating an org's first client; re-scoping and re-issuing the clients it provisioned |
| `agp.operator` | **no** — by name | the hub operator (§4.4) |
| `agp.execution.admin` | **no** — by name | reading the ledger unmasked (§8) |

A client MUST NOT be given scopes beyond its creator's own.

---

# 11. Conformance

The reference suite has two profiles:

- **v0.5** (`pytest tests/`, server with caller verdicts allowed): the v0.9 protocol — registry, decision (now complete: contexts and taint, evidence, decisions, policy evaluations, impact, escalations), execution, security, v0.9 — 70 tests.
- **production** (`pytest tests/test_production.py --profile production`, server computing every verdict) — the §19 Production Profile as extended by §2 here, plus §§3, 6, 7 — server verdicts, approvals bound to people, the whole chain with `execute-async` and its receipt, a suspended agent refused at validate, the capability check, reported events, packs with cited verdicts — 12 tests.

A server whose detectors enforce will suspend the suite's agent for scope probing (its refusals are deliberate): run it with scope probing in report mode.

---

# 12. Open questions for the working group

1. **Principal ids** are the product's own (`user:3f2…`) and per org. Should AGP define a URI form, or federate them (a hub's person deciding in a bank's org, §4.4)?
2. **`hub_and_org`** assumes one hub. Should a bank's AGP trust more than one operator, and how is an operator's credential rotated?
3. **Detectors' thresholds** are the reference's. Should the protocol fix the signals and the ladder and leave thresholds to implementations, or publish recommended values?
4. **The capability check (§6)** overlaps `/agp/validate`. Should validate accept a capability without an envelope instead?
5. **Packs' `signals`** are a namespaced vocabulary a product fills. Should AGP register namespaces (`bian.*` for BIAN Service Domains, `aiact.*`, …)?
6. **`execute-async`** (§2.6) changes when v0.9's synchronous envelope completes a task. Should the synchronous form be deprecated for products that act themselves?
7. **Masking (§8)** is on reads only. Should evidence packs offer a masked variant with a separate attestation?
