"""
AGP MCP Server

Exposes the AGP governance lifecycle as MCP tools so that Claude (and
any MCP-compatible agent) can participate in accountability-governed
workflows without raw HTTP calls.

Tool groups
-----------
Registry tools  — task management, liability, capabilities, policy sets
Decision tools  — decision records, policy evaluation, approvals, escalations
Execution tools — action envelope submission, validate-only, audit replay
Session tools   — high-level one-call lifecycle wrapper

Usage
-----
  python -m agp_mcp           # stdio transport (Claude Desktop)
  python -m agp_mcp --sse     # SSE transport (remote MCP host)
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Annotated, Any

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from .config import Config

# ── Lazy client ───────────────────────────────────────────────────────────────

_config: Config | None = None
_http: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(server: FastMCP):  # type: ignore[type-arg]
    global _config, _http
    _config = Config()
    _http = httpx.AsyncClient(
        base_url=_config.base_url,
        headers={"Content-Type": "application/json", **_config.headers},
        timeout=_config.timeout_ms / 1000,
    )
    try:
        yield
    finally:
        if _http:
            await _http.aclose()


def _client() -> httpx.AsyncClient:
    if _http is None:
        raise RuntimeError("MCP server not fully started — _http client is None")
    return _http


async def _request(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
    prefer: str | None = None,
) -> Any:
    """Send an HTTP request to the AGP server and return the parsed JSON body."""
    headers: dict[str, str] = {}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    if prefer:
        headers["Prefer"] = prefer

    try:
        response = await _client().request(
            method,
            path,
            json=body,
            params={k: v for k, v in (params or {}).items() if v is not None},
            headers=headers,
        )
    except httpx.RequestError as exc:
        raise ToolError(f"AGP server unreachable: {exc}") from exc

    if not response.is_success:
        try:
            err = response.json().get("error", {})
            msg = err.get("message") or response.text
            code = err.get("code", f"HTTP_{response.status_code}")
        except Exception:
            msg = response.text
            code = f"HTTP_{response.status_code}"
        raise ToolError(f"[{code}] {msg}")

    return response.json()


def _fmt(obj: Any) -> str:
    """Pretty-print a JSON-serialisable object as a tool return value."""
    return json.dumps(obj, indent=2)


import uuid
from datetime import datetime, timedelta, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _future(days: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _ikey() -> str:
    return uuid.uuid4().hex


# ── FastMCP server ────────────────────────────────────────────────────────────

mcp = FastMCP(
    name="agp",
    instructions=(
        "AGP governance server binding. "
        "Use these tools to register tasks, record decisions, "
        "evaluate policies, and gate execution under the Agent Accountability "
        "and Control Protocol. Always call create_task before any governed action."
    ),
    lifespan=lifespan,
)

# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRY TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
async def create_task(
    principal_id: Annotated[str, "ID of the agent requesting the task"],
    requested_outcome: Annotated[str, "Human-readable description of what the agent intends to do"],
    risk_tier: Annotated[str, "Risk classification: low | medium | high | critical | extreme"],
    sponsoring_entity: Annotated[str | None, "Organisation sponsoring this task"] = None,
    jurisdictions: Annotated[list[str] | None, "Applicable legal jurisdictions, e.g. ['EU', 'US-CA']"] = None,
    regulatory_frameworks: Annotated[list[str] | None, "Regulatory frameworks, e.g. ['EU_AI_ACT_2024']"] = None,
) -> str:
    """
    Register a new governed task in the AGP registry.

    This is always the first step in a governed workflow. Returns a Task object
    including the task_id needed for all subsequent calls.

    Risk tiers: low (routine, automated) → medium (sensitive data) →
    high (consequential decisions) → critical (safety-critical) →
    extreme (prohibited/requires special approval).
    """
    body: dict[str, Any] = {
        "principal_id": principal_id,
        "requested_outcome": requested_outcome,
        "risk_tier": risk_tier,
        "created_at": _now(),
    }
    if sponsoring_entity:
        body["sponsoring_entity"] = sponsoring_entity
    if jurisdictions:
        body["jurisdictions"] = jurisdictions
    if regulatory_frameworks:
        body["regulatory_frameworks"] = regulatory_frameworks

    result = await _request("POST", "/agp/tasks", body=body, idempotency_key=_ikey())
    return _fmt(result)


@mcp.tool()
async def get_task(
    task_id: Annotated[str, "Task ID returned by create_task"],
) -> str:
    """Retrieve the current state of a task by ID."""
    result = await _request("GET", f"/agp/tasks/{task_id}")
    return _fmt(result)


@mcp.tool()
async def transition_task(
    task_id: Annotated[str, "Task ID"],
    status: Annotated[str, "Target status: CREATED|BOUND|DECIDED|POLICY_CHECKED|APPROVAL_PENDING|EXECUTING|COMPLETED|FAILED|QUARANTINED|EXPIRED"],
) -> str:
    """
    Advance a task to a new status.

    Most transitions happen automatically when you call bind_liability,
    record_decision, evaluate_policy, or submit_action. Use this only
    when you need to drive the state machine directly (e.g. to mark
    a task FAILED or EXPIRED).
    """
    result = await _request("PATCH", f"/agp/tasks/{task_id}", body={"status": status})
    return _fmt(result)


@mcp.tool()
async def bind_liability(
    task_id: Annotated[str, "Task ID"],
    sponsoring_entity: Annotated[str, "Organisation taking accountability"],
    accountable_owner: Annotated[str, "Named individual responsible (email recommended)"],
    jurisdiction: Annotated[str, "Primary legal jurisdiction, e.g. 'EU' or 'US-CA'"],
) -> str:
    """
    Bind accountability for a task (CREATED → BOUND).

    Records who is legally responsible for this task's execution.
    Required before a decision can be recorded.
    """
    task = await _request("GET", f"/agp/tasks/{task_id}")
    result = await _request(
        "POST",
        "/agp/liability-bindings",
        body={
            "task_id": task_id,
            "sponsoring_entity": sponsoring_entity,
            "accountable_owner": accountable_owner,
            "jurisdiction": jurisdiction,
            "risk_tier": task["risk_tier"],
            "created_at": _now(),
        },
        idempotency_key=_ikey(),
    )
    return _fmt(result)


@mcp.tool()
async def issue_capability(
    subject_agent: Annotated[str, "Agent ID that will receive the capability"],
    issuer: Annotated[str, "Agent or principal issuing the capability"],
    principal_id: Annotated[str, "Principal on whose behalf this is issued"],
    permitted_actions: Annotated[list[str], "List of action names the agent is permitted to perform"],
    expires_in_days: Annotated[int, "Validity period in days (default: 30)"] = 30,
) -> str:
    """
    Issue a capability token authorising an agent to perform specific actions.

    The returned capability_id is used as capability_token_ref when submitting
    an action envelope. Tokens expire after expires_in_days.
    """
    result = await _request(
        "POST",
        "/agp/capabilities",
        body={
            "subject_agent": subject_agent,
            "issuer": issuer,
            "principal_id": principal_id,
            "permitted_actions": permitted_actions,
            "constraints": {},
            "expires_at": _future(expires_in_days),
            "revocation_id": _ikey(),
        },
        idempotency_key=_ikey(),
    )
    return _fmt(result)


@mcp.tool()
async def register_policy_set(
    name: Annotated[str, "Human-readable policy set name"],
    version: Annotated[str, "Semantic version, e.g. '1.0.0'"],
    publisher: Annotated[str, "Organisation publishing this policy set"],
    regulatory_frameworks: Annotated[list[str], "Frameworks covered, e.g. ['EU_AI_ACT_2024']"],
    jurisdictions: Annotated[list[str], "Applicable jurisdictions, e.g. ['EU']"],
    ruleset_hash: Annotated[str, "SHA-256 hash of the policy ruleset, e.g. 'sha256:abc...'"],
    ruleset_engine: Annotated[str, "Policy engine: opa | cedar | rego | custom"] = "opa",
) -> str:
    """
    Register a new policy set in the AGP registry.

    Policy sets define the rules evaluated during policy_decision calls.
    A policy set must be 'active' to be referenced in evaluations.
    """
    result = await _request(
        "POST",
        "/agp/policy-sets",
        body={
            "name": name,
            "version": version,
            "publisher": publisher,
            "regulatory_frameworks": regulatory_frameworks,
            "jurisdictions": jurisdictions,
            "ruleset_hash": ruleset_hash,
            "ruleset_engine": ruleset_engine,
            "attestation_level": "self_attested",
            "effective_from": _now(),
            "created_at": _now(),
        },
        idempotency_key=_ikey(),
    )
    return _fmt(result)


# ═══════════════════════════════════════════════════════════════════════════════
# DECISION TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
async def record_decision(
    task_id: Annotated[str, "Task ID (must be in BOUND status)"],
    agent_id: Annotated[str, "ID of the agent making the decision"],
    selected_action: Annotated[str, "The specific action the agent has chosen to take"],
    rationale: Annotated[str, "Explanation of why this action was selected"],
    uncertainty_score: Annotated[float, "Agent's self-assessed uncertainty [0.0–1.0]; >0.7 triggers escalation"],
    alternatives_considered: Annotated[list[str] | None, "Other actions the agent considered"] = None,
    evidence_refs: Annotated[list[str] | None, "References to evidence supporting this decision"] = None,
) -> str:
    """
    Record an agent decision (BOUND → DECIDED).

    Captures the agent's reasoning before any action is taken. This creates
    an immutable audit record. High uncertainty (>0.7) automatically escalates
    to APPROVAL_PENDING. The returned decision_id is needed for policy evaluation
    and execution.
    """
    body: dict[str, Any] = {
        "task_id": task_id,
        "agent_id": agent_id,
        "selected_action": selected_action,
        "rationale": rationale,
        "uncertainty_score": uncertainty_score,
        "created_at": _now(),
    }
    if alternatives_considered:
        body["alternatives_considered"] = alternatives_considered
    if evidence_refs:
        body["evidence_refs"] = evidence_refs

    result = await _request("POST", "/agp/decision/decisions", body=body, idempotency_key=_ikey())
    return _fmt(result)


@mcp.tool()
async def evaluate_policy(
    task_id: Annotated[str, "Task ID (must be in DECIDED status)"],
    verdict: Annotated[str, "Policy verdict: allow | deny | require_approval | require_human_review | quarantine"],
    rationale: Annotated[str, "Explanation of why this verdict was reached"],
    decision_ref: Annotated[str, "decision_id from record_decision"],
    matched_rules: Annotated[list[str] | None, "Policy rules that were matched"] = None,
    obligations: Annotated[list[str] | None, "Post-execution obligations the agent must fulfil"] = None,
    policy_set_ref: Annotated[str | None, "policy_set_id of the ruleset used for evaluation"] = None,
    risk_classification: Annotated[str | None, "Risk classification determined by policy engine"] = None,
) -> str:
    """
    Record a policy evaluation verdict (DECIDED → POLICY_CHECKED or APPROVAL_PENDING).

    This is the §9 policy gate. Verdict semantics:
      allow             — proceed to execution
      require_approval  — task moves to APPROVAL_PENDING, human must approve
      require_human_review — execution may proceed but human must review outcome
      deny              — task is blocked (moves to FAILED)
      quarantine        — task is isolated pending investigation
    """
    body: dict[str, Any] = {
        "task_id": task_id,
        "verdict": verdict,
        "rationale": rationale,
        "decision_ref": decision_ref,
        "matched_rules": matched_rules or [],
        "obligations": obligations or [],
        "evaluated_at": _now(),
    }
    if policy_set_ref:
        body["policy_set_ref"] = policy_set_ref
    if risk_classification:
        body["risk_classification"] = risk_classification

    result = await _request("POST", "/agp/decision/policy-evaluations", body=body, idempotency_key=_ikey())
    return _fmt(result)


@mcp.tool()
async def create_approval(
    task_id: Annotated[str, "Task ID (must be in APPROVAL_PENDING status)"],
    approver_id: Annotated[str, "ID of the human approver"],
    decision: Annotated[str, "Approval decision: approved | rejected"],
    rationale: Annotated[str, "Approver's reasoning"],
    policy_evaluation_ref: Annotated[str, "policy_evaluation_id from evaluate_policy"],
) -> str:
    """
    Record a human approval decision (APPROVAL_PENDING → POLICY_CHECKED or FAILED).

    Required when the policy verdict was 'require_approval'. An 'approved'
    decision allows the task to proceed to execution. A 'rejected' decision
    moves the task to FAILED.
    """
    result = await _request(
        "POST",
        "/agp/decision/approvals",
        body={
            "task_id": task_id,
            "approver_id": approver_id,
            "decision": decision,
            "rationale": rationale,
            "policy_evaluation_ref": policy_evaluation_ref,
            "approved_at": _now(),
        },
        idempotency_key=_ikey(),
    )
    return _fmt(result)


@mcp.tool()
async def create_escalation(
    task_id: Annotated[str, "Task ID"],
    raised_by: Annotated[str, "Agent ID raising the escalation"],
    concern_type: Annotated[str, "Type of concern: uncertainty | scope_ambiguity | ethical_concern | safety | other"],
    description: Annotated[str, "Detailed description of the concern requiring escalation"],
) -> str:
    """
    Raise an escalation notice for a task.

    Agents should escalate when they are uncertain, detect scope ambiguity,
    or identify an ethical concern that requires human judgment. Escalation
    moves the task to APPROVAL_PENDING.
    """
    result = await _request(
        "POST",
        "/agp/decision/escalations",
        body={
            "task_id": task_id,
            "raised_by": raised_by,
            "concern_type": concern_type,
            "description": description,
            "raised_at": _now(),
        },
        idempotency_key=_ikey(),
    )
    return _fmt(result)


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
async def submit_action(
    task_id: Annotated[str, "Task ID (must be in POLICY_CHECKED status)"],
    agent_id: Annotated[str, "Agent ID performing the action"],
    tool_id: Annotated[str, "Identifier of the tool or capability being invoked"],
    operation: Annotated[dict[str, Any], "Tool-specific operation parameters"],
    capability_token_ref: Annotated[str, "capability_id from issue_capability"],
    decision_ref: Annotated[str, "decision_id from record_decision"],
    policy_decision_ref: Annotated[str, "policy_evaluation_id from evaluate_policy"],
) -> str:
    """
    Submit an action envelope through the §10 execution gate (POLICY_CHECKED → EXECUTING → COMPLETED).

    This is the final governed step. The server validates all pre-conditions:
    - Capability token is valid and not revoked
    - Decision record references this task
    - Policy decision verdict is 'allow'
    - Task is in POLICY_CHECKED status

    On success, the action is logged to the tamper-evident ledger and the
    task advances to COMPLETED. Returns an ExecutionReceipt.
    """
    result = await _request(
        "POST",
        "/agp/action-envelopes",
        body={
            "task_id": task_id,
            "agent_id": agent_id,
            "tool_id": tool_id,
            "operation": operation,
            "capability_token_ref": capability_token_ref,
            "decision_ref": decision_ref,
            "policy_decision_ref": policy_decision_ref,
            "created_at": _now(),
        },
        idempotency_key=_ikey(),
    )
    return _fmt(result)


@mcp.tool()
async def validate_action(
    task_id: Annotated[str, "Task ID"],
    agent_id: Annotated[str, "Agent ID"],
    tool_id: Annotated[str, "Tool identifier"],
    operation: Annotated[dict[str, Any], "Operation parameters"],
    capability_token_ref: Annotated[str, "capability_id"],
    decision_ref: Annotated[str, "decision_id"],
    policy_decision_ref: Annotated[str, "policy_evaluation_id"],
) -> str:
    """
    Validate an action envelope without executing it (dry-run mode).

    Checks all §10 gate pre-conditions and returns 'valid: true' or a list
    of validation errors — without changing any task state or writing to the
    ledger. Use this before submit_action to catch configuration errors early.
    """
    result = await _request(
        "POST",
        "/agp/action-envelopes",
        body={
            "task_id": task_id,
            "agent_id": agent_id,
            "tool_id": tool_id,
            "operation": operation,
            "capability_token_ref": capability_token_ref,
            "decision_ref": decision_ref,
            "policy_decision_ref": policy_decision_ref,
            "created_at": _now(),
        },
        idempotency_key=_ikey(),
        prefer="validate-only",
    )
    return _fmt(result)


@mcp.tool()
async def replay_audit_log(
    task_id: Annotated[str, "Task ID to retrieve the audit trail for"],
) -> str:
    """
    Retrieve the complete tamper-evident audit trail for a task.

    Returns all ledger events in chronological order. Each event includes
    a hash linking it to the previous event (hash-chained ledger). Use this
    to generate compliance reports or investigate incidents.
    """
    result = await _request("GET", f"/agp/tasks/{task_id}/replay")
    return _fmt(result)


# ═══════════════════════════════════════════════════════════════════════════════
# HIGH-LEVEL SESSION TOOL
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
async def run_governed_task(
    principal_id: Annotated[str, "Agent ID performing the task"],
    requested_outcome: Annotated[str, "What the agent intends to accomplish"],
    risk_tier: Annotated[str, "Risk tier: low | medium | high | critical"],
    selected_action: Annotated[str, "Specific action to take"],
    rationale: Annotated[str, "Why this action is appropriate"],
    tool_id: Annotated[str, "Tool or capability to invoke"],
    operation: Annotated[dict[str, Any], "Tool-specific parameters"],
    sponsoring_entity: Annotated[str, "Organisation sponsoring this task"],
    accountable_owner: Annotated[str, "Named accountable individual (email)"],
    jurisdiction: Annotated[str, "Primary jurisdiction, e.g. 'EU'"],
    policy_verdict: Annotated[str, "Policy verdict to record: allow | require_approval"] = "allow",
    uncertainty_score: Annotated[float, "Agent uncertainty [0.0–1.0]"] = 0.1,
) -> str:
    """
    Execute a complete governed task lifecycle in a single call.

    Walks the full AGP lifecycle automatically:
      create_task → bind_liability → issue_capability →
      record_decision → evaluate_policy → submit_action

    Returns a summary JSON with all created artefact IDs and the final
    execution receipt. If policy_verdict is 'require_approval', the task
    will be left in APPROVAL_PENDING and the summary will include the
    approval URL.

    Use this for straightforward governed actions. For workflows requiring
    custom policy evaluation logic, conditional branching, or human-in-the-loop
    steps, use the individual tools instead.
    """
    summary: dict[str, Any] = {}

    # 1. Create task
    task = await _request(
        "POST", "/agp/tasks",
        body={
            "principal_id": principal_id,
            "requested_outcome": requested_outcome,
            "risk_tier": risk_tier,
            "sponsoring_entity": sponsoring_entity,
            "created_at": _now(),
        },
        idempotency_key=_ikey(),
    )
    task_id: str = task["task_id"]
    summary["task_id"] = task_id
    summary["status"] = task["status"]

    # 2. Bind liability
    binding = await _request(
        "POST", "/agp/liability-bindings",
        body={
            "task_id": task_id,
            "sponsoring_entity": sponsoring_entity,
            "accountable_owner": accountable_owner,
            "jurisdiction": jurisdiction,
            "risk_tier": risk_tier,
            "created_at": _now(),
        },
        idempotency_key=_ikey(),
    )
    summary["binding_id"] = binding["binding_id"]

    # 3. Issue capability
    token = await _request(
        "POST", "/agp/capabilities",
        body={
            "subject_agent": principal_id,
            "issuer": sponsoring_entity,
            "principal_id": principal_id,
            "permitted_actions": [selected_action],
            "constraints": {},
            "expires_at": _future(30),
            "revocation_id": _ikey(),
        },
        idempotency_key=_ikey(),
    )
    capability_id: str = token["capability_id"]
    summary["capability_id"] = capability_id

    # 4. Record decision
    decision = await _request(
        "POST", "/agp/decision/decisions",
        body={
            "task_id": task_id,
            "agent_id": principal_id,
            "selected_action": selected_action,
            "rationale": rationale,
            "uncertainty_score": uncertainty_score,
            "created_at": _now(),
        },
        idempotency_key=_ikey(),
    )
    decision_id: str = decision["decision_id"]
    summary["decision_id"] = decision_id

    # 5. Evaluate policy
    pd = await _request(
        "POST", "/agp/decision/policy-evaluations",
        body={
            "task_id": task_id,
            "verdict": policy_verdict,
            "rationale": f"Automated policy check for {risk_tier}-risk task",
            "decision_ref": decision_id,
            "matched_rules": [],
            "obligations": [],
            "evaluated_at": _now(),
        },
        idempotency_key=_ikey(),
    )
    policy_evaluation_id: str = pd["policy_evaluation_id"]
    summary["policy_evaluation_id"] = policy_evaluation_id
    summary["verdict"] = policy_verdict

    if policy_verdict != "allow":
        summary["status"] = "APPROVAL_PENDING"
        summary["message"] = (
            f"Task requires human approval (verdict: {policy_verdict}). "
            f"Call create_approval with task_id={task_id} and "
            f"policy_evaluation_ref={policy_evaluation_id}."
        )
        return _fmt(summary)

    # 6. Submit action
    receipt = await _request(
        "POST", "/agp/action-envelopes",
        body={
            "task_id": task_id,
            "agent_id": principal_id,
            "tool_id": tool_id,
            "operation": operation,
            "capability_token_ref": capability_id,
            "decision_ref": decision_id,
            "policy_decision_ref": policy_evaluation_id,
            "created_at": _now(),
        },
        idempotency_key=_ikey(),
    )
    summary["action_id"] = receipt.get("action_id")
    summary["status"] = "COMPLETED"
    summary["receipt"] = receipt

    return _fmt(summary)
