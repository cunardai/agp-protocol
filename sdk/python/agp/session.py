"""
AGP SDK — TaskSession

High-level fluent interface that manages the full AGP task lifecycle.
Hides state machine complexity: tracks task_id, capability token, decision,
and policy evaluation refs so callers don't have to.

Usage (simple, low-risk):
    client = AGPClient("http://localhost:8099")
    with client.task_session(
        principal_id="my-agent",
        requested_outcome="analyse customer feedback",
        risk_tier="low",
    ) as session:
        session.bind(sponsoring_entity="acme", accountable_owner="cto@acme.com",
                     jurisdiction="EU")
        session.decide(agent_id="my-agent", selected_action="run_analysis",
                       rationale="No PII, standard NLP", uncertainty_score=0.05)
        session.evaluate(verdict="allow")
        receipt = session.execute(agent_id="my-agent", tool_id="nlp-tool",
                                  operation={"text": "analyse this"},
                                  capability_token_ref="cap_xxx")

Usage (high-risk, EU AI Act governed):
    with client.task_session(..., risk_tier="high",
                             jurisdictions=["EU"],
                             regulatory_frameworks=["EU_AI_ACT_2024"]) as session:
        session.bind(...)
        session.decide(...)
        session.evaluate(verdict="require_approval", policy_set_ref="pset_xxx")
        session.approve(approver_id="human-reviewer-001")
        receipt = session.execute(...)
"""
from __future__ import annotations

from typing import Any

from .decision import DecisionClient
from .execution import ExecutionClient
from .models import (
    ActionEnvelope, ApprovalArtifact, AsyncOperation, CapabilityToken,
    DecisionRecord, GovernanceAttestation, LiabilityBinding, PolicyDecision,
    RiskTier, Task,
)
from .registry import RegistryClient


