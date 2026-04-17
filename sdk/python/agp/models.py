"""
AGP SDK — Pydantic models for all AGP protocol objects.

Models are intentionally permissive on extra fields (model_config allows them)
so that newer server versions don't break older SDK clients.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _AGPBase(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


# ── Shared enums / literals ────────────────────────────────────────────────────

RiskTier = Literal["low", "medium", "high", "critical"]
TaskStatus = Literal[
    "CREATED", "BOUND", "DELEGATED", "SKILL_BOUND", "COMMERCE_INIT",
    "ANALYZING", "DECIDED", "POLICY_CHECKED", "APPROVAL_PENDING",
    "EXECUTING", "COMPLETED", "DENIED", "REVOKED", "QUARANTINED", "FAILED",
]
Verdict = Literal["allow", "deny", "require_approval", "require_stronger_auth", "quarantine"]
ApprovalDecision = Literal["approved", "denied"]
PolicySetStatus = Literal["active", "deprecated", "revoked"]
RulesetEngine = Literal["opa", "cedar", "casbin", "custom"]
AttestationLevel = Literal["self_attested", "third_party_attested", "verified"]


# ── Registry domain ────────────────────────────────────────────────────────────

class Task(_AGPBase):
    task_id: str
    principal_id: str
    requested_outcome: str
    risk_tier: RiskTier
    status: TaskStatus
    created_at: str
    expires_at: str | None = None
    sponsoring_entity: str | None = None
    governance_requirements: dict[str, Any] | None = None
    liability_binding_ref: str | None = None
    jurisdictions: list[str] = Field(default_factory=list)
    regulatory_frameworks: list[str] = Field(default_factory=list)


class LiabilityBinding(_AGPBase):
    binding_id: str
    type: str = "LiabilityBinding"
    task_id: str
    sponsoring_entity: str
    accountable_owner: str
    jurisdiction: str
    risk_tier: RiskTier
    created_at: str


class CapabilityToken(_AGPBase):
    capability_id: str
    type: str = "CapabilityToken"
    subject_agent: str
    issuer: str
    principal_id: str
    permitted_actions: list[str]
    constraints: dict[str, Any]
    expires_at: str
    revocation_id: str


class DelegationChain(_AGPBase):
    delegation_id: str
    type: str = "DelegationChain"
    root_principal: str
    delegator_agent: str
    delegate_agent: str
    authority_scope: list[str]
    constraints: dict[str, Any]
    accepted_at: str
    expires_at: str
    signature_chain: list[str]
    parent_delegation_id: str | None = None


class SkillManifest(_AGPBase):
    skill_id: str
    type: str = "SkillManifest"
    name: str
    version: str
    publisher: str
    supported_protocols: list[str]
    skill_class: str
    risk_class: str
    instruction_hash: str
    attestation_level: AttestationLevel
    created_at: str


class PolicySet(_AGPBase):
    policy_set_id: str
    type: str = "PolicySet"
    name: str
    version: str
    publisher: str
    regulatory_frameworks: list[str]
    jurisdictions: list[str]
    ruleset_hash: str
    ruleset_engine: RulesetEngine
    attestation_level: AttestationLevel
    status: PolicySetStatus
    effective_from: str
    created_at: str
    certifying_body: str | None = None
    supersedes: str | None = None


class RevocationNotice(_AGPBase):
    revocation_id: str
    type: str = "RevocationNotice"
    issuer: str
    target_type: str
    target_id: str
    reason: str
    effective_at: str


# ── Decision domain ────────────────────────────────────────────────────────────

class AttestedContext(_AGPBase):
    context_id: str
    type: str = "AttestedContext"
    task_id: str
    trust_class: str
    created_at: str


class EvidenceBundle(_AGPBase):
    bundle_id: str
    type: str = "EvidenceBundle"
    task_id: str
    items: list[dict[str, Any]]
    created_at: str


class DecisionRecord(_AGPBase):
    decision_id: str
    type: str = "DecisionRecord"
    task_id: str
    agent_id: str
    selected_action: str
    rationale: str
    uncertainty_score: float
    created_at: str


class PolicyDecision(_AGPBase):
    policy_evaluation_id: str
    type: str = "PolicyDecision"
    task_id: str
    decision_ref: str
    verdict: Verdict
    evaluated_at: str
    policy_set_ref: str | None = None
    jurisdiction: str | None = None
    rationale: str | None = None
    matched_rules: list[str] = Field(default_factory=list)
    obligations: list[str] = Field(default_factory=list)


class ApprovalArtifact(_AGPBase):
    approval_id: str
    type: str = "ApprovalArtifact"
    task_id: str
    approver_id: str
    decision: ApprovalDecision
    approved_at: str
    notes: str | None = None


class EscalationNotice(_AGPBase):
    escalation_id: str
    type: str = "EscalationNotice"
    task_id: str
    raised_by: str
    concern_type: str
    description: str
    raised_at: str


# ── Execution domain ───────────────────────────────────────────────────────────

class GovernanceAttestation(_AGPBase):
    agent_role: str
    verdict: Literal["cleared", "blocked"]
    attestation_ref: str | None = None


class ActionEnvelope(_AGPBase):
    action_id: str
    type: str = "ActionEnvelope"
    task_id: str
    agent_id: str
    tool_id: str
    operation: dict[str, Any]
    capability_token_ref: str
    decision_ref: str
    policy_decision_ref: str
    created_at: str
    approval_ref: str | None = None
    receipt_ref: str | None = None
    governance_attestations: list[GovernanceAttestation] = Field(default_factory=list)


class ExecutionReceipt(_AGPBase):
    receipt_id: str
    type: str = "ExecutionReceipt"
    action_ref: str
    task_id: str
    executed_at: str
    executor_id: str
    outcome: str


class EventLedgerRecord(_AGPBase):
    event_id: str
    type: str = "EventLedgerRecord"
    task_id: str
    timestamp: str
    agent_id: str
    principal_id: str
    outcome: str
    prev_event_hash: str | None = None
    tool_action_ref: str | None = None
    decision_ref: str | None = None


class AsyncOperation(_AGPBase):
    operation_id: str
    status: str
    created_at: str
    status_url: str
    action_envelope_ref: str | None = None


# ── Pagination wrapper ─────────────────────────────────────────────────────────

class Page(_AGPBase):
    has_more: bool
    next_cursor: str | None = None


class PagedResult(_AGPBase):
    items: list[Any]
    page: Page