class TaskSession:
    """
    Stateful wrapper around an AGP task lifecycle.

    Tracks all artifact refs internally so you never have to pass
    decision_id, policy_evaluation_id, etc. between calls manually.
    """

    def __init__(
        self,
        registry: RegistryClient,
        decision: DecisionClient,
        execution: ExecutionClient,
        *,
        task: Task,
    ):
        self._reg = registry
        self._dec = decision
        self._exe = execution

        # Task state
        self.task: Task = task

        # Artifacts accumulated during the lifecycle
        self.liability_binding: LiabilityBinding | None = None
        self.capability_token: CapabilityToken | None = None
        self.decision_record: DecisionRecord | None = None
        self.policy_decision: PolicyDecision | None = None
        self.approval: ApprovalArtifact | None = None

    # ── Context manager ────────────────────────────────────────────────────

    def __enter__(self) -> "TaskSession":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            # Mark task as FAILED on unhandled exception
            try:
                self._reg.transition_task(self.task.task_id, "FAILED")
            except Exception:
                pass  # Best-effort; don't mask the original error

    @property
    def task_id(self) -> str:
        return self.task.task_id

    # ── Step 1: Bind liability ─────────────────────────────────────────────

    def bind(
        self,
        *,
        sponsoring_entity: str,
        accountable_owner: str,
        jurisdiction: str,
        risk_tier: RiskTier | None = None,
    ) -> "TaskSession":
        """
        Create a LiabilityBinding (CREATED → BOUND).
        Must be called before decide().
        """
        self.liability_binding = self._reg.create_liability_binding(
            task_id=self.task_id,
            sponsoring_entity=sponsoring_entity,
            accountable_owner=accountable_owner,
            jurisdiction=jurisdiction,
            risk_tier=risk_tier or self.task.risk_tier,
        )
        self.task = self._reg.get_task(self.task_id)
        return self

    # ── Step 1b: Issue capability token (optional, can be pre-issued) ──────

    def issue_capability(
        self,
        *,
        subject_agent: str,
        issuer: str,
        principal_id: str,
        permitted_actions: list[str],
        constraints: dict[str, Any] | None = None,
        expires_in_days: int = 30,
    ) -> "TaskSession":
        """Issue a CapabilityToken for this task's agent."""
        self.capability_token = self._reg.issue_capability(
            subject_agent=subject_agent,
            issuer=issuer,
            principal_id=principal_id,
            permitted_actions=permitted_actions,
            constraints=constraints,
            expires_in_days=expires_in_days,
        )
        return self

    def with_capability(self, token: CapabilityToken) -> "TaskSession":
        """Attach a pre-existing CapabilityToken to this session."""
        self.capability_token = token
        return self

    # ── Step 2: Submit decision ────────────────────────────────────────────

    def decide(
        self,
        *,
        agent_id: str,
        selected_action: str,
        rationale: str,
        uncertainty_score: float,
    ) -> "TaskSession":
        """
        Advance task to ANALYZING, then record the DecisionRecord (→ DECIDED).
        """
        current = self._reg.get_task(self.task_id)
        if current.status == "BOUND":
            self._reg.transition_task(self.task_id, "ANALYZING")
        self.decision_record = self._dec.create_decision(
            task_id=self.task_id,
            agent_id=agent_id,
            selected_action=selected_action,
            rationale=rationale,
            uncertainty_score=uncertainty_score,
        )
        self.task = self._reg.get_task(self.task_id)
        return self

    # ── Step 3: Policy evaluation ──────────────────────────────────────────

    def evaluate(
        self,
        *,
        verdict: str,
        rationale: str | None = None,
        policy_set_ref: str | None = None,
        jurisdiction: str | None = None,
        matched_rules: list[str] | None = None,
        obligations: list[str] | None = None,
    ) -> "TaskSession":
        """
        Record a PolicyDecision (DECIDED → POLICY_CHECKED | APPROVAL_PENDING | DENIED).

        Raises AGPBadRequestError if verdict is deny/quarantine and rationale is missing.
        """
        if not self.decision_record:
            raise RuntimeError("Call decide() before evaluate()")

        self.policy_decision = self._dec.evaluate_policy(
            task_id=self.task_id,
            decision_ref=self.decision_record.decision_id,
            verdict=verdict,  # type: ignore[arg-type]
            rationale=rationale,
            policy_set_ref=policy_set_ref,
            jurisdiction=jurisdiction,
            matched_rules=matched_rules,
            obligations=obligations,
        )
        self.task = self._reg.get_task(self.task_id)
        return self

    # ── Step 4 (conditional): Human approval ──────────────────────────────

    def approve(
        self,
        *,
        approver_id: str,
        decision: str = "approved",
        notes: str | None = None,
    ) -> "TaskSession":
        """
        Record human approval (APPROVAL_PENDING → POLICY_CHECKED).
        Only required when verdict was require_approval or risk_tier is high/critical.
        """
        self.approval = self._dec.create_approval(
            task_id=self.task_id,
            approver_id=approver_id,
            decision=decision,  # type: ignore[arg-type]
            notes=notes,
        )
        self.task = self._reg.get_task(self.task_id)
        return self

    def escalate(self, *, raised_by: str, concern_type: str, description: str) -> "TaskSession":
        """Raise an escalation notice (does not block execution)."""
        self._dec.escalate(
            task_id=self.task_id,
            raised_by=raised_by,
            concern_type=concern_type,
            description=description,
        )
        return self

    # ── Step 5: Execute ────────────────────────────────────────────────────

    def execute(
        self,
        *,
        agent_id: str,
        tool_id: str,
        operation: dict[str, Any],
        capability_token_ref: str | None = None,
        governance_attestations: list[GovernanceAttestation] | None = None,
        async_mode: bool = False,
    ) -> ActionEnvelope | AsyncOperation:
        """
        Submit the ActionEnvelope through the fail-closed gate.

        capability_token_ref defaults to session.capability_token.capability_id
        if issue_capability() or with_capability() was called.

        Raises:
            AGPPolicyDeniedError      — gate blocked by policy
            AGPApprovalRequiredError  — approval missing
            AGPTokenRevokedError      — token revoked
            AGPTokenExpiredError      — token expired
            RuntimeError               — evaluate() not yet called
        """
        if not self.policy_decision:
            raise RuntimeError("Call evaluate() before execute()")

        cap_ref = capability_token_ref
        if cap_ref is None and self.capability_token:
            cap_ref = self.capability_token.capability_id
        if not cap_ref:
            raise RuntimeError(
                "No capability_token_ref. Call issue_capability() or pass capability_token_ref."
            )

        approval_ref = self.approval.approval_id if self.approval else None

        # Advance to EXECUTING if not already there
        current = self._reg.get_task(self.task_id)
        if current.status == "POLICY_CHECKED":
            self._reg.transition_task(self.task_id, "EXECUTING")

        result = self._exe.submit_envelope(
            task_id=self.task_id,
            agent_id=agent_id,
            tool_id=tool_id,
            operation=operation,
            capability_token_ref=cap_ref,
            decision_ref=self.decision_record.decision_id,  # type: ignore[union-attr]
            policy_decision_ref=self.policy_decision.policy_evaluation_id,
            approval_ref=approval_ref,
            governance_attestations=governance_attestations,
            async_mode=async_mode,
        )
        if not async_mode:
            self.task = self._reg.get_task(self.task_id)
        return result

    # ── Convenience accessors ──────────────────────────────────────────────

    def refresh(self) -> "TaskSession":
        """Re-fetch current task state from the server."""
        self.task = self._reg.get_task(self.task_id)
        return self

    def replay(self) -> list[dict[str, Any]]:
        """Return the ordered audit ledger for this task."""
        return self._exe.replay_task(self.task_id)["events"]
